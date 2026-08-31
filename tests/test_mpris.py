from spotify_viz.mpris import NowPlaying, parse_metadata


def test_parse_metadata_normalizes_playerctl_lines() -> None:
    assert parse_metadata("Hardfloor\tAcperience 1\tPlaying\t123") == NowPlaying(
        artist="Hardfloor", title="Acperience 1", status="Playing", position=123
    )


def test_parse_metadata_returns_none_for_unavailable_player() -> None:
    assert parse_metadata("") is None
