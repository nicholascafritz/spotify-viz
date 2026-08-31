from __future__ import annotations

from dataclasses import dataclass


WIDE_MIN_COLUMNS = 72
WIDE_MIN_ROWS = 16


@dataclass(frozen=True, slots=True)
class Layout:
    columns: int
    rows: int
    canvas_width: int
    canvas_height: int
    compact: bool
    status_visible: bool


def select_layout(*, columns: int, rows: int, show_status: bool = True) -> Layout:
    """Select a stable cell grid without ever requiring horizontal scrolling."""
    safe_columns = max(1, columns)
    safe_rows = max(1, rows)
    compact = safe_columns < WIDE_MIN_COLUMNS or safe_rows < WIDE_MIN_ROWS
    status_visible = show_status and not compact
    return Layout(
        columns=safe_columns,
        rows=safe_rows,
        canvas_width=safe_columns,
        canvas_height=max(1, safe_rows - int(status_visible)),
        compact=compact,
        status_visible=status_visible,
    )
