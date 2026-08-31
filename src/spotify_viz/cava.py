from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from importlib.resources import files
import os
from pathlib import Path
import selectors
import subprocess
import tempfile

from .signal import SpectrumFrame


RAW_SAMPLE_BYTES = 2


class TapState(str, Enum):
    CONNECTED = "connected"
    STALE = "stale"
    LOST = "lost"


def monitor_source(explicit: str | None, *, default_sink: Callable[[], str]) -> str:
    if explicit:
        return explicit
    sink = default_sink().strip()
    return sink if sink.endswith(".monitor") else f"{sink}.monitor"


def default_sink() -> str:
    completed = subprocess.run(
        ["pactl", "get-default-sink"], capture_output=True, text=True, check=True, timeout=2
    )
    return completed.stdout.strip()


def cava_template() -> str:
    return files("spotify_viz").joinpath("resources/cava.conf.template").read_text(encoding="utf-8")


def cava_config(source: str, *, bars: int = 24, framerate: int = 30) -> str:
    return cava_template().format(source=source, bars=bars, framerate=framerate)


def write_config(path: Path, source: str, *, bars: int = 24, framerate: int = 30) -> None:
    path.write_text(cava_config(source, bars=bars, framerate=framerate), encoding="utf-8")


class RawFrameParser:
    def __init__(self, *, bars: int) -> None:
        self.bars = bars
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[SpectrumFrame]:
        self._buffer.extend(chunk)
        frame_size = self.bars * RAW_SAMPLE_BYTES
        frames: list[SpectrumFrame] = []
        while len(self._buffer) >= frame_size:
            raw = bytes(self._buffer[:frame_size])
            del self._buffer[:frame_size]
            values = tuple(int.from_bytes(raw[index : index + 2], "little") for index in range(0, frame_size, 2))
            frames.append(SpectrumFrame(values))
        return frames


def tap_state_for_process(returncode: int | None, *, received_frame: bool) -> TapState:
    if received_frame:
        return TapState.CONNECTED
    if returncode is not None:
        return TapState.LOST
    return TapState.STALE


@dataclass
class CavaBridge:
    source: str
    bars: int = 24
    fps: int = 30

    def __post_init__(self) -> None:
        self.parser = RawFrameParser(bars=self.bars)
        self.state = TapState.STALE
        self.last_frame: SpectrumFrame | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._selector: selectors.BaseSelector | None = None
        self._config_path: Path | None = None

    @classmethod
    def discover(cls, explicit_source: str | None, *, bars: int = 24, fps: int = 30) -> CavaBridge:
        return cls(monitor_source(explicit_source, default_sink=default_sink), bars=bars, fps=fps)

    def start(self) -> None:
        temporary = tempfile.NamedTemporaryFile(prefix="spotify-viz-", suffix=".conf", delete=False)
        temporary.close()
        self._config_path = Path(temporary.name)
        write_config(self._config_path, self.source, bars=self.bars, framerate=self.fps)
        self._process = subprocess.Popen(
            ["cava", "-p", str(self._config_path)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        if self._process.stdout is None:
            self.state = TapState.LOST
            return
        os.set_blocking(self._process.stdout.fileno(), False)
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._process.stdout, selectors.EVENT_READ)

    def poll(self) -> SpectrumFrame | None:
        if self._process is None or self._process.stdout is None:
            self.state = TapState.LOST
            return self.last_frame
        received = False
        if self._selector is not None:
            for key, _ in self._selector.select(timeout=0):
                try:
                    chunk = os.read(key.fd, 8192)
                except BlockingIOError:
                    chunk = b""
                if chunk:
                    frames = self.parser.feed(chunk)
                    if frames:
                        self.last_frame = frames[-1]
                        received = True
        self.state = tap_state_for_process(self._process.poll(), received_frame=received)
        return self.last_frame

    def close(self) -> None:
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1)
        self._process = None
        if self._config_path is not None:
            self._config_path.unlink(missing_ok=True)
            self._config_path = None
