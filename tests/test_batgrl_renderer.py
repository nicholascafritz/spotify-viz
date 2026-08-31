from __future__ import annotations

from spotify_viz.batgrl_renderer import DenseCathedralComposer, LayeredFrame
from spotify_viz.signal import SignalBands


ASCII_GLYPHS = set(" /\\|_-=.:+*#")


def bands(
    *,
    bass: float = 0.3,
    mid: float = 0.4,
    treble: float = 0.5,
    energy: float | None = None,
    transient: bool = False,
) -> SignalBands:
    resolved_energy = (bass + mid + treble) / 3 if energy is None else energy
    return SignalBands(bass=bass, mid=mid, treble=treble, energy=resolved_energy, transient=transient)


def test_batgrl_composer_produces_dense_deterministic_ascii_layers() -> None:
    composer = DenseCathedralComposer(seed=42)

    first = composer.render(width=100, height=32, bands=bands(), tick=12)
    second = composer.render(width=100, height=32, bands=bands(), tick=12)

    assert isinstance(first, LayeredFrame)
    assert first == second
    assert (first.width, first.height) == (100, 32)
    assert set(first.layers) == {"backdrop", "architecture", "particles", "atmosphere", "reactive"}
    assert all(len(row) == 100 for layer in first.layers.values() for row in layer.rows)
    assert set("".join(first.composite_rows())) <= ASCII_GLYPHS


def test_dense_bulkheads_leave_an_unboxed_nonempty_particle_field() -> None:
    frame = DenseCathedralComposer(seed=42).render(width=100, height=32, bands=bands(bass=0.6), tick=12)
    left, top, right, bottom = frame.field_bounds
    field_area = (right - left + 1) * (bottom - top + 1)
    architecture_ink = sum(
        character != " "
        for row in frame.layers["architecture"].rows[top : bottom + 1]
        for character in row[left : right + 1]
    )
    particle_ink = sum(
        character != " "
        for row in frame.layers["particles"].rows[top : bottom + 1]
        for character in row[left : right + 1]
    )

    assert (top, bottom) == (0, frame.height - 1)
    assert architecture_ink <= frame.height
    assert field_area * 0.04 <= particle_ink <= field_area * 0.30


def test_particle_field_has_no_long_rigid_portal_edge() -> None:
    frame = DenseCathedralComposer(seed=42).render(width=100, height=32, bands=bands(bass=0.6), tick=12)
    left, top, right, bottom = frame.field_bounds

    longest_runs = []
    for row in frame.layers["particles"].rows[top : bottom + 1]:
        runs = "".join("#" if character != " " else " " for character in row[left : right + 1]).split()
        longest_runs.append(max((len(run) for run in runs), default=0))

    assert max(longest_runs) <= 8


def test_bulkhead_architecture_retains_dense_full_height_side_coverage() -> None:
    frame = DenseCathedralComposer(seed=42).render(width=100, height=32, bands=bands(bass=0.5, mid=0.5), tick=12)
    left, _, right, _ = frame.field_bounds
    rows = frame.layers["architecture"].rows

    side_width = left + frame.width - right - 1
    side_ink_by_row = [sum(character != " " for character in (*row[:left], *row[right + 1 :])) for row in rows]

    assert all(ink >= side_width * 0.85 for ink in side_ink_by_row)


def test_portrait_terminal_keeps_dense_sides_and_an_open_particle_center() -> None:
    frame = DenseCathedralComposer(seed=42).render(width=80, height=42, bands=bands(bass=0.5, mid=0.5), tick=12)
    left, top, right, bottom = frame.field_bounds
    architecture = frame.layers["architecture"].rows
    particles = frame.layers["particles"].rows

    center_architecture_ink = sum(
        character != " " for row in architecture[top : bottom + 1] for character in row[left : right + 1]
    )
    center_particle_ink = sum(
        character != " " for row in particles[top : bottom + 1] for character in row[left : right + 1]
    )

    assert center_architecture_ink <= frame.height
    assert center_particle_ink >= 80


def occupied_positions(frame: LayeredFrame, layer_name: str) -> set[tuple[int, int]]:
    return {
        (x, y)
        for y, row in enumerate(frame.layers[layer_name].rows)
        for x, character in enumerate(row)
        if character != " "
    }


def test_bass_changes_particle_positions_and_compresses_cloud_spread() -> None:
    composer = DenseCathedralComposer(seed=42)
    calm = composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=0.0, energy=0.5), tick=9)
    bass_heavy = composer.render(width=90, height=28, bands=bands(bass=1.0, mid=0.0, treble=0.0, energy=0.5), tick=9)

    calm_positions = occupied_positions(calm, "particles")
    bass_positions = occupied_positions(bass_heavy, "particles")

    assert calm_positions != bass_positions
    assert len({x for x, _ in bass_positions}) < len({x for x, _ in calm_positions})


def test_mids_laterally_shear_particles_without_changing_their_vertical_domain() -> None:
    composer = DenseCathedralComposer(seed=42)
    calm = composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=0.0, energy=0.5), tick=9)
    mid_heavy = composer.render(width=90, height=28, bands=bands(bass=0.0, mid=1.0, treble=0.0, energy=0.5), tick=9)

    calm_positions = occupied_positions(calm, "particles")
    mid_positions = occupied_positions(mid_heavy, "particles")

    assert calm_positions != mid_positions
    assert {y for _, y in calm_positions} == {y for _, y in mid_positions}


def test_treble_brightens_particle_glyphs_without_moving_particles() -> None:
    composer = DenseCathedralComposer(seed=42)
    calm = composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=0.0, energy=0.5), tick=9)
    treble_heavy = composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=1.0, energy=0.5), tick=9)

    calm_glyphs = "".join(calm.layers["particles"].rows)
    treble_glyphs = "".join(treble_heavy.layers["particles"].rows)

    assert occupied_positions(calm, "particles") == occupied_positions(treble_heavy, "particles")
    assert not set(calm_glyphs) & {"+", "*"}
    assert sum(glyph in "+*" for glyph in treble_glyphs) >= 20


def test_transient_adds_only_a_short_lived_reactive_burst() -> None:
    composer = DenseCathedralComposer(seed=42)
    calm_bands = bands(bass=0.2, mid=0.3, treble=0.4)
    hit_bands = bands(bass=0.2, mid=0.3, treble=0.4, transient=True)
    calm = composer.render(width=90, height=28, bands=calm_bands, tick=9)
    hit = composer.render(width=90, height=28, bands=hit_bands, tick=9)

    for layer_name in ("backdrop", "architecture", "particles", "atmosphere"):
        assert calm.layers[layer_name] == hit.layers[layer_name]
    assert not occupied_positions(calm, "reactive")
    assert occupied_positions(hit, "reactive")
    assert set("".join(hit.layers["reactive"].rows)) <= {" ", "-", "="}


def test_audio_variants_keep_fixed_ascii_dimensions() -> None:
    composer = DenseCathedralComposer(seed=42)
    variants = (
        composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=0.0), tick=9),
        composer.render(width=90, height=28, bands=bands(bass=1.0, mid=0.0, treble=0.0), tick=9),
        composer.render(width=90, height=28, bands=bands(bass=0.0, mid=1.0, treble=0.0), tick=9),
        composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=1.0), tick=9),
        composer.render(width=90, height=28, bands=bands(bass=0.0, mid=0.0, treble=0.0, transient=True), tick=9),
    )

    for frame in variants:
        assert (frame.width, frame.height) == (90, 28)
        assert set("".join(frame.composite_rows())) <= ASCII_GLYPHS
