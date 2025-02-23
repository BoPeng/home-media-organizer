import argparse
import fnmatch
import logging
import os
from pathlib import Path

from .utils import get_response


# cleanup
#
def cleanup(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for item in args.items:
        for root, _, files in os.walk(item):
            rootpath = Path(root)
            if args.file_types:
                for f in files:
                    if any(fnmatch.fnmatch(f, x) for x in args.file_types):
                        if args.confirmed or get_response(f"Remove {rootpath / f}?"):
                            if logger is not None:
                                logger.info(f"Remove {rootpath / f}")
                            (rootpath / f).unlink()
            # empty directories are always removed when traverse the directory
            if not os.listdir(root):
                if args.confirmed or get_response(f"Remove empty directory {root}?"):
                    if logger is not None:
                        logger.info(f"Remove empty directory [blue]{root}[/blue]")
                    rootpath.rmdir()


def get_cleanup_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "cleanup",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove unwanted files and empty directories.",
    )
    parser.add_argument(
        "file-types",
        nargs="*",
        help="Files or patterns to be removed.",
    )
    parser.set_defaults(func=cleanup, command="cleanup")
    return parser
