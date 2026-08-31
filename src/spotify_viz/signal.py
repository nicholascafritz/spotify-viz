from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpectrumFrame:
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SignalBands:
    bass: float
    mid: float
    treble: float
    energy: float
    transient: bool


class SignalProcessor:
    def __init__(self) -> None:
        self._previous_energy = 0.0
        self._baseline = 0.0

    def process(self, frame: SpectrumFrame, *, now: float) -> SignalBands:
        del now
        values = [max(0.0, min(1.0, value / 65535.0)) for value in frame.values]
        if not values:
            values = [0.0]
        third = max(1, len(values) // 3)
        bass = sum(values[:third]) / len(values[:third])
        mid_values = values[third : third * 2] or [0.0]
        high_values = values[third * 2 :] or [0.0]
        mid = sum(mid_values) / len(mid_values)
        treble = sum(high_values) / len(high_values)
        raw_energy = sum(values) / len(values)
        transient = raw_energy > max(0.16, self._baseline * 2.2) and raw_energy > self._previous_energy
        energy = self._previous_energy * 0.58 + raw_energy * 0.42
        self._baseline = self._baseline * 0.88 + raw_energy * 0.12
        self._previous_energy = energy
        return SignalBands(bass=bass, mid=mid, treble=treble, energy=energy, transient=transient)
