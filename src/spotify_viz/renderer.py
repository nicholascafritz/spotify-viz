from __future__ import annotations

from spotify_viz.signal import SignalBands


def render_frame(width: int, height: int, bands: SignalBands, *, tick: int) -> str:
    width, height = max(width, 20), max(height, 8)
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    horizon = max(2, height // 2 - int(bands.bass * 2))
    center = width // 2 + (int((tick % 11) - 5) if bands.transient else 0)
    for y in range(horizon, height):
        depth = (y - horizon + 1) / max(1, height - horizon)
        half = max(2, int(depth * width * (0.45 + bands.bass * 0.12)))
        left, right = max(0, center - half), min(width - 1, center + half)
        canvas[y][left] = "/"
        canvas[y][right] = "\\"
        if y % max(2, int(5 - bands.treble * 3)) == 0:
            for x in range(left + 1, right):
                if (x + tick) % max(3, int(9 - bands.mid * 5)) == 0:
                    canvas[y][x] = "."
    for door_y in range(horizon + 2, height, 6):
        span = max(3, (height - door_y) * 2)
        for x in (center - span, center + span):
            if 0 <= x < width:
                canvas[door_y][x] = "|"
        if 0 <= center - span < width and 0 <= center + span < width:
            canvas[door_y][center - span : center + span + 1] = list("-" * (span * 2 + 1))
    void = "[]"
    for index, char in enumerate(void):
        if 0 <= center + index - 1 < width:
            canvas[horizon][center + index - 1] = char
    return "\n".join("".join(row) for row in canvas)
