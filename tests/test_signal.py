from spotify_viz.signal import SignalProcessor, SpectrumFrame


def test_signal_processor_splits_frequency_regions() -> None:
    processor = SignalProcessor()
    processor.process(SpectrumFrame((0,) * 9), now=0.0)

    bands = processor.process(
        SpectrumFrame((65535, 65535, 65535, 32768, 32768, 32768, 65535, 65535, 65535)),
        now=1.0,
    )

    assert bands.bass > 0.9
    assert 0.49 < bands.mid < 0.51
    assert bands.treble > 0.9


def test_loud_spike_is_a_bounded_transient_then_decays() -> None:
    processor = SignalProcessor()
    processor.process(SpectrumFrame((0,) * 12), now=0.0)

    hit = processor.process(SpectrumFrame((65535,) * 12), now=0.1)
    settled = processor.process(SpectrumFrame((0,) * 12), now=0.2)

    assert hit.transient is True
    assert settled.transient is False
    assert 0 <= settled.energy < hit.energy
