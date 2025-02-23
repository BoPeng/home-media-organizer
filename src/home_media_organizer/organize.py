import argparse
import logging

from .home_media_organizer import iter_files
from .media_file import MediaFile
from .utils import OrganizeOperation


#
# organize files
#
def organize_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    for option in ("media_root", "dir_pattern"):
        if not getattr(args, option):
            raise ValueError(
                f"Option --{option} is required. Please specify them either from command line or in your configuration file."
            )

    for item in iter_files(args):
        m = MediaFile(item)
        m.organize(
            media_root=args.media_root,
            dir_pattern=args.dir_pattern,
            album=args.album,
            album_sep=args.album_sep,
            operation=OrganizeOperation(args.operation),
            confirmed=args.confirmed,
            logger=logger,
        )


def get_organize_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "organize",
        # parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Organize files into appropriate folder",
    )
    parser.add_argument(
        "--media-root",
        help="Destination folder, which should be the root of all photos.",
    )
    parser.add_argument(
        "--dir-pattern",
        help="Location for the album, which is by default derived from media year and month.",
    )
    parser.add_argument(
        "--album",
        help="Album name for the photo, if need to further organize the media files by albums.",
    )
    parser.add_argument(
        "--album-sep",
        default="-",
        help="""How to append album name to directory name. Default
            to "-" for directory structure like 2015-10-Vacation.""",
    )
    parser.add_argument(
        "--operation",
        default="move",
        choices=[x.value for x in OrganizeOperation],
        help="How to organize the files. By default, files will be moved.",
    )
    parser.set_defaults(func=organize_files, command="organize")
    return parser
