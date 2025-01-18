"""Console script for home-media-organizer."""

from . import __version__
from .home_media_organizer import *
from .media_file import MediaFile
import argparse
import sys


#
# command line tools
#
def list_files(args):
    """List all or selected media files."""

    for item in iter_files(args):
        print(item)


def show_exif(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.show_exif(args.keys, args.format)


def rename_file(item):
    m = MediaFile(item)
    m.rename()


def rename_files(args):
    if args.yees:
        process_with_queue(args, rename_file)
    else:
        for item in iter_files(args):
            print(f"Processing {item}")
            rename_file(item)


def check_jpeg(item, remove=False):
    if not any(item.endswith(x) for x in (".jpg", ".jpeg")):
        return
    try:
        i = Image.open(item)
        i.close()
    except UnidentifiedImageError:
        if remove:
            print(f"Remove {item}")
            os.remove(item)
        else:
            print(f"Corrupted {item}")
        return


def check_jpeg_files(args):
    process_with_queue(args, lambda x, remove=args.remove: check_jpeg(x, remove=remove))


def get_file_size(filename):
    return (filename, os.path.getsize(filename))


def get_file_md5(filename, md5_cache):
    return (filename, MediaFile(filename).calculate_md5(md5_cache).md5)


def remove_duplicated_files(args):
    md5_files = defaultdict(list)
    size_files = defaultdict(list)

    if os.path.isfile("md5.json"):
        md5_cache = json.load(open("md5.json"))
    else:
        md5_cache = {}

    with Pool() as pool:
        # get file size
        for filename, filesize in pool.map(get_file_size, iter_files(args)):
            size_files[filesize].append(filename)
        #
        # get md5 for files with the same size
        potential_duplicates = sum([x for x in size_files.values() if len(x) > 1], [])
        for filename, md5 in pool.starmap(
            get_file_md5,
            zip(potential_duplicates, [md5_cache] * len(potential_duplicates)),
        ):
            md5_files[md5].append(filename)

    with open("md5.json", "w") as store:
        json.dump(md5_cache, store, indent=4)

    #
    for md5, files in md5_files.items():
        if len(files) == 1:
            continue
        # print(f"Found {len(files)} files with md5 {md5}")
        # keep the one with the deepest path name
        sorted_files = sorted(files, key=len)
        for filename in sorted_files[:-1]:
            print(f"Remove {filename} that duplicates {sorted_files[-1]} ")
            os.remove(filename)


def organize_files(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.move(args.media_root, subdir=args.subdir if args.subdir else m.get_subdir())


def shift_exif_date(args):
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
            confirmed=args.confirmed,
        )


def set_exif_date(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.set_dates(args.set_date)


#
# User interface
#
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
        dest="confirmed",
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
    # common options for all
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
        "show-exif", parents=[parent_parser], help="Show all or selected exif information"
    )
    parser_show.add_argument("--keys", nargs="*", help="Show all or selected exif")
    parser_show.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Show output in json or text format",
    )
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
        "shift-exif", parents=[parent_parser], help="YY:MM:DD:HH:MM to shift the exif dates."
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
    args.func(args)


if __name__ == "__main__":
    sys.exit(app())
