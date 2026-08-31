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
    "backdrop": Color(13, 29, 44),
    "architecture": Color(72, 120, 148),
    "void": Color(180, 67, 211),
    "atmosphere": Color(94, 191, 187),
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
        self.layers = {
            name: Text(size=size, is_transparent=True)
            for name in LAYER_ORDER
        }
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
    """Deterministic pure-ASCII scene model for batgrl layer presentation."""

    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def render(self, *, width: int, height: int, bands: SignalBands, tick: int) -> LayeredFrame:
        width, height = max(1, width), max(1, height)
        backdrop = _LayerBuilder(width, height)
        architecture = _LayerBuilder(width, height)
        void = _LayerBuilder(width, height)
        atmosphere = _LayerBuilder(width, height)
        reactive = _LayerBuilder(width, height)

        phase = tick * 0.07 + self.seed * 0.013
        camera = int(round(math.sin(phase) * 2 + math.sin(phase * 0.37) * 2 + bands.bass * math.sin(phase * 1.9) * 4))
        void_width = max(5, min(width // 4, int(width * (0.09 + bands.bass * 0.07))))
        void_height = max(5, min(height // 2, int(height * (0.28 + bands.bass * 0.16))))
        void_x = min(width - 3, max(void_width + 2, int(width * 0.58) + camera))
        void_top = max(2, min(height - void_height - 2, int(height * 0.24) - int(bands.bass * 2)))
        void_left = max(1, void_x - void_width // 2)
        void_right = min(width - 2, void_x + void_width // 2)
        void_bottom = min(height - 2, void_top + void_height)
        void_bounds = (void_left, void_top, void_right, void_bottom)

        self._backdrop(backdrop, tick, bands)
        self._architecture(architecture, void_bounds, bands, tick, camera)
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

    def _backdrop(self, layer: _LayerBuilder, tick: int, bands: SignalBands) -> None:
        for y in range(1, layer.height - 1):
            if (y + tick) % 5 == 0:
                for x in range((tick + y) % 4, layer.width, 7):
                    layer.put(x, y, ".")
        horizon = int(layer.height * 0.6)
        for x in range(0, layer.width, 3):
            if (x + tick) % 5:
                layer.put(x, horizon, ":")

    def _architecture(
        self,
        layer: _LayerBuilder,
        void_bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
        camera: int,
    ) -> None:
        left_void, top_void, right_void, bottom_void = void_bounds
        sway = int(math.sin((tick + self.seed) * 0.15) * (1 + bands.mid * 5))
        for y in range(layer.height):
            depth = y / max(1, layer.height - 1)
            wall = max(1, int(layer.width * (0.03 + (1 - depth) * 0.17)))
            left = wall + sway
            right = layer.width - 1 - wall + sway
            for offset, glyph in ((0, "|"), (2, ":"), (4, "|"), (6, "/")):
                layer.put(left + offset, y, glyph if (y + offset) % 4 else "+")
                layer.put(right - offset, y, "\\" if glyph == "/" else glyph)
            if y % 4 == 0:
                for x in range(max(0, left - 2), min(layer.width, left + 8)):
                    layer.put(x, y, "=")
                for x in range(max(0, right - 7), min(layer.width, right + 3)):
                    layer.put(x, y, "=")

        for level, ratio in enumerate((0.45, 0.56, 0.68, 0.79, 0.88)):
            y = min(layer.height - 2, max(1, int(layer.height * ratio) + ((level % 2) * 2 - 1) * sway))
            span = int(layer.width * (0.2 + level * 0.045))
            left, right = max(1, left_void - span), min(layer.width - 2, right_void + span)
            for x in range(left, right + 1):
                if (x + tick + level) % 4:
                    layer.put(x, y, "=")
            for bay in range(left + 3, right - 2, 11):
                if left_void <= bay <= right_void and top_void <= y <= bottom_void:
                    continue
                layer.put(bay, y - 1, "|")
                layer.put(bay + 1, y - 2, "#")
                layer.put(bay + 2, y - 1, "|")

        for y in range(2, layer.height - 2, 5):
            for x in range(8, layer.width - 8, 9):
                if left_void - 2 <= x <= right_void + 2 and top_void - 1 <= y <= bottom_void + 1:
                    continue
                glyph = "#" if (x + y + tick) % 3 else "+"
                layer.put(x + sway, y, glyph)
                layer.put(x + sway, y + 1, "|")

    @staticmethod
    def _void(layer: _LayerBuilder, bounds: tuple[int, int, int, int], bands: SignalBands, tick: int) -> None:
        left, top, right, bottom = bounds
        center = (left + right) // 2
        for y in range(top, bottom + 1):
            inset = int((y - top) * 0.18)
            edge_left, edge_right = left + inset, right - inset
            layer.put(edge_left, y, "/" if y < bottom else "_")
            layer.put(edge_right, y, "\\" if y < bottom else "_")
            for x in range(edge_left + 1, edge_right):
                glyph = "#" if (x + y + tick) % 3 else ":"
                layer.put(x, y, glyph)
        layer.put(center, top - 1, "=")
        if bands.bass > 0.65:
            layer.put(center, bottom + 1, "=")

    def _atmosphere(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left, top, right, bottom = bounds
        count = 18 + int(bands.mid * 42)
        for index in range(count):
            x = (index * 29 + tick * (index % 5 + 1) + self.seed * 7) % layer.width
            y = (index * 17 + tick * (index % 3 + 1) + self.seed) % layer.height
            if left - 2 <= x <= right + 2 and top - 1 <= y <= bottom + 1:
                continue
            layer.put(x, y, (".", ":", "+", "*")[index % 4])

    def _reactive(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left, top, right, bottom = bounds
        for index in range(int(bands.treble * 7)):
            y = (tick * 3 + index * 5 + self.seed) % layer.height
            x = (tick * 7 + index * 13) % max(1, layer.width - 9)
            if top <= y <= bottom and left - 2 <= x <= right + 2:
                x = max(0, right + 3)
            for column in range(x, min(layer.width, x + 3 + int(bands.treble * 10))):
                if (column + y) % 2:
                    layer.put(column, y, "-")
        if bands.transient:
            for index in range(5):
                y = (top + tick + index * 3) % layer.height
                x = max(0, min(layer.width - 6, left - 10 + index * 7))
                for column in range(x, x + 6):
                    layer.put(column, y, "=")
