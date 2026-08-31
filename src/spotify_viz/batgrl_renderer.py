from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from batgrl.colors import Color
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.text import Text

from .signal import SignalBands


ASCII_GLYPHS = frozenset(" /\\|_-=.:+*#")
LAYER_ORDER = ("backdrop", "architecture", "void", "atmosphere", "reactive")
LAYER_COLORS = {
    "backdrop": Color(9, 22, 34),
    "architecture": Color(56, 126, 166),
    "void": Color(201, 72, 225),
    "atmosphere": Color(63, 187, 179),
    "reactive": Color(89, 230, 255),
}


@dataclass(frozen=True, slots=True)
class GlyphLayer:
    rows: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayeredFrame:
    width: int
    height: int
    layers: Mapping[str, GlyphLayer]
    void_bounds: tuple[int, int, int, int]

    def composite_rows(self) -> tuple[str, ...]:
        output: list[str] = []
        for y in range(self.height):
            row = [" "] * self.width
            for name in LAYER_ORDER:
                for x, glyph in enumerate(self.layers[name].rows[y]):
                    if glyph != " ":
                        row[x] = glyph
            output.append("".join(row))
        return tuple(output)


class _LayerBuilder:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.rows = [[" "] * width for _ in range(height)]

    def put(self, x: int, y: int, glyph: str) -> None:
        if 0 <= x < self.width and 0 <= y < self.height and glyph in ASCII_GLYPHS:
            self.rows[y][x] = glyph

    def line(self, x0: int, y0: int, x1: int, y1: int, glyph: str) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            self.put(x, y, glyph)

    def freeze(self) -> GlyphLayer:
        return GlyphLayer(tuple("".join(row) for row in self.rows))


class BatgrlLayerStack(Gadget):
    """Persistent transparent batgrl text planes for a layered frame."""

    def __init__(self, *, size: tuple[int, int]) -> None:
        super().__init__(size=size, is_transparent=True)
        self.layers = {name: Text(size=size, is_transparent=True) for name in LAYER_ORDER}
        for layer in self.layers.values():
            self.add_gadget(layer)

    def present(self, frame: LayeredFrame) -> None:
        size = (frame.height, frame.width)
        self.size = size
        for name, text in self.layers.items():
            text.size = size
            text.clear()
            color = LAYER_COLORS[name]
            for y, row in enumerate(frame.layers[name].rows):
                start = 0
                while start < len(row):
                    while start < len(row) and row[start] == " ":
                        start += 1
                    end = start
                    while end < len(row) and row[end] != " ":
                        end += 1
                    if start < end:
                        text.add_str(row[start:end], pos=(y, start), fg_color=color)
                    start = end


class DenseCathedralComposer:
    """A dense, load-bearing ASCII nave with an off-centre living void."""

    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def render(self, *, width: int, height: int, bands: SignalBands, tick: int) -> LayeredFrame:
        width, height = max(1, width), max(1, height)
        backdrop = _LayerBuilder(width, height)
        architecture = _LayerBuilder(width, height)
        void = _LayerBuilder(width, height)
        atmosphere = _LayerBuilder(width, height)
        reactive = _LayerBuilder(width, height)

        phase = tick * 0.055 + self.seed * 0.019
        drift = int(round(math.sin(phase) * 2 + bands.bass * math.sin(phase * 1.7) * 3))
        void_width = max(7, min(width // 3, int(width * (0.15 + bands.bass * 0.06))))
        void_height = max(7, min(height - 5, int(height * (0.43 + bands.bass * 0.10))))
        void_x = min(width - void_width // 2 - 3, max(void_width // 2 + 3, int(width * 0.62) + drift))
        void_top = max(2, min(height - void_height - 2, int(height * 0.17)))
        void_bounds = (
            max(1, void_x - void_width // 2),
            void_top,
            min(width - 2, void_x + void_width // 2),
            min(height - 2, void_top + void_height),
        )

        self._backdrop(backdrop, tick)
        self._architecture(architecture, void_bounds, bands, tick)
        self._void(void, void_bounds, bands, tick)
        self._atmosphere(atmosphere, void_bounds, bands, tick)
        self._reactive(reactive, void_bounds, bands, tick)

        return LayeredFrame(
            width=width,
            height=height,
            layers={
                "backdrop": backdrop.freeze(),
                "architecture": architecture.freeze(),
                "void": void.freeze(),
                "atmosphere": atmosphere.freeze(),
                "reactive": reactive.freeze(),
            },
            void_bounds=void_bounds,
        )

    def _backdrop(self, layer: _LayerBuilder, tick: int) -> None:
        for y in range(1, layer.height - 1):
            for x in range((y * 3 + tick) % 11, layer.width, 17):
                if (x + y * 5 + self.seed) % 4 == 0:
                    layer.put(x, y, ".")

    def _architecture(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left_void, top_void, right_void, bottom_void = bounds
        wall_width = max(6, min(layer.width // 4, int(layer.width * 0.21)))
        sway = int(round(math.sin((tick + self.seed) * 0.12) * (1 + bands.mid * 2)))

        material_phase = tick + int(bands.mid * 7)
        self._bulkhead(layer, 0, wall_width, material_phase, sway, mirrored=False)
        self._bulkhead(layer, layer.width - wall_width, layer.width - 1, material_phase, sway, mirrored=True)

        floor_top = max(bottom_void + 1, int(layer.height * 0.56))
        nave_left = wall_width - 2
        nave_right = layer.width - wall_width + 1
        for y in range(max(1, int(layer.height * 0.38)), layer.height):
            depth = (y - int(layer.height * 0.38)) / max(1, layer.height * 0.62)
            left = int(nave_left + (left_void - nave_left) * max(0.0, 1.0 - depth) * 0.62)
            right = int(nave_right + (right_void - nave_right) * max(0.0, 1.0 - depth) * 0.62)
            if y % 3 == 0:
                for x in range(max(0, left), min(layer.width, right + 1)):
                    if not self._inside(x, y, bounds) and (x + y + tick) % 5:
                        layer.put(x, y, "=")
            if y >= floor_top and y % 2:
                for x in range(max(0, left), min(layer.width, right + 1), 3):
                    if not self._inside(x, y, bounds):
                        layer.put(x, y, "_")
            layer.put(left, y, "/" if y < floor_top else "|")
            layer.put(right, y, "\\" if y < floor_top else "|")

        for level, ratio in enumerate((0.34, 0.49, 0.64, 0.80, 0.92)):
            y = min(layer.height - 2, max(2, int(layer.height * ratio) + ((level % 2) * 2 - 1) * sway))
            span = int(layer.width * (0.26 + level * 0.065))
            left, right = max(wall_width - 1, left_void - span), min(layer.width - wall_width, right_void + span)
            for x in range(left, right + 1):
                if not self._inside(x, y, bounds):
                    layer.put(x, y, "=")
            for brace_x in range(left + 5 + (level % 3), right - 3, 12):
                if not self._inside(brace_x, y - 1, bounds):
                    layer.put(brace_x, y - 1, "|")
                    layer.put(brace_x + 1, y - 2, "#")
                    layer.put(brace_x + 2, y - 1, "|")

        for cable in range(3):
            x = int(layer.width * (0.29 + cable * 0.17)) + sway
            end = max(3, int(layer.height * (0.38 + cable * 0.10)))
            for y in range(1, end):
                if not self._inside(x, y, bounds):
                    layer.put(x + int(math.sin(y * 0.7 + tick * 0.08 + cable) * 2), y, "|" if y % 3 else ":")

    def _bulkhead(self, layer: _LayerBuilder, start: int, end: int, tick: int, sway: int, *, mirrored: bool) -> None:
        width = max(1, end - start + 1)
        for y in range(layer.height):
            for column in range(width):
                x = end - column if mirrored else start + column
                if column in (0, width - 1):
                    glyph = "|"
                elif y % 5 == 0:
                    glyph = "="
                elif column % 5 == 0:
                    glyph = "|"
                elif (column + y * 2 + tick + self.seed) % 7 in (0, 1):
                    glyph = "#"
                elif (column * 3 + y + tick) % 5:
                    glyph = ":"
                else:
                    glyph = "."
                layer.put(x + (sway if column == width - 2 else 0), y, glyph)
            if y % 7 == 3:
                socket = start + width // 2 if not mirrored else end - width // 2
                layer.put(socket, y, "+")
                layer.put(socket, y + 1, "|")

    @staticmethod
    def _inside(x: int, y: int, bounds: tuple[int, int, int, int]) -> bool:
        left, top, right, bottom = bounds
        return left <= x <= right and top <= y <= bottom

    @staticmethod
    def _void(layer: _LayerBuilder, bounds: tuple[int, int, int, int], bands: SignalBands, tick: int) -> None:
        left, top, right, bottom = bounds
        center = (left + right) // 2
        height = max(1, bottom - top)
        for y in range(top, bottom + 1):
            arch = int(max(0, (bottom - y) / height * 3))
            edge_left, edge_right = left + arch, right - arch
            layer.put(edge_left, y, "/" if y < bottom else "_")
            layer.put(edge_right, y, "\\" if y < bottom else "_")
            for x in range(edge_left + 1, edge_right):
                if (x + y + tick) % 5:
                    layer.put(x, y, "#" if (x + y) % 2 else ":")
        for offset in range(-2, 3):
            layer.put(center + offset, top - 1, "=")
        if bands.bass > 0.6:
            layer.put(center, bottom + 1, "=")

    def _atmosphere(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left, top, right, bottom = bounds
        for index in range(12 + int(bands.mid * 24)):
            x = (index * 37 + tick * (index % 3 + 1) + self.seed * 11) % layer.width
            y = (index * 19 + tick * (index % 2 + 1) + self.seed) % layer.height
            if not (left - 3 <= x <= right + 3 and top - 2 <= y <= bottom + 2):
                layer.put(x, y, (".", ":", "+", "*")[index % 4])

    def _reactive(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left, top, right, bottom = bounds
        for index in range(2 + int(bands.treble * 8)):
            y = (tick * 2 + index * 4 + self.seed) % layer.height
            x = (tick * 11 + index * 17) % max(1, layer.width - 14)
            if top <= y <= bottom and left - 3 <= x <= right + 3:
                x = right + 4
            for column in range(x, min(layer.width, x + 5 + int(bands.treble * 11))):
                if (column + y + index) % 2:
                    layer.put(column, y, "-")
        if bands.transient:
            for index in range(6):
                y = (top + tick + index * 3) % layer.height
                x = max(0, min(layer.width - 8, left - 13 + index * 8))
                for column in range(x, x + 8):
                    layer.put(column, y, "=")
