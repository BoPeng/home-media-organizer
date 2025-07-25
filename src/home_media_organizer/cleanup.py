import argparse
import logging

from .home_media_organizer import iter_files
from .utils import get_response


# cleanup
#
def cleanup(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    failed_cnt = 0
    for item in iter_files(args, logger=logger):
        if args.confirmed is False:
            if logger is not None:
                logger.info(f"[green]DRYRUN[/green] Would remove {item}")
        elif args.confirmed or get_response(f"Remove {item}?"):
            if logger is not None:
                logger.info(f"Remove {item}")
            try:
                item.unlink()
                cnt += 1
            except Exception as ex:
                failed_cnt += 1
                if logger is not None:
                    logger.error(f"Failed to remove {item}: {ex}")
    if logger is not None:
        logger.info(f"[magenta]{cnt}[/magenta] files removed.")
        if failed_cnt > 0:
            logger.error(f"[red]{failed_cnt}[/red] files failed to remove.")


def get_cleanup_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "cleanup",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove unwanted files and empty directories",
    )

    parser.set_defaults(func=cleanup, command="cleanup")
    return parser
