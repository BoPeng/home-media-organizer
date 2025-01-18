"""Tests for `home_media_organizer`.cli module."""

from typing import List

import pytest

import home_media_organizer
from home_media_organizer import cli


@pytest.mark.parametrize(
    "options,expected",
    [
        ([], "home_media_organizer.cli.main"),
        (["--help"], "Usage: "),
        (
            ["--version"],
            f"home-media-organizer, version { home_media_organizer.__version__ }\n",
        ),
    ],
)
def test_command_line_interface(options: List[str], expected: str) -> None:
    """Test the CLI."""
    result = runner.invoke(cli.app, options)
    assert result.exit_code == 0
    assert expected in result.stdout
