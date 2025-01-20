import hashlib
import platform
import tempfile
from datetime import datetime
from typing import List, Optional

import joblib
import rich
from PIL import Image, UnidentifiedImageError

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

cachedir = "/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()
mem = joblib.Memory(cachedir, verbose=0)


def clear_cache() -> None:
    mem.clear()


def get_response(msg: str, allowed: Optional[List[str]] = None) -> bool:
    while True:
        res = input(f'{msg} (y/n{"/" if allowed else ""}{"/".join(allowed or [])})? ')
        if res == "y":
            return True
        if res == "n":
            return False
        if allowed and res in allowed:
            return res
        print("Invalid response, please try again")


@mem.cache
def jpeg_openable(file_path: str) -> bool:
    try:
        with Image.open(file_path) as img:
            img.verify()  # verify that it is, in fact an image
            return True
    except UnidentifiedImageError:
        return False


@mem.cache
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


@mem.cache
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


def extract_date_from_filename(date_str: str, pattern: str) -> str:
    # Calculate the length of the date string based on the pattern
    date_length = calculate_pattern_length(pattern)
    # Extract the date part from the filename
    return datetime.strptime(date_str[:date_length], pattern)
