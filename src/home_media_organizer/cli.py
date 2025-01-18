"""Console script for home-media-organizer."""

from . import __version__
from .home_media_organizer import *

import argparse
import sys


def list_files(items, **kwargs):
    """List all or selected media files."""

    for item in iter_files(items, **kwargs):
        print(item)


def get_common_args_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "items",
        nargs="+",
        help="Directories or files to be processed",
    )
    parser.add_argument(
        "--with-exif", nargs="*", help="Process only media files with specified exif data."
    )
    parser.add_argument(
        "--without-exif", nargs="*", help="Process only media files without specified exif data."
    )
    parser.add_argument(
        "--file-types", nargs="*", help="File types to process, such as .jpg, .mp4."
    )
    parser.add_argument("-j", "--jobs", help="Number of jobs for multiprocessing.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        dest="__confirm__",
        help="Proceed with all actions without prompt.",
    )
    return parser


def app():
    parser = argparse.ArgumentParser(
        description="""An Swiss Army Knife kind of tool to help fix, organize, and maitain your home media library""",
        epilog="""See documentation at https://github.com/BoPeng/home-media-organizer/""",
        # parents=[],
    )
    parser.add_argument(
        "-v", "--version", action="version", version="Home Media Organizer " + __version__
    )
    #
    parent_parser = get_common_args_parser()
    subparsers = parser.add_subparsers(required=True, help="sub-command help")
    #
    # List relevant files
    #
    parser_list = subparsers.add_parser("list", parents=[parent_parser], help="List filename")
    parser_list.set_defaults(func=list_files)
    #
    # show exif of files
    #
    parser_show = subparsers.add_parser(
        "show", parents=[parent_parser], help="Show all or selected exif"
    )
    parser_show.add_argument("--keys", nargs="*", help="Show all or selected exif")
    parser_show.set_defaults(func=show_exif)
    #
    # check jpeg
    #
    parser_check = subparsers.add_parser(
        "check-jpeg", parents=[parent_parser], help="Check if JPEG file is corrupted"
    )
    parser_check.add_argument(
        "--remove", action="store_true", help="If the file if it is corrupted."
    )
    parser_check.set_defaults(func=check_jpeg_files)
    #
    # rename file to its canonical name
    #
    parser_rename = subparsers.add_parser(
        "rename",
        parents=[parent_parser],
        help="Rename files to their intended name, according to exif or other information.",
    )
    parser_rename.set_defaults(func=rename_files)
    #
    # dedup: remove duplicated files
    #
    parser_dedup = subparsers.add_parser(
        "dedup",
        parents=[parent_parser],
        help="Remove duplicated files.",
    )
    parser_dedup.set_defaults(func=remove_duplicated_files)
    #
    # organize files
    #
    parser_organize = subparsers.add_parser(
        "organize",
        parents=[parent_parser],
        help="Organize files into appropriate folder",
    )
    parser_organize.add_argument(
        "--media-root",
        default="/Volumes/Public/MyPictures",
        help="Destination folder, which should be the root of all photos.",
    )
    parser_organize.add_argument(
        "--subdir",
        default="{year}/{month}",
        help="Destination subfolder.",
    )
    parser_organize.set_defaults(func=organize_files)
    #
    # shift date of exif
    #
    parser_shift = subparsers.add_parser(
        "shift", parents=[parent_parser], help="YY:MM:DD:HH:MM to shift the exif dates."
    )
    parser_shift.add_argument("--by", help="YY:MM:DD:HH:MM to shift the exif dates.")
    parser_shift.set_defaults(func=shift_exif_date)
    #
    # set dates of exif
    #
    parser_set_exif = subparsers.add_parser(
        "set-exif",
        parents=[parent_parser],
        help="Set the exif dates if unavailable.",
    )
    parser_set_exif.add_argument(
        "date", nargs="+", help="YY:MM:DD:HH:MM to set the exif dates if unavailable."
    )
    parser_set_exif.set_defaults(func=set_exif_date)
    #
    # cleanup
    #
    parser_cleanup = subparsers.add_parser(
        "cleanup",
        parents=[parent_parser],
        help="Remove unwanted files and empty directories.",
    )
    parser_cleanup.add_argument(
        "removable_files",
        nargs="*",
        default=[
            "*.MOI",
            "*.PGI",
            "*.THM",
            "Default.PLS",
            ".picasa*.ini",
            "Thumbs.db",
            "*.ini",
            "*.bat",
            "autprint*",
        ],
        help="Files or patterns to be removed.",
    )
    parser_cleanup.set_defaults(func=cleanup)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # calling the associated functions
    args = parser.parse_args()
    confirmed = args.__confirm__
    args.func(args)


if __name__ == "__main__":
    sys.exit(app())
