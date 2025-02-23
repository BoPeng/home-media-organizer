from pathlib import Path
from typing import Callable, Dict, Generator

import pytest
from PIL import Image
from pytest import TempPathFactory

import home_media_organizer
from home_media_organizer.media_file import MediaFile


@pytest.fixture
def version() -> Generator[str, None, None]:
    """Sample pytest fixture."""
    yield home_media_organizer.__version__


@pytest.fixture(scope="session")
def config_file(tmp_path_factory: TempPathFactory) -> Callable:
    def generate_config_file(rename_format: str = "%Y%m%d_%H%M%S") -> str:
        fn = tmp_path_factory.mktemp("config") / "test.toml"
        with open(fn, "w") as f:
            f.write(
                f"""\
[rename]
format = "{rename_format}"
"""
            )
        return str(fn)

    return generate_config_file


@pytest.fixture(scope="session")
def image_file(tmp_path_factory: TempPathFactory) -> Callable:
    def _generate_image_file(
        filename: str = "test.jpg", exif: Dict[str, str] | None = None, valid: bool = True
    ) -> Path:
        fn = Path(tmp_path_factory.mktemp("image")) / filename
        if valid:
            width, height = 100, 100
            color = (1, 2, 5)
            image = Image.new("RGB", (width, height), color)
            image.save(fn, "JPEG")
        else:
            with open(fn, "w") as f:
                f.write("not an image")

        if exif:
            MediaFile(fn).set_exif(exif, override=True, confirmed=True)
            for k, v in exif.items():
                assert MediaFile(fn).exif[k] == v
        return fn

    return _generate_image_file
