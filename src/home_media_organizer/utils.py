import hashlib
import os
import platform
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import rich
from diskcache import Cache  # type: ignore
from PIL import Image, UnidentifiedImageError
from rich.prompt import Prompt

try:
    import ffmpeg  # type: ignore
except ImportError:
    ffmpeg = None


class CompareBy(Enum):
    CONTENT = "content"
    NAME_AND_CONTENT = "name_and_content"


class CompareOutput(Enum):
    A = "A"
    B = "B"
    BOTH = "Both"


class OrganizeOperation(Enum):
    MOVE = "move"
    COPY = "copy"


cachedir = "/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()
cache = Cache(cachedir, verbose=0)


def clear_cache(tag: str) -> None:
    cache.evict(tag)


def get_response(msg: str) -> bool:
    return Prompt.ask(msg, choices=["y", "n"], default="y") == "y"


@cache.memoize(tag="validate")
def jpeg_openable(file_path: str) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()  # verify that it is, in fact an image
            return True
    except UnidentifiedImageError:
        return False


@cache.memoize(tag="validate")
def mpg_playable(file_path: str) -> bool:
    if not ffmpeg:
        rich.print("[red]ffmpeg not installed, skip[/red]")
        return True
    try:
        # Try to probe the file using ffmpeg
        probe = ffmpeg.probe(file_path)

        # Check if 'streams' exist in the probe result
        if "streams" in probe:
            video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
            if len(video_streams) > 0:
                return True
        return False
    except ffmpeg.Error:
        return False


@cache.memoize(tag="signature")
def get_file_hash(file_path: str) -> str:
    return calculate_file_hash(file_path)


def calculate_file_hash(file_path: str) -> str:
    sha_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha_hash.update(byte_block)
    return sha_hash.hexdigest()


def calculate_pattern_length(pattern: str) -> int:
    length = 0
    i = 0
    while i < len(pattern):
        if pattern[i] == "%":
            if pattern[i + 1] in ["Y"]:
                length += 4
            elif pattern[i + 1] in ["m", "d", "H", "M", "S"]:
                length += 2
            i += 2
        else:
            length += 1
            i += 1
    return length


def extract_date_from_filename(date_str: str, pattern: str) -> datetime:
    # Calculate the length of the date string based on the pattern
    date_length = calculate_pattern_length(pattern)
    # Extract the date part from the filename
    return datetime.strptime(date_str[:date_length], pattern)


def merge_dicts(dicts: list) -> dict:
    """Merge a list of dictionaries into a single dictionary, including nested dictionaries.

    :param dicts: A list of dictionaries to merge.
    :return: A single merged dictionary.
    """

    def merge(d1: dict, d2: dict) -> dict:
        for key, value in d2.items():
            if key in d1:
                if isinstance(d1[key], dict) and isinstance(value, dict):
                    d1[key] = merge(d1[key], value)
                elif isinstance(d1[key], list) and isinstance(value, list):
                    d1[key].extend(value)
                else:
                    d1[key] = value
            else:
                d1[key] = value
        return d1

    result: Dict[str, Any] = {}
    for dictionary in dicts:
        result = merge(result, dictionary)
    return result


@dataclass
class ManifestItem:
    filename: str
    hash_value: str
    tags: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Return presentation of tag in manifest file"""
        return f"{self.filename}\t{self.hash_value}\t{' '.join(self.tags)}"


class Manifest:
    def __init__(self: "Manifest", filename: str | None) -> None:
        self.filename = filename
        self.manifest: Dict[str, ManifestItem] = {}
        if self.filename and os.path.isfile(self.filename):
            self.load()

    def load(self: "Manifest") -> None:
        assert self.filename is not None
        with open(self.filename, "r") as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    filename, hash_value, tags = line.split("\t")
                    self.manifest[filename] = ManifestItem(
                        filename=filename, hash_value=hash_value, tags=tags.split()
                    )

    def get_hash(self: "Manifest", filename: str, default: str | None = None) -> str | None:
        if filename in self.manifest:
            return self.manifest[filename].hash_value
        return default

    def set_hash(self: "Manifest", filename: str, signature: str) -> None:
        if filename in self.manifest:
            self.manifest[filename].hash_value = signature
        else:
            self.manifest[filename] = ManifestItem(
                filename=filename, hash_value=signature, tags=[]
            )

    def __getitem__(self: "Manifest", filename: str) -> ManifestItem:
        """Return the manifest item with given filename"""
        if filename not in self.manifest:
            self.manifest[filename] = ManifestItem(filename=filename, hash_value="", tags=[])
        return self.manifest[filename]

    def get_tags(self: "Manifest", filename: str) -> List[str]:
        if filename in self.manifest:
            return self.manifest[filename].tags
        return []

    def add_tags(self: "Manifest", filename: str, tags: List[str]) -> None:
        if filename in self.manifest:
            self.manifest[filename].tags = list(set(self.manifest[filename].tags + tags))
        else:
            self.manifest[filename] = ManifestItem(filename=filename, hash_value="", tags=tags)

    def save(self: "Manifest") -> None:
        assert self.filename is not None
        with open(self.filename, "w") as f:
            for filename in sorted(self.manifest.keys()):
                f.write(str(self.manifest[filename]) + "\n")
