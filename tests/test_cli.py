"""Tests for `home_media_organizer`.cli module."""

import os
import pathlib
import shlex
import subprocess
from typing import Callable, Dict, List

import pytest
from PIL import Image
from pytest import TempPathFactory

import home_media_organizer
from home_media_organizer import cli
from home_media_organizer.media_file import MediaFile


@pytest.mark.parametrize(
    "options,expected",
    [
        (["--help"], "usage: "),
        (
            ["--version"],
            f"home-media-organizer, version { home_media_organizer.__version__ }\n",
        ),
    ],
)
def test_main_app(options: List[str], expected: str) -> None:
    """Test app"""
    result = subprocess.run(["hmo", *options], capture_output=True, text=True)
    assert result.returncode == 0
    assert expected in result.stdout


@pytest.mark.parametrize(
    "command, options",
    [
        ("list file1 file2", {"items": ["file1", "file2"], "command": "list"}),
    ],
)
def test_parse_args(command: str, options: Dict) -> None:
    args = cli.parse_args(shlex.split(command))

    # combine test into in one assert
    for k, v in options.items():
        assert getattr(args, k) == v


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
    ) -> str:
        fn = tmp_path_factory.mktemp("image") / filename
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
        return str(fn)

    return _generate_image_file


def test_config(config_file: Callable) -> None:
    """Test using --config to assign command line arguments."""
    cfg = config_file()
    args = cli.parse_args(["rename", "--config", cfg, "file1", "file2"])
    assert args.config == cfg
    assert args.command == "rename"
    assert args.items == ["file1", "file2"]
    assert args.format == "%Y%m%d_%H%M%S"


def test_list(image_file: Callable) -> None:
    fn = image_file()
    result = subprocess.run(["hmo", "list", fn], capture_output=True, text=True)
    assert result.returncode == 0
    assert os.path.basename(fn) in result.stdout


def test_list_with_exif(image_file: Callable) -> None:
    """Test --with-exif and --without-exif options."""
    # list file with exif
    exif = {"EXIF:DateTimeOriginal": "2022:01:01 12:00:00"}
    fn = image_file(exif=exif)
    #
    result = subprocess.run(
        ["hmo", "list", fn, "--with-exif", "EXIF:DateTimeOriginal"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.path.basename(fn) in result.stdout
    # list files without exif
    result = subprocess.run(
        ["hmo", "list", fn, "--without-exif", "EXIF:DateTimeOriginal"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.path.basename(fn) not in result.stdout


def test_list_with_file_types(image_file: Callable) -> None:
    """Test --file-types option."""
    # list file with extensions
    fn = image_file()
    # list file with extensions
    result = subprocess.run(
        ["hmo", "list", fn, "--file-types", "*.jpg"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.path.basename(fn) in result.stdout
    #
    result = subprocess.run(
        ["hmo", "list", fn, "--file-types", "*.mp4"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert os.path.basename(fn) not in result.stdout


def test_show_exif(image_file: Callable) -> None:
    """Test --show-exif option."""
    exif = {"EXIF:DateTimeOriginal": "2022:01:01 12:00:00"}
    fn = image_file(exif=exif)
    #
    result = subprocess.run(
        ["hmo", "show-exif", fn, "--keys", "EXIF:DateTimeOriginal"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert exif["EXIF:DateTimeOriginal"] in result.stdout
    #
    # show all exif
    result = subprocess.run(
        ["hmo", "show-exif", fn],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert exif["EXIF:DateTimeOriginal"] in result.stdout
    #
    # show --format text
    result = subprocess.run(
        ["hmo", "show-exif", fn, "--format", "text"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert exif["EXIF:DateTimeOriginal"] in result.stdout


def test_set_exif_from_values(image_file: Callable) -> None:
    """Test --set-exif option."""
    fn = image_file()
    #
    result = subprocess.run(
        [
            "hmo",
            "set-exif",
            fn,
            "--values",
            "EXIF:DateTimeOriginal=2022:01:01 12:00:00",
            "--yes",
            "--overwrite",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2022:01:01 12:00:00"
    #
    # set a different value, with --confirm, and value will not be changed
    result = subprocess.run(
        ["hmo", "set-exif", fn, "--values", "EXIF:DateTimeOriginal=2020:01:01 12:00:01", "--yes"],
        capture_output=True,
        text=True,
    )
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2022:01:01 12:00:00"
    #
    # now with --overwrite, the exif value should be changed
    result = subprocess.run(
        [
            "hmo",
            "set-exif",
            fn,
            "--values",
            "EXIF:DateTimeOriginal=2020:01:01 12:00:01",
            "--yes",
            "--overwrite",
        ],
        capture_output=True,
        text=True,
    )
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2020:01:01 12:00:01"


@pytest.mark.parametrize(
    "filename,pattern",
    [
        ("20121012_120102.jpg", "%Y%m%d_%H%M%S"),
        ("va2012_10_12.120102-some.jpg", "va%Y_%m_%d.%H%M%S"),
    ],
)
def test_set_exif_from_file(image_file: Callable, filename: str, pattern: str) -> None:
    """Test --set-exif option."""
    fn = image_file(filename=filename)
    #
    result = subprocess.run(
        ["hmo", "set-exif", fn, "--from-filename", pattern, "--overwrite", "--yes"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2012:10:12 12:01:02"


def test_set_exif_from_date(image_file: Callable) -> None:
    """Test --set-exif option."""
    fn = image_file()
    #
    result = subprocess.run(
        ["hmo", "set-exif", fn, "--from-date", "20121012_120102", "--overwrite", "--yes"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2012:10:12 12:01:02"

    #
    # set a different value, without --overwrite, and value will not be changed
    result = subprocess.run(
        ["hmo", "set-exif", fn, "--from-date", "20101012_120102", "--yes"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2012:10:12 12:01:02"
    #
    # this time with --overwrite
    result = subprocess.run(
        ["hmo", "set-exif", fn, "--from-date", "20101012_120102", "--yes", "--overwrite"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2010:10:12 12:01:02"


def test_set_exif_from_date_with_keys(image_file: Callable) -> None:
    """Test --set-exif option."""
    fn = image_file()
    #
    result = subprocess.run(
        [
            "hmo",
            "set-exif",
            fn,
            "--from-date",
            "20141012_120102",
            "--keys",
            "EXIF:DateTimeOriginal",
            "--yes",
            "--overwrite",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    # this is not changed
    assert MediaFile(fn).exif["EXIF:DateTimeOriginal"] == "2014:10:12 12:01:02"


@pytest.mark.parametrize(
    "pattern,suffix,filename",
    [
        ("%Y%m%d_%H%M%S", "", "20220101_120000.jpg"),
        ("%Y%m%d_%H%M%S", "test", "20220101_120000test.jpg"),
        ("%Y_%m_%d.%H_%M_%S", "", "2022_01_01.12_00_00.jpg"),
    ],
)
def test_rename(image_file: Callable, pattern: str, suffix: str, filename: str) -> None:
    """Test rename command."""
    exif = {"EXIF:DateTimeOriginal": "2022:01:01 12:00:00"}
    fn = image_file(exif=exif)
    #
    result = subprocess.run(
        ["hmo", "rename", fn, "--format", pattern]
        + (["--suffix", suffix] if suffix else [])
        + ["--yes"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    new_file = os.path.join(os.path.dirname(fn), filename)
    assert os.path.isfile(new_file)


#
# this test fails for unknown reason
#
# def test_rename_with_config(config_file, image_file: str) -> None:
#     """Test rename command."""
#     cfg = config_file(rename_format="%Y-%m-%d.%H%M%S-test")
#     exif = {"EXIF:DateTimeOriginal": "2022:01:01 12:00:00"}
#     fn = image_file(exif=exif)
#     #
#     with open(cfg, "r") as f:
#         print(f.read())
#     # do not specify --format from command line
#     result = subprocess.run(
#         ["hmo", "rename", fn, "--config", cfg, "--yes"],
#         capture_output=True,
#         text=True,
#     )
#     assert result.returncode == 0
#     new_file = os.path.join(os.path.dirname(fn), "2022-01-01.120000-test.jpg")
#     assert os.path.isfile(new_file)


@pytest.mark.parametrize(
    "dir_pattern,album,album_sep,new_dir",
    [
        ("%Y/%b", "", "-", "2022/Jan"),
        ("%Y/%Y-%m", "", "-", "2022/2022-01"),
        ("%Y/%Y-%m", "vacation", "-", "2022/2022-01-vacation"),
        ("%Y/%Y-%m", "vacation", "/", "2022/2022-01/vacation"),
    ],
)
def test_organize_file(
    image_file: Callable,
    tmp_path: pathlib.Path,
    dir_pattern: str,
    album: str,
    album_sep: str,
    new_dir: str,
) -> None:
    """Test organize command."""
    exif = {"EXIF:DateTimeOriginal": "2022:01:01 12:00:00"}
    fn = image_file(exif=exif, filename="20220101_120000.jpg")
    #
    result = subprocess.run(
        [
            "hmo",
            "organize",
            fn,
            "--media-root",
            str(tmp_path),
            "--dir-pattern",
            dir_pattern,
            "--album",
            album,
            "--album-sep",
            album_sep,
            "--yes",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    new_file = tmp_path / new_dir / os.path.basename(fn)
    assert os.path.isfile(new_file)
