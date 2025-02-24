import argparse
import logging
import os
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Tuple

from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .utils import clear_cache, get_file_hash, get_response


#
# dedup: remove duplicated files
#
def get_file_size(filename: Path) -> Tuple[Path, int]:
    return (filename, filename.stat().st_size)


def get_file_md5(filename: Path) -> Tuple[Path, str]:
    return (filename, get_file_hash(filename.resolve()))


def remove_duplicated_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="dedup")

    md5_files = defaultdict(list)
    size_files = defaultdict(list)

    with Pool(args.jobs or None) as pool:
        # get file size
        for filename, filesize in tqdm(
            pool.imap(get_file_size, iter_files(args)), desc="Checking file size"
        ):
            size_files[filesize].append(filename)
        #
        # get md5 for files with the same size
        potential_duplicates = [file for x in size_files.values() if len(x) > 1 for file in x]
        for filename, md5 in tqdm(
            pool.imap(get_file_md5, potential_duplicates),
            desc="Checking file content",
        ):
            md5_files[md5].append(filename)

    #
    duplicated_cnt = 0
    removed_cnt = 0
    for files in md5_files.values():
        if len(files) == 1:
            continue
        # keep the one with the deepest path name
        duplicated_cnt += len(files) - 1
        sorted_files = sorted(files, key=lambda x: len(str(x)))
        for filename in sorted_files[:-1]:
            if logger is not None:
                logger.info(f"[red]{filename}[/red] is a duplicated copy of {sorted_files[-1]} ")
            if args.confirmed is False:
                if logger is not None:
                    logger.info(f"[green]DRYRUN[/green] Would remove {filename}")
            elif args.confirmed or get_response("Remove it?"):
                os.remove(filename)
                if logger is not None:
                    logger.info(f"[red]{filename}[/red] is removed.")
                removed_cnt += 1
    if logger is not None:
        logger.info(
            f"[blue]{removed_cnt}[/blue] out of [blue]{duplicated_cnt}[/blue] duplicated files are removed."
        )


def get_dedup_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "dedup",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove duplicated files",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="invalidate cached file signatures and re-examine all file content.",
    )
    parser.set_defaults(func=remove_duplicated_files, command="dedup")
    return parser
