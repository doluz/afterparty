"""The skill's API client runs on a plain Python with no packages."""

import subprocess
import sys
from pathlib import Path

CLIENT = (
    Path(__file__).resolve().parent.parent / "skills" / "afterparty" / "scripts" / "afterparty.py"
)


def test_client_help_lists_every_command():
    out = subprocess.run(
        [sys.executable, "-I", str(CLIENT), "--help"], capture_output=True, text=True, check=True
    ).stdout
    for cmd in ("stats", "events", "people", "export", "sync", "follow-up"):
        assert cmd in out


def test_client_refuses_to_run_without_credentials():
    r = subprocess.run(
        [sys.executable, "-I", str(CLIENT), "--url", "http://127.0.0.1:9", "stats"],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin"},
    )
    assert r.returncode != 0
    assert "AFTERPARTY_AUTH" in r.stderr
