import argparse
import fnmatch
import logging

import rich

from .home_media_organizer import iter_files
from .media_file import MediaFile


#
# show EXIF of files
#
def show_exif(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    for item in iter_files(args):
        metadata = MediaFile(item).exif

        if args.keys is not None:
            if all("*" not in key for key in args.keys):
                metadata = {k: metadata.get(k, "NA") for k in args.keys}
            else:
                metadata = {
                    k: v
                    for k, v in metadata.items()
                    if any(fnmatch.fnmatch(k, key) for key in args.keys)
                }

        if not args.format or args.format == "json":
            rich.print_json(data=metadata)
        else:
            for key, value in metadata.items():
                rich.print(f"[bold blue]{key}[/bold blue]=[green]{value}[/green]")
            rich.print()

        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files shown.")


def get_show_exif_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "show-exif",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        #
        help="Show EXIF metadata of media files",
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
