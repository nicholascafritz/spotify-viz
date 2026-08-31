from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys

from spotify_viz.app import VisualizerApp, frame_delay, sanitize_status_text
from spotify_viz.cava import TapState
from spotify_viz.config import VizConfig
from spotify_viz.mpris import MprisState, NowPlaying
from spotify_viz.scene import ServerCathedralScene
from spotify_viz.signal import SpectrumFrame


@dataclass
class FakeCava:
    state: TapState = TapState.CONNECTED
    frame: SpectrumFrame | None = SpectrumFrame((25000,) * 24)
    closed: bool = False

    def poll(self) -> SpectrumFrame | None:
        return self.frame

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeMpris:
    state: MprisState = MprisState.CONNECTED
    now_playing: NowPlaying | None = NowPlaying("Hardfloor", "Acperience 1", "Playing", 123, 240)
    toggles: int = 0

    def poll(self) -> NowPlaying | None:
        return self.now_playing

    def toggle_playback(self) -> bool:
        self.toggles += 1
        return True


class FakeTerminal:
    def __init__(self) -> None:
        self.frames: list[str] = []

    def draw(self, content: str) -> None:
        self.frames.append(content)


def make_app(*, cava: FakeCava | None = None, mpris: FakeMpris | None = None, size: tuple[int, int] = (100, 30)) -> tuple[VisualizerApp, FakeTerminal, FakeCava, FakeMpris]:
    fake_cava = cava or FakeCava()
    fake_mpris = mpris or FakeMpris()
    terminal = FakeTerminal()
    app = VisualizerApp(
        config=VizConfig(fps=20),
        cava=fake_cava,
        mpris=fake_mpris,
        terminal=terminal,
        size_provider=lambda: size,
        scenes=[ServerCathedralScene(seed=1), ServerCathedralScene(seed=2)],
    )
    return app, terminal, fake_cava, fake_mpris


def test_module_help_exits_successfully() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "spotify_viz", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Audio-reactive" in completed.stdout


def test_frame_delay_caps_configured_fps() -> None:
    assert frame_delay(fps=20, started=10.0, now=10.02) == 0.03
    assert frame_delay(fps=20, started=10.0, now=10.2) == 0.0


def test_no_mpris_keeps_scene_running_with_no_signal_status() -> None:
    app, terminal, _, _ = make_app(mpris=FakeMpris(state=MprisState.NO_SIGNAL, now_playing=None))

    assert app.step(now=0.0) is True
    assert terminal.frames
    assert "NO SIGNAL" in terminal.frames[-1]


def test_lost_audio_uses_quiet_scene_and_explicit_status() -> None:
    app, terminal, _, _ = make_app(cava=FakeCava(state=TapState.LOST, frame=None))

    app.step(now=0.0)

    assert "AUDIO TAP LOST" in terminal.frames[-1]


def test_stale_audio_settles_the_existing_scene_instead_of_reprocessing_last_frame() -> None:
    app, _, _, _ = make_app(cava=FakeCava(state=TapState.STALE, frame=SpectrumFrame((65535,) * 24)))
    app.state.bands = app.state.bands.__class__(0.5, 0.4, 0.3, 0.4, False)

    app.step(now=0.0)

    assert app.state.bands.bass == 0.4
    assert round(app.state.bands.mid, 2) == 0.32
    assert app.state.bands.treble == 0.24


def test_controls_toggle_only_available_ncspot_and_cycle_scene_help_and_quit() -> None:
    app, _, _, mpris = make_app()

    assert app.handle_key(b" ") is True
    assert mpris.toggles == 1
    assert app.handle_key(b"m") is True
    assert app.state.active_scene == 1
    assert app.handle_key(b"h") is True
    assert app.state.help_visible is True
    assert app.handle_key(b"q") is False


def test_space_is_ignored_when_ncspot_is_unavailable() -> None:
    app, _, _, mpris = make_app(mpris=FakeMpris(state=MprisState.NO_SIGNAL, now_playing=None))

    assert app.handle_key(b" ") is True
    assert mpris.toggles == 0


def test_compact_layout_hides_variable_status_readout() -> None:
    app, terminal, _, _ = make_app(size=(60, 12))

    app.step(now=0.0)

    assert "Hardfloor" not in terminal.frames[-1]


def test_status_text_removes_terminal_controls_and_clips_display_width() -> None:
    assert sanitize_status_text("bad\x1b]52;clipboard\x07\ntrack", width=11) == "bad]52;clip"


def test_cleanup_owns_only_cava_child() -> None:
    app, _, cava, _ = make_app()

    app.close()

    assert cava.closed is True
