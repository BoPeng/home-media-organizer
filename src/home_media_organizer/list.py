import argparse
import logging

from .home_media_organizer import iter_files


#
# List files
#
def list_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    """List all or selected media files."""
    cnt = 0
    for item in iter_files(args):
        print(item)
        cnt += 1
    if logger is not None:
        logger.info(f"[magenta]{cnt}[/magenta] files found.")


def get_list_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "list",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # # parents=[parent_parser],
        help="List filename",
    )

    parser.set_defaults(func=list_files, command="list")
    return parser
