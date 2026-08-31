from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess


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


def cava_config(source: str, *, bars: int = 24) -> str:
    return f"""[general]
bars = {bars}
framerate = 30

[input]
method = pulse
source = {source}

[output]
method = raw
raw_target = /dev/stdout
data_format = binary
bit_format = 16bit
channels = mono
"""


def write_config(path: Path, source: str, *, bars: int = 24) -> None:
    path.write_text(cava_config(source, bars=bars), encoding="utf-8")
