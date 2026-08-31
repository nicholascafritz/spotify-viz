from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when spotify-viz configuration is invalid."""


@dataclass(frozen=True, slots=True)
class VizConfig:
    scene: str = "corridor"
    fps: int = 30
    motion_intensity: float = 0.65
    show_status: bool = True
    audio_source: str | None = None


def load_config(path: Path | None) -> VizConfig:
    if path is None:
        return VizConfig()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ConfigError(f"cannot read config: {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML: {error}") from error

    config = VizConfig(
        scene=data.get("scene", "corridor"),
        fps=data.get("fps", 30),
        motion_intensity=data.get("motion_intensity", 0.65),
        show_status=data.get("show_status", True),
        audio_source=data.get("audio_source"),
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
