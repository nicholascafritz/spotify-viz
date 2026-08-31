from spotify_viz.renderer import compose_ansi, render_frame
from spotify_viz.scene import ServerCathedralScene
from spotify_viz.signal import SignalBands


def test_cathedral_frame_has_fixed_dimensions_and_an_ascii_void() -> None:
    frame = render_frame(60, 18, SignalBands(0.8, 0.4, 0.2, 0.5, True), tick=7)

    rows = frame.splitlines()
    assert len(rows) == 18
    assert all(len(row) == 60 for row in rows)
    assert "#" in frame
    assert set(frame) <= set(" /\\|_-=.:+*#\n")


def test_ansi_composition_honors_palette_overrides() -> None:
    canvas = ServerCathedralScene(seed=2).render( width=60, height=18, bands=SignalBands(0.2, 0.2, 0.2, 0.2, False), tick=1)

    rendered = compose_ansi(canvas, overrides={"structure": "#11aa22"})

    assert "\x1b[38;2;17;170;34m" in rendered
