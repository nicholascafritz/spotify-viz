from __future__ import annotations

from collections.abc import Callable, Sequence
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

    def toggle_playback(self) -> bool:
        try:
            return self._runner(["playerctl", "--player=ncspot", "play-pause"]).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


def current() -> NowPlaying | None:
    return MprisBridge().poll()


def toggle() -> bool:
    return MprisBridge().toggle_playback()
