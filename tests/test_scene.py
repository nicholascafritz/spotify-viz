from __future__ import annotations

from spotify_viz.scene import PaletteRole, ServerCathedralScene
from spotify_viz.signal import SignalBands


ALLOWED_GLYPHS = set(" /\\|_-=.:+*#")


def bands(*, bass: float = 0.2, mid: float = 0.2, treble: float = 0.2, transient: bool = False) -> SignalBands:
    return SignalBands(bass=bass, mid=mid, treble=treble, energy=(bass + mid + treble) / 3, transient=transient)


def test_server_cathedral_is_deterministic_and_fixed_dimension() -> None:
    scene = ServerCathedralScene(seed=42)

    first = scene.render(width=80, height=24, bands=bands(), tick=7)
    second = scene.render(width=80, height=24, bands=bands(), tick=7)

    assert first == second
    assert first.width == 80
    assert first.height == 24
    assert all(len(row) == 80 for row in first.plain_rows())
    assert set("".join(first.plain_rows())) <= ALLOWED_GLYPHS


def test_cathedral_has_separate_depth_layers_and_off_centre_cyan_door() -> None:
    frame = ServerCathedralScene(seed=42).render(width=100, height=30, bands=bands(bass=0.5, mid=0.5), tick=8)

    assert {cell.role for cell in frame.cells} >= {PaletteRole.STRUCTURE, PaletteRole.REACTIVE, PaletteRole.VOID, PaletteRole.ATMOSPHERE}
    door_cells = [cell for cell in frame.cells if cell.role is PaletteRole.VOID]
    assert door_cells
    assert abs(sum(cell.x for cell in door_cells) / len(door_cells) - frame.width / 2) >= 1


def test_bass_moves_camera_and_changes_door_geometry() -> None:
    scene = ServerCathedralScene(seed=42)
    calm = scene.render(width=90, height=28, bands=bands(bass=0.0), tick=11)
    heavy = scene.render(width=90, height=28, bands=bands(bass=1.0), tick=11)

    assert calm != heavy
    assert calm.door_bounds != heavy.door_bounds


def test_cathedral_keeps_the_central_hanging_cable_out_of_the_focal_axis() -> None:
    frame = ServerCathedralScene(seed=42).render(width=100, height=30, bands=bands(), tick=8)
    assert all(
        frame.cells[y * frame.width + x].glyph not in "|:"
        for y in range(1, min(8, frame.height))
        for x in range(45, min(55, frame.width))
    )
    assert any(
        cell.y == int(frame.height * 0.52) and cell.role is PaletteRole.STRUCTURE and cell.glyph == "="
        for cell in frame.cells
    )


def test_midrange_increases_depth_separated_machine_and_debris_motion() -> None:
    scene = ServerCathedralScene(seed=42)
    quiet = scene.render(width=90, height=28, bands=bands(mid=0.0), tick=6)
    moving = scene.render(width=90, height=28, bands=bands(mid=1.0), tick=6)

    assert quiet != moving
    assert sum(cell.role is PaletteRole.ATMOSPHERE for cell in moving.cells) >= sum(cell.role is PaletteRole.ATMOSPHERE for cell in quiet.cells)


def test_treble_adds_bounded_interference_without_resizing_canvas() -> None:
    scene = ServerCathedralScene(seed=42)
    calm = scene.render(width=80, height=24, bands=bands(treble=0.0), tick=4)
    fractured = scene.render(width=80, height=24, bands=bands(treble=1.0), tick=4)

    assert (fractured.width, fractured.height) == (80, 24)
    assert sum(cell.role is PaletteRole.REACTIVE for cell in fractured.cells) >= sum(cell.role is PaletteRole.REACTIVE for cell in calm.cells)


def test_signal_tears_only_appear_on_transient_frames() -> None:
    scene = ServerCathedralScene(seed=42)
    quiet = scene.render(width=80, height=24, bands=bands(), tick=5)
    hit = scene.render(width=80, height=24, bands=bands(transient=True), tick=5)

    assert not any(cell.role is PaletteRole.SIGNAL for cell in quiet.cells)
    assert any(cell.role is PaletteRole.SIGNAL for cell in hit.cells)
