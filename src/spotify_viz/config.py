from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib


PALETTE_KEYS = {"background", "structure", "reactive", "void", "atmosphere", "signal", "warning", "error"}
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


class ConfigError(ValueError):
    """Raised when spotify-viz configuration is invalid."""


@dataclass(frozen=True, slots=True)
class VizConfig:
    scene: str = "corridor"
    fps: int = 30
    motion_intensity: float = 0.65
    show_status: bool = True
    audio_source: str | None = None
    palette: tuple[tuple[str, str], ...] = ()


def default_config_path() -> Path:
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_root / "spotify-viz" / "config.toml"


def load_config(path: Path | None) -> VizConfig:
    config_path = path or default_config_path()
    if not config_path.exists() and path is None:
        return VizConfig()
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read config: {config_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML: {error}") from error

    allowed = {"scene", "fps", "motion_intensity", "show_status", "audio_source", "palette"}
    unknown = set(data) - allowed
    if unknown:
        raise ConfigError(f"unsupported configuration keys: {', '.join(sorted(unknown))}")
    palette_data = data.get("palette", {})
    if not isinstance(palette_data, dict):
        raise ConfigError("palette must be a TOML table")
    unknown_palette = set(palette_data) - PALETTE_KEYS
    if unknown_palette:
        raise ConfigError(f"unsupported palette keys: {', '.join(sorted(unknown_palette))}")
    if any(not isinstance(value, str) or not HEX_COLOR.fullmatch(value) for value in palette_data.values()):
        raise ConfigError("palette values must use #RRGGBB")
    palette = tuple(sorted(palette_data.items()))
    config = VizConfig(
        scene=data.get("scene", "corridor"),
        fps=data.get("fps", 30),
        motion_intensity=data.get("motion_intensity", 0.65),
        show_status=data.get("show_status", True),
        audio_source=data.get("audio_source"),
        palette=palette,
    )
    if config.scene != "corridor":
        raise ConfigError("scene must be 'corridor'")
    if not isinstance(config.fps, int) or not 1 <= config.fps <= 60:
        raise ConfigError("fps must be an integer from 1 through 60")
    if not isinstance(config.motion_intensity, (int, float)) or not 0 <= config.motion_intensity <= 1:
        raise ConfigError("motion_intensity must be from 0 through 1")
    if not isinstance(config.show_status, bool):
        raise ConfigError("show_status must be true or false")
    if config.audio_source is not None and not isinstance(config.audio_source, str):
        raise ConfigError("audio_source must be a string")
    return config
