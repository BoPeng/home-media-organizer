"""Tests for `home_media_organizer` module."""

from typing import Generator

import pytest

import home_media_organizer


@pytest.fixture
def version() -> Generator[str, None, None]:
    """Sample pytest fixture."""
    yield home_media_organizer.__version__


def test_version(version: str) -> None:
    """Sample pytest test function with the pytest fixture as an argument."""
    assert version == "0.3.5"
