import argparse
import fnmatch
import os
import sys
import threading
from logging import Logger
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, Generator, List

import rich
from exiftool import ExifToolHelper  # type: ignore
from tqdm import tqdm  # type: ignore

from .media_file import date_func
from .utils import manifest


def iter_files(
    args: argparse.Namespace,
    items: List[str] | None = None,
    logger: Logger | None = None,
) -> Generator[Path, None, None]:
    def allowed_filetype(filename: Path) -> bool:
        if args.file_types and not any(fnmatch.fnmatch(filename, x) for x in args.file_types):
            if logger is not None:
                logger.debug(f"Ignoring {filename} due to failed --file-types matching.")
            return False
        if filename.suffix.lower() not in date_func:
            if logger is not None:
                logger.debug(f"Ignoring {filename} due to unsupported filetype")
            return False
        return True

    # if file is selected based on args.matches,, args.with_exif, args.without_exif
    def allowed_metadata(metadata: Dict) -> bool:
        for cond in args.without_exif or []:
            if "=" in cond:
                k, v = cond.split("=")
                if "*" in k:
                    raise ValueError(
                        f"Invalid condition {cond}: '*' is not allowed when key=value is specified."
                    )
                if k in metadata and metadata[k] == v:
                    return False
            elif "*" in cond:
                if any(fnmatch.fnmatch(x, cond) for x in metadata.keys()):
                    return False
            else:
                if cond in metadata:
                    return False
        match = True
        for cond in args.with_exif or []:
            if "=" in cond:
                k, v = cond.split("=")
                if "*" in k:
                    raise ValueError(
                        f"Invalid condition {cond}: '*' is not allowed when key=value is specified."
                    )
                if k not in metadata or metadata[k] != v:
                    match = False
            elif "*" in cond:
                if not any(fnmatch.fnmatch(x, cond) for x in metadata.keys()):
                    match = False
            else:
                if cond not in metadata:
                    match = False
        return match

    if args.with_tags is not None:
        files_with_tags = {x.filename for x in manifest.find_by_tags(args.with_tags)}
    if args.without_tags is not None:
        files_with_unwanted_tags = {x.filename for x in manifest.find_by_tags(args.without_tags)}

    for item in items or args.items:
        # if item is an absolute path, use it directory
        # if item is an relative path, check current working directory first
        # if not found, check the search path
        item = Path(item)
        if item.is_absolute():
            pass
        elif item.exists():
            item = item.resolve()
        elif args.search_paths:
            search_paths = (
                [args.search_paths] if isinstance(args.search_paths, str) else args.search_paths
            )
            for path in search_paths:
                if (Path(path) / item).exists():
                    item = (Path(path) / item).resolve()
                    break
            else:
                if len(search_paths) == 1:
                    rich.print(
                        f"[red]{item} not found in current directory or {search_paths[0]}[/red]"
                    )
                else:
                    rich.print(
                        f"[red]{item} not found in current directory or any directory under {', '.join(search_paths)}[/red]"
                    )
                sys.exit(1)
        else:
            rich.print(f"[red]{item} not found in current directory[/red]")
            sys.exit(1)
        if item.is_file():
            if not allowed_filetype(item):
                continue
            if args.with_tags is not None and str(item) not in files_with_tags:
                if logger is not None:
                    logger.debug(f"Ignoring {item} due to failed --with-tags matching.")
                continue
            if args.without_tags is not None and str(item) in files_with_unwanted_tags:
                if logger is not None:
                    logger.debug(f"Ignoring {item} due to failed --without-tags matching.")
                continue
            if args.with_exif or args.without_exif:
                with ExifToolHelper() as e:
                    metadata = {
                        x: y
                        for x, y in e.get_metadata(item.resolve())[0].items()
                        if not x.startswith("File:")
                    }
                if not allowed_metadata(metadata):
                    if logger is not None:
                        logger.debug(
                            f"Ignoring {item} due to failed --with-exif or --without-exif matching."
                        )
                    continue
            yield item
        else:
            if not item.is_dir():
                rich.print(f"[red]{item} is not a filename or directory[/red]")
                continue
            for root, _, files in os.walk(item):
                # if with_tags if specified, check if any of the files_with_tags is under root
                if args.with_tags is not None and not any(
                    f.startswith(root) for f in files_with_tags
                ):
                    if logger is not None:
                        logger.debug(
                            f"Ignoring {root} because no files under this directory has matching tag."
                        )
                    continue
                rootpath = Path(root)
                if args.with_exif or args.without_exif:
                    # get exif atll at the same time
                    qualified_files = [
                        rootpath / f
                        for f in files
                        if allowed_filetype(Path(f))
                        and (args.with_tags is None or str(rootpath / f) in files_with_tags)
                        and (
                            args.without_tags is None
                            or str(rootpath / f) not in files_with_unwanted_tags
                        )
                    ]
                    if not qualified_files:
                        continue
                    with ExifToolHelper() as e:
                        all_metadata = e.get_metadata(files=qualified_files)
                        for qualified_file, metadata in zip(qualified_files, all_metadata):
                            if allowed_metadata(
                                {x: y for x, y in metadata.items() if not x.startswith("File:")}
                            ):
                                yield qualified_file
                else:
                    for f in files:
                        if (
                            args.with_tags is not None and str(rootpath / f) not in files_with_tags
                        ) or (
                            args.without_tags is not None
                            and str(rootpath / f) in files_with_unwanted_tags
                        ):
                            if logger is not None:
                                logger.debug(
                                    f"Ignoring {rootpath/f} due to failed --with-tags or --without-tags matching."
                                )
                            continue
                        if allowed_filetype(Path(f)):
                            yield rootpath / f


class Worker(threading.Thread):
    def __init__(self: "Worker", queue: Queue[Any], task: Callable) -> None:
        threading.Thread.__init__(self)
        self.queue = queue
        self.task = task
        self.daemon = True

    def run(self: "Worker") -> None:
        while True:
            item = self.queue.get()
            if item is None:
                break
            self.task(item)
            self.queue.task_done()


def process_with_queue(args: argparse.Namespace, func: Callable) -> None:
    q: Queue[str] = Queue()
    # Create worker threads
    num_workers = args.jobs or 10
    for _ in range(num_workers):
        t = Worker(q, func)
        t.start()

    for item in (pbar := tqdm(iter_files(args))):
        pbar.set_description(f"Processing {item.name}")
        q.put(item)
    q.join()
