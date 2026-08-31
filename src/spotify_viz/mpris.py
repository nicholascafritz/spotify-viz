from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass(frozen=True, slots=True)
class NowPlaying:
    artist: str
    title: str
    status: str
    position: int


def parse_metadata(output: str) -> NowPlaying | None:
    fields = output.strip().split("\t")
    if len(fields) != 4:
        return None
    try:
        return NowPlaying(fields[0] or "UNKNOWN", fields[1] or "UNKNOWN", fields[2], int(float(fields[3])))
    except ValueError:
        return None


def current() -> NowPlaying | None:
    result = subprocess.run(
        ["playerctl", "--player=ncspot", "metadata", "--format", "{{artist}}\t{{title}}\t{{status}}\t{{position}}"],
        capture_output=True,
        text=True,
        check=False,
        timeout=2,
    )
    return parse_metadata(result.stdout) if result.returncode == 0 else None


def toggle() -> bool:
    return subprocess.run(
        ["playerctl", "--player=ncspot", "play-pause"], check=False, timeout=2
    ).returncode == 0
