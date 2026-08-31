from __future__ import annotations

import subprocess
import sys


def test_module_help_exits_successfully() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "spotify_viz", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Audio-reactive" in completed.stdout
