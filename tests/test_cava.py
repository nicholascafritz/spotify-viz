from spotify_viz.cava import cava_config, monitor_source


def test_explicit_audio_source_wins() -> None:
    assert monitor_source("explicit.monitor", default_sink=lambda: "ignored") == "explicit.monitor"


def test_monitor_source_appends_monitor_suffix() -> None:
    assert monitor_source(None, default_sink=lambda: "alsa_output.usb") == "alsa_output.usb.monitor"


def test_cava_config_requests_raw_16bit_stdout() -> None:
    config = cava_config("alsa_output.usb.monitor", bars=24)

    assert "method = pulse" in config
    assert "source = alsa_output.usb.monitor" in config
    assert "method = raw" in config
    assert "data_format = binary" in config
    assert "bit_format = 16bit" in config
