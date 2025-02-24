import argparse
import logging
import sys
from typing import List, Optional

from rich.console import Console
from rich.logging import RichHandler

from . import __version__
from .classify import get_classify_parser
from .cleanup import get_cleanup_parser
from .compare import get_compare_parser
from .config import Config
from .dedup import get_dedup_parser
from .list import get_list_parser
from .organize import get_organize_parser
from .remove_tags import get_remove_tags_parser
from .rename import get_rename_parser
from .set_exif import get_set_exif_parser
from .set_tags import get_set_tags_parser
from .shift_exif import get_shift_exif_parser
from .show_exif import get_show_exif_parser
from .show_tags import get_show_tags_parser
from .utils import manifest
from .validate import get_validate_parser


#
# User interface
#
def add_common_arguments(subparser: argparse.ArgumentParser) -> None:
    parser = subparser.add_argument_group("common options")
    parser.add_argument(
        "items",
        nargs="+",
        help="Directories or files to be processed",
    )
    parser.add_argument(
        "--file-types", nargs="*", help="File types to process, such as *.jpg, *.mp4, or 'video*'."
    )
    parser.add_argument(
        "--with-tags",
        nargs="*",
        help="""Process only media files with specified tag, one of the tags if multiple value are provided,
            or any tag if no value is specified. Logical expressions such as 'baby AND happy' are
            supported.""",
    )
    parser.add_argument(
        "--without-tags",
        nargs="*",
        help="""Process only media files that do not contain specified tag, or any of the tags if multiple
            values are provided, or without any tag if no value is specified. Logical expressions such as
            'baby AND happy' is allowed.""",
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
        "-c",
        "--config",
        help="""A configuration file in toml format. The configuration
        will be merged with configuration from ~/.home-media-organizer/config.toml""",
    )
    parser.add_argument(
        "--search-paths",
        nargs="+",
        help="""Search paths for items to be processed if relative file or directory names are specified. The current directory will always be searched first.""",
    )
    parser.add_argument(
        "--manifest",
        help="""Path to a manifest file that stores metadata such as file signature and tags.
            Default to ~/.home-media-organizer/manifest.db.""",
    )
    parser.add_argument("-j", "--jobs", type=int, help="Number of jobs for multiprocessing.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="confirmed",
        help="Proceed with all actions without prompt.",
    )


def parse_args(arg_list: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""An versatile tool to maintain your home media library""",
        epilog="""See documentation at https://github.com/BoPeng/home-media-organizer/""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="home-media-organizer, version " + __version__
    )
    subparsers = parser.add_subparsers(required=True, help="sub-command help")

    for subparser in [
        get_classify_parser(subparsers),
        get_cleanup_parser(subparsers),
        get_compare_parser(subparsers),
        get_dedup_parser(subparsers),
        get_list_parser(subparsers),
        get_organize_parser(subparsers),
        get_remove_tags_parser(subparsers),
        get_rename_parser(subparsers),
        get_set_exif_parser(subparsers),
        get_set_tags_parser(subparsers),
        get_shift_exif_parser(subparsers),
        get_show_exif_parser(subparsers),
        get_show_tags_parser(subparsers),
        get_validate_parser(subparsers),
    ]:
        # we do not use parent parser mechanism because we would like to
        # create a separate argument group for each subcommand
        add_common_arguments(subparser)

    # load configuration
    args = parser.parse_args(arg_list)
    config = Config(args.config).config
    # assign config to args
    if "default" in config:
        for k, v in config["default"].items():
            k = k.replace("-", "_")
            if getattr(args, k, None) is not None:
                continue
            setattr(args, k, v)
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
    manifest.init_db(args.manifest, logger=logger)

    # calling the associated functions
    try:
        args.func(args, logger)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(app())
