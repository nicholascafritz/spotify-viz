from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from batgrl.colors import Color
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.text import Text

from .signal import SignalBands


ASCII_GLYPHS = frozenset(" /\\|_-=.:+*#")
LAYER_ORDER = ("backdrop", "architecture", "particles", "atmosphere", "reactive")
LAYER_COLORS = {
    "backdrop": Color(9, 22, 34),
    "architecture": Color(56, 126, 166),
    "particles": Color(201, 72, 225),
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
    field_bounds: tuple[int, int, int, int]

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
    """Dense ASCII side bulkheads framing an audio-reactive particle field."""

    def __init__(self, *, seed: int = 0) -> None:
        self.seed = seed

    def render(self, *, width: int, height: int, bands: SignalBands, tick: int) -> LayeredFrame:
        width, height = max(1, width), max(1, height)
        backdrop = _LayerBuilder(width, height)
        architecture = _LayerBuilder(width, height)
        particles = _LayerBuilder(width, height)
        atmosphere = _LayerBuilder(width, height)
        reactive = _LayerBuilder(width, height)

        wall_width = self._bulkhead_width(width)
        if width > wall_width * 2 + 1:
            field_bounds = (wall_width + 1, 0, width - wall_width - 1, height - 1)
        else:
            field_bounds = (0, 0, -1, height - 1)

        self._backdrop(backdrop, tick)
        self._architecture(architecture, wall_width, bands, tick)
        self._particles(particles, field_bounds, bands, tick)
        self._atmosphere(atmosphere, field_bounds, bands, tick)
        self._reactive(reactive, field_bounds, bands, tick)

        return LayeredFrame(
            width=width,
            height=height,
            layers={
                "backdrop": backdrop.freeze(),
                "architecture": architecture.freeze(),
                "particles": particles.freeze(),
                "atmosphere": atmosphere.freeze(),
                "reactive": reactive.freeze(),
            },
            field_bounds=field_bounds,
        )

    def _backdrop(self, layer: _LayerBuilder, tick: int) -> None:
        for y in range(1, layer.height - 1):
            for x in range((y * 3 + tick) % 11, layer.width, 17):
                if (x + y * 5 + self.seed) % 4 == 0:
                    layer.put(x, y, ".")

    def _architecture(
        self,
        layer: _LayerBuilder,
        wall_width: int,
        bands: SignalBands,
        tick: int,
    ) -> None:
        sway = int(round(math.sin((tick + self.seed) * 0.12) * (1 + bands.mid * 2)))
        material_phase = tick + int(bands.mid * 7)
        self._bulkhead(layer, 0, wall_width, material_phase, sway, mirrored=False)
        self._bulkhead(layer, layer.width - wall_width, layer.width - 1, material_phase, sway, mirrored=True)

    @staticmethod
    def _bulkhead_width(width: int) -> int:
        return max(6, min(width // 4, int(width * 0.21)))

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

    def _particles(
        self,
        layer: _LayerBuilder,
        bounds: tuple[int, int, int, int],
        bands: SignalBands,
        tick: int,
    ) -> None:
        left, top, right, bottom = bounds
        field_width = right - left + 1
        field_height = bottom - top + 1
        if field_width <= 0 or field_height <= 0:
            return

        particle_count = max(1, field_width * field_height // 14)
        for index in range(particle_count):
            phase = tick * 0.035 + index * 0.71 + self.seed * 0.03
            base_x = (index * 37 + self.seed * 11 + round(math.sin(phase) * 2)) % field_width
            base_y = (index * 19 + self.seed * 7 + round(math.cos(phase * 0.61))) % field_height

            cloud = index % 2
            cloud_phase = tick * 0.045 + self.seed * 0.017 + cloud * math.pi
            center_x = field_width * (0.31 + cloud * 0.38 + math.sin(cloud_phase) * 0.045)
            center_y = field_height * (0.42 + cloud * 0.16 + math.cos(cloud_phase * 0.83) * 0.08)
            compression = bands.bass * (0.74 + math.sin(tick * 0.11 + self.seed * 0.013) * 0.12)
            local_x = round(base_x + (center_x - base_x) * compression)
            local_y = round(base_y + (center_y - base_y) * compression * 0.45)

            shear_phase = local_y / max(1, field_height - 1) * math.tau + tick * 0.04 + self.seed * 0.01
            shear = round(math.sin(shear_phase) * bands.mid * max(2, field_width * 0.13))
            x = left + max(0, min(field_width - 1, local_x + shear))
            y = top + max(0, min(field_height - 1, local_y))

            detail = (index * 29 + self.seed * 17) % 100
            if detail < bands.treble * 20:
                glyph = "*"
            elif detail < bands.treble * 70:
                glyph = "+"
            else:
                glyph = ":" if (index * 13 + self.seed) % 5 == 0 else "."
            layer.put(x, y, glyph)

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
        if not bands.transient:
            return

        left, top, right, bottom = bounds
        field_width = right - left + 1
        field_height = bottom - top + 1
        if field_width <= 0 or field_height <= 0:
            return

        for index in range(10):
            cloud = index % 2
            center_x = left + round(field_width * (0.32 + cloud * 0.36))
            center_y = top + round(field_height * (0.43 + cloud * 0.14))
            angle = index * math.tau / 10 + tick * 0.07 + self.seed * 0.011
            start_x = center_x + round(math.cos(angle) * 2)
            start_y = center_y + round(math.sin(angle))
            length = 5 + (index * 3 + self.seed) % 6
            end_x = center_x + round(math.cos(angle) * length)
            end_y = center_y + round(math.sin(angle) * length * 0.45)
            layer.line(start_x, start_y, end_x, end_y, "=" if index % 3 == 0 else "-")
