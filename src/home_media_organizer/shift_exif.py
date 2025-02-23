import argparse
import logging

from .home_media_organizer import iter_files
from .media_file import MediaFile


#
# shift date of EXIF
#
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


def get_shift_exif_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "shift-exif",
        # parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Shift the date related metadata in EXIF.",
    )
    parser.add_argument(
        "--years",
        default=0,
        type=int,
        help="Number of years to shift. This is applied to year directly and will not affect month, day, etc of the dates.",
    )
    parser.add_argument(
        "--months",
        default=0,
        type=int,
        help="Number of months to shift. This is applied to month (and year) directly and will not affect year, day, etc.",
    )
    parser.add_argument("--weeks", default=0, type=int, help="Number of weeks to shift")
    parser.add_argument("-d", "--days", default=0, type=int, help="Number of days to shift")
    parser.add_argument("--hours", default=0, type=int, help="Number of hours to shift")
    parser.add_argument("--minutes", default=0, type=int, help="Number of minutes to shift")
    parser.add_argument("--seconds", default=0, type=int, help="Number of seconds to shift")
    parser.add_argument(
        "--keys",
        nargs="+",
        help="""A list of date keys that will be set. All keys ending with `Date`
         will be changed if left unspecified. """,
    )
    parser.set_defaults(func=shift_exif_date, command="shift-exif")
    return parser
