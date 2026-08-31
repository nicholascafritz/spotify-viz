from __future__ import annotations

import re
import sys
import termios
import tty
from typing import TextIO


ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ENTER_ALTERNATE = "\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H"
EXIT_ALTERNATE = "\x1b[0m\x1b[?25h\x1b[?1049l"


def visible_width(text: str) -> int:
    return len(ANSI_PATTERN.sub("", text))


class TerminalSession:
    """Own the alternate screen and raw terminal state for one renderer run."""

    def __init__(self, writer: TextIO | None = None, *, interactive: bool = True) -> None:
        self.writer = writer or sys.stdout
        self.interactive = interactive
        self._stdin_fd: int | None = None
        self._old_settings: list[int | list[bytes | int]] | None = None

    def __enter__(self) -> TerminalSession:
        if self.interactive and sys.stdin.isatty():
            stdin_fd = sys.stdin.fileno()
            self._stdin_fd = stdin_fd
            self._old_settings = termios.tcgetattr(stdin_fd)
            tty.setcbreak(stdin_fd)
        self.writer.write(ENTER_ALTERNATE)
        self.writer.flush()
        return self

    def draw(self, content: str) -> None:
        self.writer.write("\x1b[H\x1b[2J")
        self.writer.write(content)
        self.writer.flush()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            if self._stdin_fd is not None and self._old_settings is not None:
                termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._old_settings)
        finally:
            self.writer.write(EXIT_ALTERNATE)
            self.writer.flush()
        return False
