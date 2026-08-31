from spotify_viz.renderer import render_frame
from spotify_viz.signal import SignalBands


def test_corridor_frame_has_fixed_dimensions_and_void() -> None:
    frame = render_frame(60, 18, SignalBands(0.8, 0.4, 0.2, 0.5, True), tick=7)

    rows = frame.splitlines()
    assert len(rows) == 18
    assert all(len(row) == 60 for row in rows)
    assert "[]" in frame
