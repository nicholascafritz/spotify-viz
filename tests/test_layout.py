from __future__ import annotations

from io import StringIO

import pytest

from spotify_viz.layout import select_layout
from spotify_viz.terminal import TerminalSession, visible_width


def test_wide_layout_reserves_a_fixed_status_row() -> None:
    layout = select_layout(columns=100, rows=30, show_status=True)

    assert layout.compact is False
    assert layout.canvas_width == 100
    assert layout.canvas_height == 29
    assert layout.status_visible is True


def test_small_terminal_uses_compact_canvas_without_status() -> None:
    layout = select_layout(columns=60, rows=12, show_status=True)

    assert layout.compact is True
    assert layout.canvas_width == 60
    assert layout.canvas_height == 12
    assert layout.status_visible is False


def test_visible_width_ignores_truecolor_ansi_sequences() -> None:
    assert visible_width("\x1b[38;2;80;220;255mvoid\x1b[0m") == 4


def test_terminal_session_restores_cursor_and_screen_after_exception() -> None:
    output = StringIO()

    with pytest.raises(RuntimeError, match="boom"):
        with TerminalSession(output, interactive=False):
            raise RuntimeError("boom")

    assert "\x1b[?1049h" in output.getvalue()
    assert "\x1b[?25l" in output.getvalue()
    assert "\x1b[?25h" in output.getvalue()
    assert "\x1b[?1049l" in output.getvalue()
