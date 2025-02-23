import argparse
import logging
import os
from multiprocessing import Pool
from typing import Tuple

from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .utils import (
    Manifest,
    calculate_file_hash,
    clear_cache,
    get_response,
    jpeg_openable,
    mpg_playable,
)


#
# check jpeg
#
def check_media_file(item: str) -> Tuple[str, str, bool]:
    return (
        item,
        calculate_file_hash(item),
        (any(item.endswith(x) for x in (".jpg", ".jpeg")) and not jpeg_openable(item))
        or (any(item.lower().endswith(x) for x in (".mp4", ".mpg")) and not mpg_playable(item)),
    )


def validate_media_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="validate")

    # if there is a manifest file, get the existing file hash
    if args.manifest:
        manifest = Manifest(args.manifest, logger=logger)

    if args.confirmed or not args.remove:
        with Pool() as pool:
            # get file size
            for item, new_hash, corrupted in tqdm(
                pool.imap(check_media_file, iter_files(args)),
                desc="Validate media",
            ):
                existing_hash = manifest.get_hash(item, None)
                if existing_hash is not None and existing_hash != new_hash:
                    if logger is not None:
                        logger.warning(f"[red][bold]{item}[/bold] is corrupted.[/red]")
                    continue
                if corrupted:
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is not playable.[/red]")
                    continue
                if args.manifest:
                    manifest.set_hash(item, new_hash)
    else:
        for item in iter_files(args):
            _, new_hash, corrupted = check_media_file(item)
            existing_hash = manifest.get_hash(item, None)
            if existing_hash is not None and existing_hash != new_hash:
                if logger is not None:
                    logger.warning(f"[red][bold]{item}[/bold] is corrupted.[/red]")
                if args.remove and (args.confirmed or get_response("Remove it?")):
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is removed.[/red]")
                    os.remove(item)
                continue
            if corrupted:
                if logger is not None:
                    logger.warning(f"[red][bold]{item}[/bold] is not playable.[/red]")
                if args.remove and (args.confirmed or get_response("Remove it?")):
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is removed.[/red]")
                    os.remove(item)
                continue
            if args.manifest:
                manifest.set_hash(item, new_hash)


def get_validate_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "validate",
        # parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Check if media file is corrupted",
    )
    parser.add_argument("--remove", action="store_true", help="If the file if it is corrupted.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="invalidate cached validation results and re-validate all files again.",
    )
    parser.set_defaults(func=validate_media_files, command="validate")
    return parser
