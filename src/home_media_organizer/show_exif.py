import argparse
import logging

from .home_media_organizer import iter_files
from .media_file import MediaFile


#
# show EXIF of files
#
def show_exif(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    for item in iter_files(args):
        m = MediaFile(item)
        m.show_exif(args.keys, output_format=args.format)
        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files shown.")


def get_show_exif_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "show-exif",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        #    # parents=[parent_parser],
        help="Show all or selected exif information",
    )
    parser.add_argument("--keys", nargs="*", help="Show all or selected exif")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Show output in json or text format",
    )
    parser.set_defaults(func=show_exif, command="show-exif")
    return parser
