import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import Any, Dict, Generator, List

from diskcache import Cache  # type: ignore
from pyparsing import (
    CharsNotIn,
    Keyword,
    ParserElement,
    ParseResults,
    Word,
    alphanums,
    infix_notation,
    opAssoc,
)
from rich.prompt import Prompt


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


hmo_home = Path.home() / ".ai-marketplace-monitor"
hmo_home.mkdir(parents=True, exist_ok=True)
cache_dir = hmo_home / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)
cache = Cache(cache_dir, verbose=0)


def clear_cache(tag: str) -> None:
    cache.evict(tag)


def get_response(msg: str) -> bool:
    return Prompt.ask(msg, choices=["y", "n"], default="y") == "y"


@cache.memoize(tag="signature")
def get_file_hash(file_path: Path) -> str:
    return calculate_file_hash(file_path)


def calculate_file_hash(file_path: Path) -> str:
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


ParserElement.enable_packrat()
double_quoted_string = ('"' + CharsNotIn('"').leaveWhitespace() + '"').setParseAction(
    lambda t: t[1]
)  # removes quotes, keeps only the content
single_quoted_string = ("'" + CharsNotIn("'").leaveWhitespace() + "'").setParseAction(
    lambda t: t[1]
)  # removes quotes, keeps only the content

special_chars = "-_=+.<>"
unquoted_string = Word(alphanums + special_chars)

operand = double_quoted_string | single_quoted_string | unquoted_string
and_op = Keyword("AND")
or_op = Keyword("OR")

# Define the grammar for parsing
expr = infix_notation(
    operand,
    [
        (and_op, 2, opAssoc.LEFT),
        (or_op, 2, opAssoc.LEFT),
    ],
)


@dataclass
class ManifestItem:
    filename: str
    hash_value: str
    tags: Dict[str, Any]

    def __str__(self) -> str:
        """Return presentation of tag in manifest file"""
        return f"{self.filename}\t{self.hash_value}\t{' '.join(self.tags.keys())}"


class Manifest:
    def __init__(
        self: "Manifest", filename: str | None = None, logger: Logger | None = None
    ) -> None:
        self.logger = logger
        self.cache: Dict[Path, ManifestItem] = {}
        self.init_db(filename)

    def init_db(self: "Manifest", filename: str | None) -> None:
        self.database_path = str(hmo_home / "manifest.db") if filename is None else filename
        self._init_db()

    def get_all_tags(self: "Manifest") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT tags FROM manifest")
            return [json.loads(row[0]) for row in cursor.fetchall()]

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

    def _get_item(self: "Manifest", filename: Path) -> ManifestItem | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT filename, hash_value, tags FROM manifest WHERE filename = ?",
                (filename.resolve(),),
            )
            row = cursor.fetchone()
            if row:
                return ManifestItem(
                    filename=row[0], hash_value=row[1], tags=json.loads(row[2]) if row[2] else {}
                )
        return None

    def get_hash(self: "Manifest", filename: Path, default: str | None = None) -> str | None:
        item = self._get_item(filename)
        return item.hash_value if item else default

    def set_hash(self: "Manifest", filename: Path, signature: str) -> None:
        abs_path = filename.resolve()
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

    def get_tags(self: "Manifest", filename: Path) -> Dict[str, Any]:
        if filename in self.cache:
            return self.cache[filename].tags
        item = self._get_item(filename)
        if item:
            self.cache[filename] = item
            return item.tags
        return {}

    def add_tags(self: "Manifest", filename: Path, tags: Dict[str, Any] | List[str]) -> None:
        abs_path = filename.resolve()
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

    def set_tags(self: "Manifest", filename: Path, tags: Dict[str, Any] | List[str]) -> None:
        abs_path = filename.resolve()
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

    def remove_tags(self: "Manifest", filename: Path, tags: List[str]) -> None:
        abs_path = filename.resolve()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for tag in tags:
                cursor.execute(
                    """
                    UPDATE manifest
                    SET tags = json_remove(tags, '$.' || ?)
                    WHERE filename = ?
                    """,
                    (tag, abs_path),
                )
            conn.commit()
            self.cache.pop(filename, None)

    def find_by_tag(self: "Manifest", tag_name: str) -> List[ManifestItem]:
        """Find all items that have a specific tag."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT filename, hash_value, tags
                FROM manifest
                WHERE json_extract(tags, '$.' || ?) IS NOT NULL
                """,
                (tag_name,),
            )
            res = {
                row[0]: ManifestItem(filename=row[0], hash_value=row[1], tags=json.loads(row[2]))
                for row in cursor.fetchall()
            }
            self.cache |= res
            if self.logger:
                self.logger.debug(f"Found {len(res)} items with tag {tag_name}")
            return list(res.values())

    def get_files_with_any_tag(self: "Manifest") -> List[ManifestItem]:
        """Get files with any tag"""
        res: Dict[Path, ManifestItem] = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT filename, hash_value, tags
                FROM manifest WHERE tags IS NOT NULL
                """
            )
            res = {
                Path(row[0]): ManifestItem(
                    filename=row[0], hash_value=row[1], tags=json.loads(row[2])
                )
                for row in cursor.fetchall()
            }
            self.cache |= res
            return list(res.values())

    def find_by_tags(self: "Manifest", tag_names: List[str]) -> List[ManifestItem]:
        """Find all items that have a specific tag."""
        if not tag_names:
            return self.get_files_with_any_tag()

        # inside tag_names, there can be AND.
        expression = " OR ".join(tag_names)

        # parse the expression
        try:
            parsed = expr.parseString(expression, parseAll=True)[0]
        except Exception as e:
            if self.logger:
                self.logger.error(f"Invalid expression: {expr}")
                self.logger.error(f"Error: {e}")
                self.logger.error(f"Parsed: {parsed}")
            return []

        def evaluate_expression(parsed_expression: str | ParseResults) -> List[ManifestItem]:
            if isinstance(parsed_expression, str):
                return self.find_by_tag(parsed_expression)

            if len(parsed_expression) == 1:
                return evaluate_expression(parsed_expression[0])

            if parsed_expression[-2] == "AND":
                set_a = evaluate_expression(parsed_expression[:-2])
                set_b = evaluate_expression(parsed_expression[-1])
                common_keys = {x.filename for x in set_a} & {x.filename for x in set_b}
                return [x for x in set_a if x.filename in common_keys]

            if parsed_expression[-2] == "OR":
                set_a = evaluate_expression(parsed_expression[:-2])
                set_b = evaluate_expression(parsed_expression[-1])
                return list(
                    ({x.filename: x for x in set_a} | {x.filename: x for x in set_b}).values()
                )

            if self.logger:
                self.logger.error(f"Invalid expression: {parsed_expression}")
            return []

        return evaluate_expression(parsed)


# create a default manifest database, can be set to another path
manifest = Manifest()
