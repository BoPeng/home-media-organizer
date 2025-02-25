import argparse
import logging
import os
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
from typing import Tuple

from rich.prompt import Prompt
from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .utils import clear_cache, get_file_hash


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

        if args.confirmed is not None:
            for filename in sorted_files[:-1]:
                if logger is not None:
                    logger.info(
                        f"[red]{filename}[/red] is a duplicated copy of {sorted_files[-1]} "
                    )
                if args.confirmed is False:
                    if logger is not None:
                        logger.info(f"[green]DRYRUN[/green] Would remove {filename}")
                else:
                    os.remove(filename)
                    if logger is not None:
                        logger.info(f"[red]{filename}[/red] is removed.")
                    removed_cnt += 1
        else:
            # ask which file that user would like to keep
            msg = f"\nThe following [red]{len(files)}[/red] files have the same content:\n"
            choices = []
            for idx, filename in enumerate(sorted_files):
                if idx == len(sorted_files) - 1:
                    msg += f"{idx + 1}:  [green]{filename}[/green]\n"
                else:
                    msg += f"{idx + 1}:  [red]{filename}[/red]\n"
                choices.append(str(idx + 1))
            choices.append("n")
            msg += """Which file would you like to keep ("n" to keep all)?"""
            answer = Prompt.ask(msg, choices=choices, default=choices[-2])
            if answer == "n":
                continue
            keep_idx = int(answer) - 1
            for idx, filename in enumerate(sorted_files):
                if idx == keep_idx:
                    continue
                os.remove(filename)
                if logger is not None:
                    logger.info(f"[red]{filename}[/red] is removed.")
                removed_cnt += 1


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
