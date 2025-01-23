import argparse
import fnmatch
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool
from typing import List, Optional, Tuple

from rich.console import Console
from rich.logging import RichHandler
from tqdm import tqdm  # type: ignore

from . import __version__
from .config import Config
from .home_media_organizer import iter_files, process_with_queue
from .media_file import MediaFile
from .utils import (
    calculate_file_hash,
    clear_cache,
    extract_date_from_filename,
    get_response,
    jpeg_openable,
    mpg_playable,
)


# command line tools
#
def list_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    """List all or selected media files."""
    cnt = 0
    for item in iter_files(args):
        print(item)
        cnt += 1
    if logger is not None:
        logger.info(f"[magenta]{cnt}[/magenta] files found.")


def show_exif(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    for item in iter_files(args):
        m = MediaFile(item)
        m.show_exif(args.keys, output_format=args.format)
        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files shown.")


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
            lambda x, filename_format=args.format, suffix=args.suffix, logger=logger: rename_file(
                x, filename_format, suffix, True, logger
            ),
        )
    else:
        for item in iter_files(args):
            if logger is not None:
                logger.info(f"Processing [blue]{item}[/blue]")
            rename_file(item, args.format, args.suffix, args.confirmed, logger)


def check_media_file(
    item: str, remove: bool = False, confirmed: bool = False, logger: logging.Logger | None = None
) -> None:
    if (any(item.endswith(x) for x in (".jpg", ".jpeg")) and not jpeg_openable(item)) or (
        any(item.lower().endswith(x) for x in (".mp4", ".mpg")) and not mpg_playable(item)
    ):
        if logger is not None:
            logger.info(f"[red][bold]{item}[/bold] is corrupted.[/red]")
        if remove and (confirmed or get_response("Remove it?")):
            if logger is not None:
                logger.info(f"[red][bold]{item}[/bold] is removed.[/red]")
            os.remove(item)


def validate_media_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache()
    if args.confirmed or not args.remove:
        process_with_queue(
            args,
            lambda x, remove=args.remove, confirmed=args.confirmed, logger=logger: check_media_file(
                x, remove=remove, confirmed=confirmed, logger=logger
            ),
        )
    else:
        for item in iter_files(args):
            check_media_file(item, remove=args.remove, confirmed=args.confirmed, logger=logger)


def get_file_size(filename: str) -> Tuple[str, int]:
    return (filename, os.path.getsize(filename))


def get_file_md5(filename: str) -> Tuple[str, str]:
    return (filename, calculate_file_hash(os.path.abspath(filename)))


def remove_duplicated_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache()

    md5_files = defaultdict(list)
    size_files = defaultdict(list)

    with Pool() as pool:
        # get file size
        for filename, filesize in tqdm(
            pool.map(get_file_size, iter_files(args)), desc="Checking file size"
        ):
            size_files[filesize].append(filename)
        #
        # get md5 for files with the same size
        potential_duplicates = [file for x in size_files.values() if len(x) > 1 for file in x]
        for filename, md5 in tqdm(
            pool.map(get_file_md5, potential_duplicates),
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
        sorted_files = sorted(files, key=len)
        for filename in sorted_files[:-1]:
            if logger is not None:
                logger.info(f"[red]{filename}[/red] is a duplicated copy of {sorted_files[-1]} ")
            if args.confirmed or get_response("Remove it?"):
                os.remove(filename)
                removed_cnt += 1
    if logger is not None:
        logger.info(
            f"[blue]{removed_cnt}[/blue] out of [blue]{duplicated_cnt}[/blue] duplicated files are removed."
        )


def organize_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for option in ("media_root", "dir_pattern"):
        if not getattr(args, option):
            raise ValueError(
                f"Option --{option} is required. Please specify them either from command line or in your configuration file."
            )

    for item in iter_files(args):
        m = MediaFile(item)
        m.move(
            media_root=args.media_root,
            dir_pattern=args.dir_pattern,
            album=args.album,
            album_sep=args.album_sep,
            confirmed=args.confirmed,
            logger=logger,
        )


def shift_exif_date(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for item in iter_files(args):
        m = MediaFile(item)
        m.shift_exif(
            years=args.years,
            months=args.months,
            weeks=args.weeks,
            days=args.days,
            hours=args.hours,
            minutes=args.minutes,
            seconds=args.seconds,
            keys=args.keys,
            confirmed=args.confirmed,
            logger=logger,
        )


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


def cleanup(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for item in args.items:
        for root, _, files in os.walk(item):
            if args.file_types:
                for f in files:
                    if any(fnmatch.fnmatch(f, x) for x in args.file_types):
                        if args.confirmed or get_response(f"Remove {os.path.join(root, f)}?"):
                            if logger is not None:
                                logger.info(f"Remove {os.path.join(root, f)}")
                            os.remove(os.path.join(root, f))
            # empty directories are always removed when traverse the directory
            if not os.listdir(root):
                if args.confirmed or get_response(f"Remove empty directory {root}?"):
                    if logger is not None:
                        logger.info(f"Remove empty directory [blue]{root}[/blue]")
                    os.rmdir(root)


#
# User interface
#
def get_common_args_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "items",
        nargs="+",
        help="Directories or files to be processed",
    )
    parser.add_argument(
        "--with-exif",
        nargs="*",
        help="""Process only media files with specified exif data, which can be "key=value",
            or "key" while key in the second case can contain "*" for wildcard matching.""",
    )
    parser.add_argument(
        "--without-exif",
        nargs="*",
        help="""Process only media files without specified exif data. Both "key=value" and
            "key" and wildcard character "*" in key are supported.
        """,
    )
    parser.add_argument(
        "--file-types", nargs="*", help="File types to process, such as *.jpg, *.mp4, or 'video*'."
    )
    parser.add_argument("-j", "--jobs", help="Number of jobs for multiprocessing.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="confirmed",
        help="Proceed with all actions without prompt.",
    )
    return parser


def parse_args(arg_list: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""An Swiss Army Knife kind of tool to help fix, organize, and maitain your home media library""",
        epilog="""See documentation at https://github.com/BoPeng/home-media-organizer/""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config",
        help="""A configuration file in toml format. The configuration
        will be merged with configuration from ~/.home-media-organizer/config.toml""",
    )
    parser.add_argument(
        "--version", action="version", version="home-media-organizer, version " + __version__
    )
    # common options for all
    parent_parser = get_common_args_parser()
    subparsers = parser.add_subparsers(required=True, help="sub-command help")
    #
    # List relevant files
    #
    parser_list = subparsers.add_parser(
        "list",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parent_parser],
        help="List filename",
    )
    parser_list.set_defaults(func=list_files, command="list")
    #
    # show EXIF of files
    #
    parser_show = subparsers.add_parser(
        "show-exif",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parent_parser],
        help="Show all or selected exif information",
    )
    parser_show.add_argument("--keys", nargs="*", help="Show all or selected exif")
    parser_show.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Show output in json or text format",
    )
    parser_show.set_defaults(func=show_exif, command="show-exif")
    #
    # check jpeg
    #
    parser_validate = subparsers.add_parser(
        "validate",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Check if media file is corrupted",
    )
    parser_validate.add_argument(
        "--remove", action="store_true", help="If the file if it is corrupted."
    )
    parser_validate.add_argument(
        "--no-cache",
        action="store_true",
        help="invalidate cached validation results and re-validate all files again.",
    )
    parser_validate.set_defaults(func=validate_media_files, command="validate")
    #
    # rename file to its canonical name
    #
    parser_rename = subparsers.add_parser(
        "rename",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Rename files to their intended name, according to EXIF or other information.",
    )
    parser_rename.add_argument(
        "--format",
        help="Format of the filename. This option is usually set through configuration file.",
    )
    parser_rename.add_argument(
        "--suffix",
        help="A string that will be appended to filename (before file extension).",
    )
    parser_rename.set_defaults(func=rename_files, command="rename")
    #
    # dedup: remove duplicated files
    #
    parser_dedup = subparsers.add_parser(
        "dedup",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove duplicated files.",
    )
    parser_dedup.add_argument(
        "--no-cache",
        action="store_true",
        help="invalidate cached file signatures and re-examine all file content.",
    )
    parser_dedup.set_defaults(func=remove_duplicated_files, command="dedup")
    #
    # organize files
    #
    parser_organize = subparsers.add_parser(
        "organize",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Organize files into appropriate folder",
    )
    parser_organize.add_argument(
        "--media-root",
        help="Destination folder, which should be the root of all photos.",
    )
    parser_organize.add_argument(
        "--dir-pattern",
        help="Location for the album, which is by default derived from media year and month.",
    )
    parser_organize.add_argument(
        "--album",
        help="Album name for the photo, if need to further organize the media files by albums.",
    )
    parser_organize.add_argument(
        "--album-sep",
        default="-",
        help="""How to append album name to directory name. Default
            to "-" for directory structure like 2015-10-Vacation.""",
    )
    parser_organize.set_defaults(func=organize_files, command="organize")
    #
    # shift date of EXIF
    #
    parser_shift = subparsers.add_parser(
        "shift-exif",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Shift the date related metadata in EXIF.",
    )
    parser_shift.add_argument(
        "--years",
        default=0,
        type=int,
        help="Number of years to shift. This is applied to year directly and will not affect month, day, etc of the dates.",
    )
    parser_shift.add_argument(
        "--months",
        default=0,
        type=int,
        help="Number of months to shift. This is applied to month (and year) directly and will not affect year, day, etc.",
    )
    parser_shift.add_argument("--weeks", default=0, type=int, help="Number of weeks to shift")
    parser_shift.add_argument("-d", "--days", default=0, type=int, help="Number of days to shift")
    parser_shift.add_argument("--hours", default=0, type=int, help="Number of hours to shift")
    parser_shift.add_argument("--minutes", default=0, type=int, help="Number of minutes to shift")
    parser_shift.add_argument("--seconds", default=0, type=int, help="Number of seconds to shift")
    parser_shift.add_argument(
        "--keys",
        nargs="+",
        help="""A list of date keys that will be set. All keys ending with `Date`
         will be changed if left unspecified. """,
    )
    parser_shift.set_defaults(func=shift_exif_date, command="shift-exif")
    #
    # set dates of EXIF
    #
    parser_set_exif = subparsers.add_parser(
        "set-exif",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="""Set the exif. Unless --overwrite is specified,
            existing exif will not be overwritten.""",
    )
    parser_set_exif.add_argument(
        "--values",
        nargs="*",
        help="""key=value pairs that you can set to the media files.
          If a value '-' is specified, hmo will read from standard
          input, which can be the output of how show-exif of another
          file, essentially allowing you to copy exif information
          from another file. """,
    )
    parser_set_exif.add_argument(
        "--from-filename",
        help="""Try to extract date information from filename of
            media files. A pattern need to be specified to correctly extract
            date information from the filename. For example,
            --from-filename %%Y%%m%%d_%%H%%M%%S will assume that the files
            have the standard filename, Only the pattern for the date part
            of the filename is needed.""",
    )
    parser_set_exif.add_argument(
        "--from-date",
        help="""Accept a date string in the YYYYMMDD_HHMMSS and use it
        to set the date information of all files.""",
    )
    parser_set_exif.add_argument(
        "--keys",
        nargs="+",
        default=["EXIF:DateTimeOriginal"],
        help="""A list of date keys that will be set if options
        --from-date or --from-filename is specified.
        """,
    )
    parser_set_exif.add_argument(
        "--overwrite",
        action="store_true",
        help="""If specified, overwrite existing exif data.
        """,
    )
    parser_set_exif.set_defaults(func=set_exif_data, command="set-exif")
    #
    # cleanup
    #
    parser_cleanup = subparsers.add_parser(
        "cleanup",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove unwanted files and empty directories.",
    )
    parser_cleanup.add_argument(
        "file-types",
        nargs="*",
        help="Files or patterns to be removed.",
    )
    parser_cleanup.set_defaults(func=cleanup, command="cleanup")

    # load configuration
    args = parser.parse_args(arg_list)
    config = Config(args.config).config
    # assign config to args
    if args.command in config:
        for k, v in config[args.command].items():
            k = k.replace("-", "_")
            if getattr(args, k, None) is not None:
                continue
            setattr(args, k, v)
    return args


def app(arg_list: Optional[List[str]] = None) -> int:
    args = parse_args(arg_list)
    logging.basicConfig(
        level="DEBUG" if args.verbose else "INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                markup=True,
                console=Console(stderr=True),
                show_path=False if args.verbose is None else args.verbose,
            )
        ],
    )

    logger = logging.getLogger(args.command)
    # calling the associated functions
    try:
        args.func(args, logger)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(app())
