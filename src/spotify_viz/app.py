from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tty

from .cava import default_sink, monitor_source, write_config
from .mpris import current, toggle
from .renderer import render_frame
from .signal import SignalProcessor, SpectrumFrame

GREEN = "\x1b[38;2;88;255;158m"
CYAN = "\x1b[38;2;80;220;255m"
DIM = "\x1b[38;2;75;105;92m"
RESET = "\x1b[0m"


def _read_frame(stream, carry: bytes, bars: int) -> tuple[SpectrumFrame | None, bytes]:
    ready, _, _ = select.select([stream], [], [], 0)
    if ready:
        carry += os.read(stream.fileno(), 8192)
    size = bars * 2
    if len(carry) < size:
        return None, carry
    raw, carry = carry[:size], carry[size:]
    return SpectrumFrame(struct.unpack(f"{bars}H", raw)), carry


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audio-reactive liminal ASCII visualizer for ncspot.")
    parser.add_argument("--source", help="PipeWire/PulseAudio monitor source")
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args(argv)
    bars = 24
    source = monitor_source(args.source, default_sink=default_sink)
    with tempfile.TemporaryDirectory(prefix="spotify-viz-") as directory:
        config = Path(directory) / "cava.conf"
        write_config(config, source, bars=bars)
        cava = subprocess.Popen(["cava", "-p", str(config)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert cava.stdout is not None
        old = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        sys.stdout.flush()
        processor, carry, tick, help_visible = SignalProcessor(), b"", 0, False
        latest = SpectrumFrame((0,) * bars)
        try:
            while True:
                started = time.monotonic()
                frame, carry = _read_frame(cava.stdout, carry, bars)
                if frame:
                    latest = frame
                bands = processor.process(latest, now=started)
                size = shutil.get_terminal_size((100, 32))
                height = max(8, size.lines - 2)
                art = render_frame(size.columns, height, bands, tick=tick)
                track = current()
                status = f"{track.artist} — {track.title}" if track else "NO SIGNAL"
                footer = "SPACE: pause  M: scene  H: help  Q: quit"
                if help_visible:
                    footer = "BASS bends space · MIDS move debris · TREBLE fractures scanlines · Q returns"
                sys.stdout.write(f"\x1b[H{GREEN}{art}{RESET}\n{CYAN}{status[:size.columns]}{RESET}\n{DIM}{footer[:size.columns]}{RESET}")
                sys.stdout.flush()
                tick += 1
                ready, _, _ = select.select([sys.stdin], [], [], max(0, 1 / max(1, args.fps) - (time.monotonic() - started)))
                if ready:
                    key = os.read(sys.stdin.fileno(), 1)
                    if key in (b"q", b"Q", b"\x03"):
                        break
                    if key == b" ":
                        toggle()
                    if key in (b"h", b"H"):
                        help_visible = not help_visible
        finally:
            cava.terminate()
            try:
                cava.wait(timeout=1)
            except subprocess.TimeoutExpired:
                cava.kill()
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
            sys.stdout.write("\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
    return 0
