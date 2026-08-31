from __future__ import annotations

from spotify_viz.batgrl_renderer import BatgrlLayerStack, DenseCathedralComposer
from spotify_viz.signal import SignalBands


def test_batgrl_layer_stack_keeps_five_persistent_transparent_text_layers() -> None:
    frame = DenseCathedralComposer(seed=4).render(
        width=72,
        height=24,
        bands=SignalBands(0.5, 0.4, 0.7, 0.5, True),
        tick=9,
    )
    stack = BatgrlLayerStack(size=(24, 72))

    stack.present(frame)

    assert tuple(stack.layers) == ("backdrop", "architecture", "particles", "atmosphere", "reactive")
    assert all(layer.is_transparent for layer in stack.layers.values())
    assert all(tuple(layer.size) == (24, 72) for layer in stack.layers.values())
    assert ord(".") in stack.layers["particles"].canvas["ord"]
    assert ord("+") in stack.layers["particles"].canvas["ord"]
    assert ord("=") in stack.layers["reactive"].canvas["ord"]
