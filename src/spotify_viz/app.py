from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
import os
import select
import shutil
import sys
import time
from pathlib import Path
from typing import Protocol

from .cava import CavaBridge, TapState
from .config import VizConfig, load_config
from .layout import Layout, select_layout
from .mpris import MprisBridge, MprisState, NowPlaying
from .renderer import compose_ansi, semantic_ansi
from .scene import ServerCathedralScene
from .signal import SignalBands, SignalProcessor, SpectrumFrame
from .terminal import TerminalSession


RESET = "\x1b[0m"
METADATA_INTERVAL = 1.0


class AudioSource(Protocol):
    state: TapState

    def poll(self) -> SpectrumFrame | None: ...

    def close(self) -> None: ...


class MetadataSource(Protocol):
    state: MprisState

    def poll(self) -> NowPlaying | None: ...

    def toggle_playback(self) -> bool: ...


class TerminalWriter(Protocol):
    def draw(self, content: str) -> None: ...


@dataclass(slots=True)
class AppState:
    layout: Layout | None = None
    bands: SignalBands = SignalBands(0.0, 0.0, 0.0, 0.0, False)
    now_playing: NowPlaying | None = None
    help_visible: bool = False
    active_scene: int = 0
    next_metadata_poll: float = float("-inf")
    tick: int = 0


def frame_delay(*, fps: int, started: float, now: float) -> float:
    return round(max(0.0, 1 / fps - (now - started)), 8)


def _format_elapsed(seconds: int) -> str:
    return f"{max(0, seconds) // 60:02d}:{max(0, seconds) % 60:02d}"


class VisualizerApp:
    def __init__(
        self,
        *,
        config: VizConfig,
        cava: AudioSource,
        mpris: MetadataSource,
        terminal: TerminalWriter,
        size_provider: Callable[[], tuple[int, int]],
        scenes: Sequence[ServerCathedralScene] | None = None,
    ) -> None:
        self.config = config
        self.cava = cava
        self.mpris = mpris
        self.terminal = terminal
        self.size_provider = size_provider
        self.scenes = list(scenes or [ServerCathedralScene(seed=42)])
        self.processor = SignalProcessor()
        self.state = AppState()

    def step(self, *, now: float) -> bool:
        columns, rows = self.size_provider()
        self.state.layout = select_layout(columns=columns, rows=rows, show_status=self.config.show_status)
        frame = self.cava.poll()
        if self.cava.state is TapState.LOST:
            self.state.bands = SignalBands(0.0, 0.0, 0.0, 0.0, False)
        elif frame is not None:
            self.state.bands = self._scaled_bands(self.processor.process(frame, now=now))
        else:
            self.state.bands = SignalBands(
                self.state.bands.bass * 0.8,
                self.state.bands.mid * 0.8,
                self.state.bands.treble * 0.8,
                self.state.bands.energy * 0.8,
                False,
            )
        if now >= self.state.next_metadata_poll:
            self.state.now_playing = self.mpris.poll()
            self.state.next_metadata_poll = now + METADATA_INTERVAL
        layout = self.state.layout
        scene = self.scenes[self.state.active_scene]
        canvas = scene.render(
            width=layout.canvas_width,
            height=layout.canvas_height,
            bands=self.state.bands,
            tick=self.state.tick,
        )
        output = compose_ansi(canvas, overrides=dict(self.config.palette))
        if layout.status_visible:
            output += "\n" + self._status_line(layout.canvas_width)
        self.terminal.draw(output)
        self.state.tick += 1
        return True

    def handle_key(self, key: bytes) -> bool:
        if key in (b"q", b"Q", b"\x03"):
            return False
        if key == b" " and self.mpris.state is not MprisState.NO_SIGNAL:
            self.mpris.toggle_playback()
        elif key in (b"m", b"M"):
            self.state.active_scene = (self.state.active_scene + 1) % len(self.scenes)
        elif key in (b"h", b"H"):
            self.state.help_visible = not self.state.help_visible
        return True

    def close(self) -> None:
        self.cava.close()

    def _scaled_bands(self, bands: SignalBands) -> SignalBands:
        intensity = self.config.motion_intensity
        return SignalBands(
            bass=min(1.0, bands.bass * intensity),
            mid=min(1.0, bands.mid * intensity),
            treble=min(1.0, bands.treble * intensity),
            energy=min(1.0, bands.energy * intensity),
            transient=bands.transient,
        )

    def _status_line(self, width: int) -> str:
        if self.state.help_visible:
            line, color = "SPACE pause  M scene  H help  Q quit", semantic_ansi("reactive", dict(self.config.palette))
        elif self.mpris.state is MprisState.NO_SIGNAL or self.state.now_playing is None:
            line, color = "NO SIGNAL", semantic_ansi("warning", dict(self.config.palette))
        else:
            track = self.state.now_playing
            stale = " STALE" if self.mpris.state is MprisState.STALE else ""
            line = f"{track.artist} - {track.title}  {track.status}{stale}  {_format_elapsed(track.position)}"
            color = semantic_ansi("reactive", dict(self.config.palette))
        if self.cava.state is TapState.LOST:
            line = f"{line}  |  AUDIO TAP LOST"
            color = semantic_ansi("error", dict(self.config.palette))
        elif self.cava.state is TapState.STALE:
            line = f"{line}  |  AUDIO STALE"
            color = semantic_ansi("warning", dict(self.config.palette))
        return color + line[:width] + RESET


def _terminal_size() -> tuple[int, int]:
    size = shutil.get_terminal_size((100, 30))
    return size.columns, size.lines


def _read_key(timeout: float) -> bytes | None:
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return None
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return os.read(sys.stdin.fileno(), 1) if ready else None


def _build_live_app(config: VizConfig, *, source: str | None) -> tuple[VisualizerApp, TerminalSession]:
    try:
        cava = CavaBridge.discover(source or config.audio_source, fps=config.fps)
    except (OSError, RuntimeError):
        cava = CavaBridge(source=source or config.audio_source or "default", fps=config.fps)
    terminal = TerminalSession()
    app = VisualizerApp(
        config=config,
        cava=cava,
        mpris=MprisBridge(),
        terminal=terminal,
        size_provider=_terminal_size,
    )
    return app, terminal


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audio-reactive liminal ASCII visualizer for ncspot.")
    parser.add_argument("--source", help="PipeWire/PulseAudio monitor source")
    parser.add_argument("--fps", type=int, help="override the configured FPS cap")
    parser.add_argument("--config", type=Path, help="explicit configuration TOML path")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.fps is not None:
        config = replace(config, fps=args.fps)
        if not 1 <= config.fps <= 60:
            parser.error("--fps must be from 1 through 60")
    app, terminal = _build_live_app(config, source=args.source)
    try:
        app.cava.start()  # type: ignore[attr-defined]
        with terminal:
            running = True
            while running:
                started = time.monotonic()
                app.step(now=started)
                key = _read_key(frame_delay(fps=config.fps, started=started, now=time.monotonic()))
                if key is not None:
                    running = app.handle_key(key)
    except KeyboardInterrupt:
        return 0
    finally:
        app.close()
    return 0
