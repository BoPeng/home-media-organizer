import argparse
import logging
import os
import sys
from datetime import datetime

from .home_media_organizer import iter_files
from .media_file import MediaFile
from .utils import extract_date_from_filename


#
# set dates of EXIF
#
def set_exif_data(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for item in iter_files(args):
        m = MediaFile(item)
        values = {}
        if args.values:
            if "-" in args.values:
                args.values.remove("-")
                args.values += sys.stdin.read().strip().split("\n")
            for item in args.values:
                if "=" not in item:
                    if logger is not None:
                        logger.error(f"[red]Invalid exif value {item}. Should be key=value[/red]")
                    sys.exit(1)
                k, v = item.split("=", 1)
                values[k] = v
        # from filename?
        if args.from_filename:
            try:
                date = extract_date_from_filename(os.path.basename(m.filename), args.from_filename)
                for k in args.keys:
                    values[k] = date.strftime("%Y:%m:%d %H:%M:%S")
            except ValueError:
                if logger is not None:
                    logger.info(
                        f"[red]Ignore {m.filename} with invalid date format {args.from_filename}[/red]"
                    )
                continue
        elif args.from_date:
            try:
                date = datetime.strptime(args.from_date, "%Y%m%d_%H%M%S")
            except ValueError:
                if logger is not None:
                    logger.info(f"[red]Invalid date format {args.from_date}[/red]")
                sys.exit(1)
            for k in args.keys:
                values[k] = date.strftime("%Y:%m:%d %H:%M:%S")
        #
        if values:
            m.set_exif(values, args.overwrite, args.confirmed, logger=logger)


def get_set_exif_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "set-exif",
        # parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="""Set the exif. Unless --overwrite is specified,
            existing exif will not be overwritten.""",
    )
    parser.add_argument(
        "--values",
        nargs="*",
        help="""key=value pairs that you can set to the media files.
          If a value '-' is specified, hmo will read from standard
          input, which can be the output of how show-exif of another
          file, essentially allowing you to copy exif information
          from another file. """,
    )
    parser.add_argument(
        "--from-filename",
        help="""Try to extract date information from filename of
            media files. A pattern need to be specified to correctly extract
            date information from the filename. For example,
            --from-filename %%Y%%m%%d_%%H%%M%%S will assume that the files
            have the standard filename, Only the pattern for the date part
            of the filename is needed.""",
    )
    parser.add_argument(
        "--from-date",
        help="""Accept a date string in the YYYYMMDD_HHMMSS and use it
        to set the date information of all files.""",
    )
    parser.add_argument(
        "--keys",
        nargs="+",
        default=["EXIF:DateTimeOriginal"],
        help="""A list of date keys that will be set if options
        --from-date or --from-filename is specified.
        """,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="""If specified, overwrite existing exif data.
        """,
    )
    parser.set_defaults(func=set_exif_data, command="set-exif")
    return parser
