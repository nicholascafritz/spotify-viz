from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .signal import SignalBands


class PaletteRole(str, Enum):
    BACKGROUND = "background"
    STRUCTURE = "structure"
    REACTIVE = "reactive"
    VOID = "void"
    ATMOSPHERE = "atmosphere"
    SIGNAL = "signal"


@dataclass(frozen=True, slots=True)
class Cell:
    x: int
    y: int
    glyph: str
    role: PaletteRole
    depth: int


@dataclass(frozen=True, slots=True)
class Canvas:
    width: int
    height: int
    cells: tuple[Cell, ...]
    door_bounds: tuple[int, int, int, int]

    def plain_rows(self) -> tuple[str, ...]:
        return tuple(
            "".join(self.cells[y * self.width + x].glyph for x in range(self.width))
            for y in range(self.height)
        )

    def text(self) -> str:
        return "\n".join(self.plain_rows())


class _CanvasBuilder:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.cells = [Cell(x, y, " ", PaletteRole.BACKGROUND, -1) for y in range(height) for x in range(width)]

    def put(self, x: int, y: int, glyph: str, role: PaletteRole, depth: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = y * self.width + x
        if depth >= self.cells[index].depth:
            self.cells[index] = Cell(x, y, glyph, role, depth)


class ServerCathedralScene:
    """A deterministic, layered ASCII server cathedral with a breathing void."""

    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def render(self, *, width: int, height: int, bands: SignalBands, tick: int) -> Canvas:
        width, height = max(1, width), max(1, height)
        canvas = _CanvasBuilder(width, height)
        phase = tick * 0.11 + self.seed * 0.019
        drift = int(round(math.sin(phase * 0.37) * 2 + math.sin(phase * 0.11) + bands.bass * math.sin(phase * 1.7) * 3))
        door_x = min(width - 5, max(4, width // 2 + 1 + drift))
        door_y = min(height - 5, max(2, int(height * 0.38) - int(bands.bass * 2)))
        door_half_width = min(max(2, 3 + int(width * bands.bass * 0.06)), max(2, width // 5))
        door_height = min(max(3, 4 + int(height * bands.bass * 0.09)), max(3, height // 3))

        self._background_door(canvas, door_x, door_y, door_half_width, door_height)
        self._midground(canvas, door_x, door_y, bands, tick)
        self._atmosphere(canvas, door_x, door_y, bands, tick)
        self._foreground(canvas, bands, tick)
        self._interference(canvas, bands, tick)
        if bands.transient:
            self._signal_tears(canvas, door_x, door_y, tick)

        return Canvas(
            width=width,
            height=height,
            cells=tuple(canvas.cells),
            door_bounds=(door_x - door_half_width, door_y, door_x + door_half_width, door_y + door_height),
        )

    @staticmethod
    def _background_door(canvas: _CanvasBuilder, x: int, y: int, half: int, height: int) -> None:
        for row in range(height + 1):
            inset = max(0, (height - row) // 3)
            left, right = x - half + inset, x + half - inset
            canvas.put(left, y + row, "/" if row else "_", PaletteRole.REACTIVE, 2)
            canvas.put(right, y + row, "\\" if row else "_", PaletteRole.REACTIVE, 2)
            for column in range(left + 1, right):
                canvas.put(column, y + row, "#" if row % 2 else ":", PaletteRole.VOID, 1)
        canvas.put(x, y - 1, "=", PaletteRole.REACTIVE, 2)

    def _midground(self, canvas: _CanvasBuilder, door_x: int, door_y: int, bands: SignalBands, tick: int) -> None:
        shift = int(math.sin((tick + self.seed) * 0.19) * (1 + bands.mid * 5))
        for level, ratio in enumerate((0.52, 0.66, 0.79)):
            y = min(canvas.height - 2, max(1, int(canvas.height * ratio) + (shift if level % 2 else -shift)))
            span = max(6, int(canvas.width * (0.17 + level * 0.10)))
            left, right = max(0, door_x - span), min(canvas.width - 1, door_x + span)
            for x in range(left, right + 1):
                if (x + level + tick) % 3:
                    canvas.put(x, y, "=", PaletteRole.STRUCTURE, 4)
            bay_offset = int((bands.mid * 4 + level) % 5)
            for bay_x in (left + 2 + bay_offset, right - 2 - bay_offset):
                canvas.put(bay_x, y - 1, "|", PaletteRole.STRUCTURE, 4)
                canvas.put(bay_x, y - 2, "#", PaletteRole.REACTIVE, 4)
                canvas.put(bay_x, y - 3, "|", PaletteRole.STRUCTURE, 4)

    def _foreground(self, canvas: _CanvasBuilder, bands: SignalBands, tick: int) -> None:
        sway = int(math.sin((tick + self.seed) * 0.07) * (1 + bands.mid * 3))
        for y in range(canvas.height):
            depth = y / max(1, canvas.height - 1)
            inset = max(0, int((1 - depth) * canvas.width * 0.13))
            left, right = inset + sway, canvas.width - 1 - inset + sway
            canvas.put(left, y, "/" if y < canvas.height // 2 else "|", PaletteRole.STRUCTURE, 8)
            canvas.put(right, y, "\\" if y < canvas.height // 2 else "|", PaletteRole.STRUCTURE, 8)
        for cable in (0, 2):
            cable_x = int(canvas.width * (0.12 + cable * 0.37)) + sway
            end = min(canvas.height // 2 + cable * 2, canvas.height - 1)
            for y in range(0, end):
                x = cable_x + int(math.sin(y * 0.6 + tick * 0.08 + cable) * (1 + bands.mid * 2))
                canvas.put(x, y, "|" if y % 3 else ":", PaletteRole.STRUCTURE, 9)

    def _atmosphere(self, canvas: _CanvasBuilder, door_x: int, door_y: int, bands: SignalBands, tick: int) -> None:
        count = 4 + int(bands.mid * 12)
        for index in range(count):
            x = (index * 37 + tick * (1 + index % 3) + self.seed * 11) % canvas.width
            y = (index * 11 + tick * (1 + index % 2) + self.seed) % canvas.height
            if abs(x - door_x) < 6 and abs(y - door_y) < 5:
                continue
            canvas.put(x, y, (".", ":", "+", "*")[index % 4], PaletteRole.ATMOSPHERE, 5)

    def _interference(self, canvas: _CanvasBuilder, bands: SignalBands, tick: int) -> None:
        rows = int(bands.treble * 4)
        for index in range(rows):
            y = (tick * 3 + index * 7 + self.seed) % canvas.height
            start = (tick * 5 + index * 17) % max(1, canvas.width - 8)
            for x in range(start, min(canvas.width, start + 3 + int(bands.treble * 8))):
                if (x + y) % 2:
                    canvas.put(x, y, "-", PaletteRole.REACTIVE, 6)

    def _signal_tears(self, canvas: _CanvasBuilder, door_x: int, door_y: int, tick: int) -> None:
        for index in range(3):
            y = (door_y + index * 3 + tick) % canvas.height
            x = max(0, min(canvas.width - 4, door_x + ((index - 1) * 9)))
            for column in range(x, x + 4):
                canvas.put(column, y, "=", PaletteRole.SIGNAL, 10)
