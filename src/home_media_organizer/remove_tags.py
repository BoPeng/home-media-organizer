import argparse
import logging
import sys

import rich

from .home_media_organizer import iter_files
from .utils import Manifest


#
# remove tags to media files
#
def remove_tags(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    if not args.manifest:
        rich.print("[red]No manifest file specified.[/red]")
        sys.exit(1)
    manifest = Manifest(args.manifest, logger=logger)
    # find only files with these tags
    if args.with_tags is None:
        args.with_tags = args.tags
    #
    for item in iter_files(args, manifest=manifest, logger=logger):
        manifest.remove_tags(item, args.tags)
        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files untagged.")


def get_remove_tags_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "remove-tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove tags associated with media files",
    )
    parser.add_argument("--tags", nargs="+", help="Tags to be removed from medis files")
    parser.set_defaults(func=remove_tags, command="remove_tags")
    return parser
