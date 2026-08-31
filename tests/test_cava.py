from __future__ import annotations

import struct

from spotify_viz.cava import RawFrameParser, TapState, cava_config, cava_template, monitor_source, tap_state_for_process


def test_explicit_audio_source_wins() -> None:
    assert monitor_source("explicit.monitor", default_sink=lambda: "ignored") == "explicit.monitor"


def test_monitor_source_appends_monitor_suffix() -> None:
    assert monitor_source(None, default_sink=lambda: "alsa_output.usb") == "alsa_output.usb.monitor"


def test_cava_config_requests_raw_16bit_stdout() -> None:
    assert "source = {source}" in cava_template()
    config = cava_config("alsa_output.usb.monitor", bars=24)

    assert "method = pulse" in config
    assert "source = alsa_output.usb.monitor" in config
    assert "method = raw" in config
    assert "raw_target = /dev/stdout" in config
    assert "data_format = binary" in config
    assert "bit_format = 16bit" in config


def test_raw_parser_buffers_split_reads_and_never_emits_partial_frames() -> None:
    parser = RawFrameParser(bars=3)
    payload = struct.pack("<3H", 1, 2, 65535)

    assert parser.feed(payload[:4]) == []
    assert [frame.values for frame in parser.feed(payload[4:])] == [(1, 2, 65535)]


def test_finished_cava_process_becomes_lost_not_an_exception() -> None:
    assert tap_state_for_process(None, received_frame=False) is TapState.STALE
    assert tap_state_for_process(1, received_frame=False) is TapState.LOST
    assert tap_state_for_process(0, received_frame=True) is TapState.CONNECTED
