from __future__ import annotations

from collections.abc import Mapping

from .scene import Canvas, PaletteRole, ServerCathedralScene
from .signal import SignalBands


RESET = "\x1b[0m"
DEFAULT_COLORS = {
    "background": "#080e0e",
    "structure": "#58ff9e",
    "reactive": "#50dcff",
    "void": "#50dcff",
    "atmosphere": "#3a7669",
    "signal": "#eef5f5",
    "warning": "#ffbe46",
    "error": "#ff5454",
}


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def semantic_ansi(name: str, overrides: Mapping[str, str] | None = None) -> str:
    color = (overrides or {}).get(name, DEFAULT_COLORS[name])
    red, green, blue = _rgb(color)
    foreground = f"\x1b[38;2;{red};{green};{blue}m"
    if name == "background":
        return f"\x1b[48;2;{red};{green};{blue}m{foreground}"
    return foreground


def render_frame(width: int, height: int, bands: SignalBands, *, tick: int) -> str:
    """Compatibility helper for deterministic plain-ASCII snapshots."""
    return ServerCathedralScene(seed=0).render(width=width, height=height, bands=bands, tick=tick).text()


def compose_ansi(frame: Canvas, *, overrides: Mapping[str, str] | None = None) -> str:
    """Apply semantic truecolor at the final terminal-write boundary."""
    output: list[str] = []
    current: PaletteRole | None = None
    for y in range(frame.height):
        if y:
            output.append(RESET)
            output.append("\n")
            current = None
        for x in range(frame.width):
            cell = frame.cells[y * frame.width + x]
            if cell.role is not current:
                output.append(semantic_ansi(cell.role.value, overrides))
                current = cell.role
            output.append(cell.glyph)
    output.append(RESET)
    return "".join(output)
