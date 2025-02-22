import hashlib
import json
import os
import platform
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from logging import Logger
from typing import Any, Dict, Generator, List

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
    tags: Dict[str, Any]

    def __str__(self) -> str:
        """Return presentation of tag in manifest file"""
        return f"{self.filename}\t{self.hash_value}\t{' '.join(self.tags.keys())}"


class Manifest:
    def __init__(self: "Manifest", filename: str, logger: Logger | None = None) -> None:
        self.database_path = filename
        self.logger = logger
        self.cache = {}
        self._init_db()

    @contextmanager
    def _get_connection(self: "Manifest") -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.database_path)
        # Enable JSON support
        conn.execute("PRAGMA journal_mode=WAL")
        # Register JSON functions for better JSON handling
        sqlite3.register_adapter(dict, json.dumps)
        sqlite3.register_converter("JSON", json.loads)
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self: "Manifest") -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS manifest (
                    filename TEXT PRIMARY KEY,
                    hash_value TEXT,
                    tags JSON
                )
            """
            )
            conn.commit()

    def _get_item(self: "Manifest", filename: str) -> ManifestItem | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT filename, hash_value, tags FROM manifest WHERE filename = ?",
                (os.path.abspath(filename),),
            )
            row = cursor.fetchone()
            if row:
                return ManifestItem(
                    filename=row[0], hash_value=row[1], tags=json.loads(row[2]) if row[2] else {}
                )
        return None

    def get_hash(self: "Manifest", filename: str, default: str | None = None) -> str | None:
        item = self._get_item(filename)
        return item.hash_value if item else default

    def set_hash(self: "Manifest", filename: str, signature: str) -> None:
        abs_path = os.path.abspath(filename)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO manifest (filename, hash_value, tags)
                VALUES (?, ?, ?)
                ON CONFLICT(filename) DO UPDATE SET hash_value = ?
            """,
                (abs_path, signature, {}, signature),
            )
            conn.commit()

    def get_tags(self: "Manifest", filename: str) -> Dict[str, Any]:
        if filename in self.cache:
            return self.cache[filename].tags
        item = self._get_item(filename)
        self.cache[filename] = item
        return item.tags if item else {}

    def add_tags(self: "Manifest", filename: str, tags: Dict[str, Any] | List[str]) -> None:
        abs_path = os.path.abspath(filename)
        if not tags:
            return
        if isinstance(tags, list):
            tags = {x: {} for x in tags}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Use JSON_PATCH or JSON_INSERT to merge the tags
            # print(f"add {abs_path=} {tags=}")
            cursor.execute(
                """
                INSERT INTO manifest (filename, hash_value, tags)
                VALUES (?, '', ?)
                ON CONFLICT(filename) DO UPDATE
                SET tags = json_patch(
                    COALESCE(tags, ?), ?
                )
            """,
                (abs_path, tags, {}, tags),
            )
            self.cache.pop(filename, None)
            conn.commit()

    def set_tags(self: "Manifest", filename: str, tags: Dict[str, Any] | List[str]) -> None:
        abs_path = os.path.abspath(filename)
        if isinstance(tags, list):
            tags = {x: {} for x in tags}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if not tags:
                cursor.execute(
                    """
                    INSERT INTO manifest (filename, hash_value, tags)
                    VALUES (?, '', NULL)
                    ON CONFLICT(filename) DO UPDATE SET tags = NULL
                    """,
                    (abs_path,),
                )
            else:
                cursor.execute(
                    """
                INSERT INTO manifest (filename, hash_value, tags)
                VALUES (?, '', ?)
                ON CONFLICT(filename) DO UPDATE SET tags = ?
                """,
                    (abs_path, tags, tags),
                )
            self.cache.pop(filename, None)
            conn.commit()

    def find_by_tags(self: "Manifest", tag_names: List[str]) -> List[ManifestItem]:
        """Find all items that have a specific tag"""
        res: Dict[str, ManifestItem] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if not tag_names:
                cursor.execute(
                    """
                    SELECT filename, hash_value, tags
                    FROM manifest WHERE tags IS NOT NULL
                    """
                )
                res = {
                    row[0]: ManifestItem(
                        filename=row[0], hash_value=row[1], tags=json.loads(row[2])
                    )
                    for row in cursor.fetchall()
                }
            else:
                for tag_name in tag_names:
                    cursor.execute(
                        """
                        SELECT filename, hash_value, tags
                        FROM manifest
                        WHERE json_extract(tags, '$.' || ?) IS NOT NULL
                    """,
                        (tag_name,),
                    )
                res |= {
                    row[0]: ManifestItem(
                        filename=row[0], hash_value=row[1], tags=json.loads(row[2])
                    )
                    for row in cursor.fetchall()
                }
        if self.logger:
            self.logger.debug(f"Found {len(res)} items with tag {tag_names}")
        self.cache |= res
        return list(res.values())
