from __future__ import annotations

from dataclasses import dataclass
from threading import Event
import time

from spotify_viz.mpris import MprisBridge, MprisState, NowPlaying, parse_metadata


@dataclass
class Result:
    returncode: int = 0
    stdout: str = "Hardfloor\tAcperience 1\tPlaying\t123\t240"


def test_parse_metadata_normalizes_playerctl_lines_with_duration() -> None:
    assert parse_metadata("Hardfloor\tAcperience 1\tPlaying\t123\t240") == NowPlaying(
        artist="Hardfloor", title="Acperience 1", status="Playing", position=123, duration=240
    )


def test_parse_metadata_converts_mpris_microseconds_to_seconds() -> None:
    assert parse_metadata("Hardfloor\tAcperience 1\tPlaying\t123000000\t240000000") == NowPlaying(
        artist="Hardfloor", title="Acperience 1", status="Playing", position=123, duration=240
    )


def test_parse_metadata_returns_none_for_unavailable_player() -> None:
    assert parse_metadata("") is None


def test_metadata_failure_retains_last_track_with_stale_state() -> None:
    responses = iter([Result(), Result(returncode=1, stdout="")])
    bridge = MprisBridge(runner=lambda _: next(responses))

    assert bridge.poll().title == "Acperience 1"
    assert bridge.poll().title == "Acperience 1"
    assert bridge.state is MprisState.STALE


def test_unavailable_ncspot_is_no_signal_and_toggle_is_scoped() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> Result:
        calls.append(command)
        return Result(returncode=1, stdout="")

    bridge = MprisBridge(runner=runner)
    assert bridge.poll() is None
    assert bridge.state is MprisState.NO_SIGNAL
    assert bridge.toggle_playback() is False
    assert calls == [
        ["playerctl", "--player=ncspot", "metadata", "--format", "{{artist}}\t{{title}}\t{{status}}\t{{position}}\t{{mpris:length}}"],
        ["playerctl", "--player=ncspot", "play-pause"],
    ]


def test_nonblocking_poll_returns_cached_metadata_while_runner_waits() -> None:
    started, release = Event(), Event()

    def runner(_: list[str]) -> Result:
        started.set()
        release.wait(timeout=1)
        return Result()

    bridge = MprisBridge(runner=runner)
    before = time.monotonic()
    assert bridge.poll_nonblocking() is None
    assert time.monotonic() - before < 0.05
    assert started.wait(timeout=1)
    assert bridge.poll_nonblocking() is None
    release.set()
    assert bridge.wait_for_poll(timeout=1).title == "Acperience 1"
    bridge.close()
