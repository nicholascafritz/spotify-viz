from __future__ import annotations

from dataclasses import dataclass

from spotify_viz.batgrl_app import BatgrlVisualizerApp
from spotify_viz.cava import TapState
from spotify_viz.config import VizConfig
from spotify_viz.mpris import MprisState, NowPlaying
from spotify_viz.signal import SpectrumFrame


@dataclass
class _Cava:
    state: TapState = TapState.CONNECTED
    close_calls: int = 0

    def poll(self) -> SpectrumFrame:
        return SpectrumFrame((24000,) * 24)

    def close(self) -> None:
        self.close_calls += 1


@dataclass
class _Mpris:
    state: MprisState = MprisState.CONNECTED

    def poll(self) -> NowPlaying:
        return NowPlaying("Hardfloor", "Acperience 1", "Playing", 123, 240)

    def toggle_playback(self) -> bool:
        return True


def test_batgrl_app_composes_dense_frame_from_existing_audio_and_mpris_bridges() -> None:
    app = BatgrlVisualizerApp(config=VizConfig(fps=20), cava=_Cava(), mpris=_Mpris())

    frame = app.compose_once(columns=100, rows=30, now=0.0)

    assert frame.width == 100
    assert frame.height == 29
    assert app.controller.state.tick == 1
    assert app.controller.state.now_playing is not None
    assert app.controller.state.now_playing.title == "Acperience 1"


def test_batgrl_app_closes_existing_bridges_once() -> None:
    cava = _Cava()
    app = BatgrlVisualizerApp(config=VizConfig(fps=20), cava=cava, mpris=_Mpris())

    app.close()
    app.close()

    assert cava.close_calls == 1
