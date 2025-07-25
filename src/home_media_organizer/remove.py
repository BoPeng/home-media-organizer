import argparse
import logging

from .home_media_organizer import iter_files
from .media_file import MediaFile
from .utils import RemoveOperation


#
# organize files
#
def remove_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    for item in iter_files(args, logger=logger):
        m = MediaFile(item)
        m.remove(
            operation=args.operation,
            recycle_bin=args.recycle_bin,
            confirmed=args.confirmed,
            logger=logger,
        )
        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files removed.")


def get_remove_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "remove",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove files or keep them to a separate folder",
    )
    parser.add_argument(
        "--recycle-bin",
        help="""Directory to which files will be moved to instead of permanently removed.
            Default to $HOME/.home-media-organizer/recycled""",
    )
    parser.add_argument(
        "--operation",
        default="recycle",
        choices=[x.value for x in RemoveOperation],
        help="How to remove files. By default, files will be moved to a recycle bin.",
    )
    parser.set_defaults(func=remove_files, command="remove")
    return parser
