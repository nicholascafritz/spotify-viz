from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
import subprocess
from typing import Protocol


class CommandResult(Protocol):
    returncode: int
    stdout: str


class MprisState(str, Enum):
    CONNECTED = "connected"
    STALE = "stale"
    NO_SIGNAL = "no_signal"


@dataclass(frozen=True, slots=True)
class NowPlaying:
    artist: str
    title: str
    status: str
    position: int
    duration: int = 0


def parse_metadata(output: str) -> NowPlaying | None:
    fields = output.strip().split("\t")
    if len(fields) not in (4, 5):
        return None
    try:
        position_raw = int(float(fields[3]))
        position = position_raw // 1_000_000 if position_raw >= 1_000_000 else position_raw
        duration_raw = int(float(fields[4])) if len(fields) == 5 else 0
        duration = duration_raw // 1_000_000 if duration_raw >= 1_000_000 else duration_raw
        return NowPlaying(fields[0] or "UNKNOWN", fields[1] or "UNKNOWN", fields[2], position, duration)
    except ValueError:
        return None


def _run(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(command), capture_output=True, text=True, check=False, timeout=2)


class MprisBridge:
    def __init__(self, *, runner: Callable[[list[str]], CommandResult] = _run) -> None:
        self._runner = runner
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="spotify-viz-mpris")
        self._future: Future[NowPlaying | None] | None = None
        self.state = MprisState.NO_SIGNAL
        self.last_now_playing: NowPlaying | None = None

    def poll(self) -> NowPlaying | None:
        command = [
            "playerctl", "--player=ncspot", "metadata", "--format",
            "{{artist}}\t{{title}}\t{{status}}\t{{position}}\t{{mpris:length}}",
        ]
        try:
            result = self._runner(command)
        except (OSError, subprocess.SubprocessError):
            result = None
        now_playing = parse_metadata(result.stdout) if result is not None and result.returncode == 0 else None
        if now_playing is not None:
            self.last_now_playing = now_playing
            self.state = MprisState.CONNECTED
            return now_playing
        self.state = MprisState.STALE if self.last_now_playing is not None else MprisState.NO_SIGNAL
        return self.last_now_playing

    def poll_nonblocking(self) -> NowPlaying | None:
        if self._future is None:
            self._future = self._executor.submit(self.poll)
            return self.last_now_playing
        if not self._future.done():
            return self.last_now_playing
        try:
            result = self._future.result()
        finally:
            self._future = None
        return result

    def wait_for_poll(self, *, timeout: float) -> NowPlaying | None:
        if self._future is None:
            return self.last_now_playing
        try:
            return self._future.result(timeout=timeout)
        finally:
            self._future = None

    def toggle_playback(self) -> bool:
        try:
            return self._runner(["playerctl", "--player=ncspot", "play-pause"]).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def current() -> NowPlaying | None:
    bridge = MprisBridge()
    try:
        return bridge.poll()
    finally:
        bridge.close()


def toggle() -> bool:
    bridge = MprisBridge()
    try:
        return bridge.toggle_playback()
    finally:
        bridge.close()
