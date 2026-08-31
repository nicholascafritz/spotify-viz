from __future__ import annotations

import pytest

from spotify_viz.config import ConfigError, VizConfig, load_config


def test_defaults_are_calm_and_complete() -> None:
    assert load_config(None) == VizConfig()


def test_toml_overrides_defaults(tmp_path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        'scene = "corridor"\nfps = 24\nmotion_intensity = 0.75\n'
        'show_status = false\naudio_source = "my.monitor"\n',
        encoding="utf-8",
    )

    assert load_config(path) == VizConfig(
        scene="corridor",
        fps=24,
        motion_intensity=0.75,
        show_status=False,
        audio_source="my.monitor",
    )


@pytest.mark.parametrize("body", ["fps = 0\n", "fps = 61\n", "motion_intensity = 1.1\n"])
def test_invalid_values_raise_a_clear_error(tmp_path, body: str) -> None:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(path)
