from __future__ import annotations

from spotify_viz.batgrl_renderer import DenseCathedralComposer, LayeredFrame
from spotify_viz.signal import SignalBands


ASCII_GLYPHS = set(" /\\|_-=.:+*#")


def bands(*, bass: float = 0.3, mid: float = 0.4, treble: float = 0.5, transient: bool = False) -> SignalBands:
    return SignalBands(bass=bass, mid=mid, treble=treble, energy=(bass + mid + treble) / 3, transient=transient)


def test_batgrl_composer_produces_dense_deterministic_ascii_layers() -> None:
    composer = DenseCathedralComposer(seed=42)

    first = composer.render(width=100, height=32, bands=bands(), tick=12)
    second = composer.render(width=100, height=32, bands=bands(), tick=12)

    assert isinstance(first, LayeredFrame)
    assert first == second
    assert (first.width, first.height) == (100, 32)
    assert set(first.layers) == {"backdrop", "architecture", "void", "atmosphere", "reactive"}
    assert all(len(row) == 100 for layer in first.layers.values() for row in layer.rows)
    assert set("".join(first.composite_rows())) <= ASCII_GLYPHS
    assert sum(character != " " for row in first.composite_rows() for character in row) >= 500


def test_dense_cathedral_keeps_an_off_centre_void_and_open_focal_axis() -> None:
    frame = DenseCathedralComposer(seed=42).render(width=100, height=32, bands=bands(bass=0.6), tick=12)
    left, top, right, bottom = frame.void_bounds

    assert left > 50
    assert top < frame.height // 2 < bottom
    assert any("#" in row for row in frame.layers["void"].rows)
    focal_column = (left + right) // 2
    assert sum(row[focal_column] != " " for row in frame.layers["architecture"].rows[top:bottom]) <= 1


def test_audio_bands_affect_separate_layers_without_changing_dimensions() -> None:
    composer = DenseCathedralComposer(seed=42)
    calm = composer.render(width=90, height=28, bands=bands(), tick=9)
    bass = composer.render(width=90, height=28, bands=bands(bass=1.0), tick=9)
    mids = composer.render(width=90, height=28, bands=bands(mid=1.0), tick=9)
    treble = composer.render(width=90, height=28, bands=bands(treble=1.0), tick=9)
    hit = composer.render(width=90, height=28, bands=bands(transient=True), tick=9)

    assert calm.void_bounds != bass.void_bounds
    assert calm.layers["architecture"] != mids.layers["architecture"]
    assert calm.layers["reactive"] != treble.layers["reactive"]
    assert calm.layers["reactive"] != hit.layers["reactive"]
    assert (hit.width, hit.height) == (90, 28)
