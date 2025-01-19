"""Tests for `home_media_organizer`.cli module."""

import shlex
import subprocess
from typing import List

import pytest

import home_media_organizer
from home_media_organizer import cli


@pytest.mark.parametrize(
    "options,expected",
    [
        # this will generate an error
        # ([], "usage: "),
        (["--help"], "usage: "),
        (
            ["--version"],
            f"home-media-organizer, version { home_media_organizer.__version__ }\n",
        ),
    ],
)
def test_main_app(options: List[str], expected: str) -> None:
    """Test app"""
    result = subprocess.run(["hmo"] + options, capture_output=True, text=True)
    assert result.returncode == 0
    assert expected in result.stdout


@pytest.mark.parametrize(
    "command, options",
    [
        ("list file1 file2", {"items": ["file1", "file2"]}),
    ],
)
def test_parse_args(command, options):
    args = cli.parse_args(shlex.split(command))

    # combine test into in one assert
    for k, v in options.items():
        assert getattr(args, k) == v
