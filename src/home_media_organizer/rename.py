import argparse
import logging

from .home_media_organizer import iter_files, process_with_queue
from .media_file import MediaFile


#
# rename file to its canonical name
#
def rename_file(
    item: str, filename_format: str, suffix: str, confirmed: bool, logger: logging.Logger | None
) -> None:
    m = MediaFile(item)
    # logger.info(f"Processing [blue]{item}[/blue]")
    m.rename(filename_format=filename_format, suffix=suffix, confirmed=confirmed, logger=logger)


def rename_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if not args.format:
        raise ValueError("Option --format is required.")
    if args.confirmed:
        process_with_queue(
            args,
            lambda x, filename_format=args.format, suffix=args.suffix or "", logger=logger: rename_file(
                x, filename_format, suffix, True, logger
            ),
        )
    else:
        for item in iter_files(args):
            if logger is not None:
                logger.info(f"Processing [blue]{item}[/blue]")
            rename_file(item, args.format, args.suffix or "", args.confirmed, logger)


def get_rename_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "rename",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Rename files to their canonical names",
    )
    parser.add_argument(
        "--format",
        help="Format of the filename. This option is usually set through configuration file.",
    )
    parser.add_argument(
        "--suffix",
        help="A string that will be appended to filename (before file extension).",
    )
    parser.set_defaults(func=rename_files, command="rename")
    return parser
