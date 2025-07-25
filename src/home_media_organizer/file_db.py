"""File database for efficient file searching and pattern matching."""

import fnmatch
import sqlite3
import threading
import time
from logging import Logger
from pathlib import Path
from typing import List, Optional, Tuple

from .utils import files_db


class FileDatabase:
    """SQLite-based file database for efficient searching."""

    def __init__(self) -> None:
        """Initialize file database.

        Args:
            db_path: Path to database file. Defaults to ~/.home-media-organizer/files.db
        """
        self.db_path = files_db
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    directory TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    indexed_at REAL NOT NULL
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_filename ON files(filename)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_directory ON files(directory)
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS directory_scans (
                    path TEXT PRIMARY KEY,
                    last_scan REAL NOT NULL,
                    last_mtime REAL NOT NULL
                )
            """
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_files(
        self,
        pattern: str,
        search_paths: Optional[List[str | Path]] = None,
        logger: Logger | None = None,
        update_db: bool = False,
    ) -> List[Path]:
        """Search for files matching a pattern.

        Args:
            pattern: Filename pattern (supports wildcards like ff*.jpg)
            search_paths: List of directories to search in. If None, searches current directory only.
            logger: Optional logger for debug messages
            update_db: If True, force database update using timestamp checking

        Returns:
            List of matching file paths, validated to exist
        """
        with self._lock:
            # If no search paths specified, use current directory
            if search_paths is None:
                search_paths = [str(Path.cwd())]

            # Update directories based on strategy
            for search_path in search_paths:
                path_obj = Path(search_path)
                if path_obj.exists() and path_obj.is_dir():
                    if update_db:
                        # Force update using timestamp checking
                        self._update_directory_if_needed(path_obj, logger)
                    else:
                        # Only scan if not in database at all
                        self._scan_if_not_in_database(path_obj, logger)

            # Search database within specified directories and their subdirectories
            with self._get_connection() as conn:
                # Convert all paths to strings for SQLite compatibility
                search_paths_str = [str(Path(p).resolve()) for p in search_paths]

                # Build query to search in directories and their subdirectories
                conditions = []
                params = []
                for path in search_paths_str:
                    # Match exact directory or any subdirectory
                    conditions.append("(directory = ? OR directory LIKE ?)")
                    params.extend([path, path + "/%"])

                query = f"""
                    SELECT path FROM files
                    WHERE {" OR ".join(conditions)}
                    ORDER BY filename
                """
                rows = conn.execute(query, params).fetchall()

                # Filter by pattern and validate existence
                matching_paths = []
                paths_to_remove = []

                for row in rows:
                    file_path = Path(row["path"])
                    filename = file_path.name

                    # Check pattern match
                    if fnmatch.fnmatch(filename, pattern):
                        # Validate file still exists
                        if file_path.exists():
                            matching_paths.append(file_path)
                        else:
                            paths_to_remove.append(str(file_path))

                # Remove non-existent files from database
                if paths_to_remove:
                    placeholders = ",".join("?" * len(paths_to_remove))
                    delete_query = f"DELETE FROM files WHERE path IN ({placeholders})"
                    conn.execute(delete_query, paths_to_remove)
                    conn.commit()

                return matching_paths

    def _scan_if_not_in_database(self, directory: Path, logger: Logger | None = None) -> None:
        """Scan directory only if it's not already in the database."""
        if not directory.exists() or not directory.is_dir():
            return

        dir_str = str(directory.resolve())
        current_time = time.time()

        with self._get_connection() as conn:
            # Check if this directory has ever been scanned
            row = conn.execute(
                "SELECT last_scan FROM directory_scans WHERE path = ?", (dir_str,)
            ).fetchone()

            if row is None:
                # Directory not in database, do initial scan
                if logger:
                    logger.debug(f"Initial scan of new directory: {directory}")
                self._scan_directory(directory, conn, logger=logger)

                # Record the scan
                dir_mtime = directory.stat().st_mtime
                conn.execute(
                    """
                    INSERT INTO directory_scans (path, last_scan, last_mtime)
                    VALUES (?, ?, ?)
                """,
                    (dir_str, current_time, dir_mtime),
                )
                conn.commit()
            elif logger:
                logger.debug(f"Directory {directory} already in database, skipping scan")

    def _update_directory_if_needed(self, directory: Path, logger: Logger | None = None) -> None:
        """Update directory in database if it has been modified since last scan."""
        if not directory.exists() or not directory.is_dir():
            return

        current_time = time.time()

        with self._get_connection() as conn:
            # Get all subdirectories that need updating
            changed_dirs = self._find_changed_directories(directory, conn)

            if changed_dirs:
                if logger:
                    logger.debug(
                        f"Found {len(changed_dirs)} changed directories under {directory}"
                    )

                # Update only the changed directories
                for changed_dir in changed_dirs:
                    self._scan_single_directory(changed_dir, conn, logger=logger)

                    # Update scan record for this specific directory
                    dir_str = str(changed_dir.resolve())
                    dir_mtime = changed_dir.stat().st_mtime
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO directory_scans (path, last_scan, last_mtime)
                        VALUES (?, ?, ?)
                    """,
                        (dir_str, current_time, dir_mtime),
                    )

                conn.commit()
            elif logger:
                logger.debug(f"No changes detected in {directory}")

    def _find_changed_directories(
        self, root_directory: Path, conn: sqlite3.Connection
    ) -> List[Path]:
        """Find all directories under root_directory that have been modified since last scan."""
        changed_dirs = []

        try:
            # Get all directories under the root (including the root itself)
            all_dirs = [root_directory] + [
                item for item in root_directory.rglob("*") if item.is_dir()
            ]

            for directory in all_dirs:
                try:
                    dir_str = str(directory.resolve())
                    current_mtime = directory.stat().st_mtime

                    # Check if this directory is in the database
                    row = conn.execute(
                        "SELECT last_mtime FROM directory_scans WHERE path = ?", (dir_str,)
                    ).fetchone()

                    # Directory needs updating if:
                    # 1. It's not in the database (new directory)
                    # 2. Its mtime is newer than the recorded mtime
                    if row is None or row["last_mtime"] < current_mtime:
                        changed_dirs.append(directory)

                except (OSError, PermissionError):
                    # Skip directories we can't access
                    continue

        except (OSError, PermissionError):
            # If we can't access the root directory, return empty list
            pass

        return changed_dirs

    def _scan_single_directory(
        self, directory: Path, conn: sqlite3.Connection, logger: Logger | None = None
    ) -> None:
        """Scan a single directory (non-recursive) and update database with its files."""
        dir_str = str(directory.resolve())
        if logger:
            logger.debug(f"Scanning single directory {directory}")

        # Remove existing entries for this specific directory only
        conn.execute("DELETE FROM files WHERE directory = ?", (dir_str,))

        # Add files directly in this directory (not subdirectories)
        try:
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        conn.execute(
                            """
                            INSERT INTO files (path, filename, directory, size, mtime, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                str(file_path),
                                file_path.name,
                                str(file_path.parent),
                                stat.st_size,
                                stat.st_mtime,
                                time.time(),
                            ),
                        )
                        if logger:
                            logger.debug(f"Adding {file_path}")
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

    def _scan_directory(
        self, directory: Path, conn: sqlite3.Connection, logger: Logger | None = None
    ) -> None:
        """Scan directory recursively and update database with all files (legacy method)."""
        dir_str = str(directory.resolve())
        if logger:
            logger.debug(f"Scanning directory recursively {directory}")

        # Remove existing entries for all files under this directory tree
        conn.execute("DELETE FROM files WHERE path LIKE ?", (dir_str + "/%",))
        conn.execute("DELETE FROM files WHERE directory = ?", (dir_str,))

        # Add all files in directory tree
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        conn.execute(
                            """
                            INSERT INTO files (path, filename, directory, size, mtime, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                str(file_path),
                                file_path.name,
                                str(file_path.parent),
                                stat.st_size,
                                stat.st_mtime,
                                time.time(),
                            ),
                        )
                        if logger:
                            logger.debug(f"Adding {file_path}")
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

    def update_search_paths(
        self,
        search_paths: List[Path | str],
        logger: Logger | None = None,
        force_update: bool = False,
    ) -> None:
        """Update database with files from specified search paths.

        Args:
            search_paths: List of directory paths to scan and index
            logger: Optional logger for debug messages
            force_update: If True, force update using timestamp checking
        """
        with self._lock:
            for search_path in search_paths:
                path_obj = Path(search_path)
                if path_obj.exists() and path_obj.is_dir():
                    if force_update:
                        self._update_directory_if_needed(path_obj, logger=logger)
                    else:
                        self._scan_if_not_in_database(path_obj, logger=logger)

    def clear_database(self) -> None:
        """Clear all entries from the database."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM files")
                conn.execute("DELETE FROM directory_scans")
                conn.commit()

    def get_stats(self) -> Tuple[int, int]:
        """Get database statistics.

        Returns:
            Tuple of (total_files, total_directories)
        """
        with self._get_connection() as conn:
            file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            dir_count = conn.execute("SELECT COUNT(*) FROM directory_scans").fetchone()[0]
            return file_count, dir_count


# Global instance
_file_db: Optional[FileDatabase] = None
_db_lock = threading.Lock()


def get_file_database() -> FileDatabase:
    """Get global file database instance."""
    global _file_db
    with _db_lock:
        if _file_db is None:
            _file_db = FileDatabase()
        return _file_db


def search_files_with_database(
    pattern: str,
    search_paths: Optional[List[Path | str]] = None,
    logger: Logger | None = None,
    update_db: bool = False,
) -> List[Path]:
    """Search for files using the database.

    Args:
        pattern: Filename pattern (supports wildcards like ff*.jpg)
        search_paths: List of directories to search in
        logger: Optional logger for debug messages
        update_db: If True, force database update using timestamp checking

    Returns:
        List of matching file paths
    """
    db = get_file_database()

    # Update database with search paths if provided
    if search_paths:
        db.update_search_paths(search_paths, logger=logger, force_update=update_db)

    # Search using database
    return db.search_files(pattern, search_paths, logger=logger, update_db=update_db)
