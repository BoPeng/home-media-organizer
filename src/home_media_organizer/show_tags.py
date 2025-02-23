import argparse
import logging
import sys

import rich

from .home_media_organizer import iter_files
from .utils import Manifest


#
# show tags of files
#
def show_tags(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    if not args.manifest:
        rich.print("[red]No manifest file specified.[/red]")
        sys.exit(1)
    manifest = Manifest(args.manifest, logger=logger)
    if args.all is True:
        all_tags = manifest.get_all_tags()
        combined_tags = {x: y for d in all_tags for x, y in d.items()}
        if args.format == "json":
            rich.print(sorted(combined_tags.keys()))
        elif args.format == "json-details":
            rich.print(combined_tags)
        elif args.format == "text":
            rich.print(", ".join(sorted(combined_tags.keys())))
        elif args.format == "text-details":
            for key, value in combined_tags.items():
                rich.print(f"[bold blue]{key}[/bold blue])=[green]{value}[/green]")
            rich.print()
        else:
            rich.print(f"[red]Unknown format: {args.format}[/red]")
        return
    if args.with_tags is None:
        args.with_tags = []
    for item in iter_files(args, manifest=manifest):
        tags = manifest.get_tags(item)
        if args.tags:
            tags = {k: v for k, v in tags.items() if k in args.tags}
        if not tags:
            if logger is not None:
                logger.debug(f"{item} has no tags.")
            continue
        if not args.format or args.format == "json":
            rich.print({item: list(tags.keys())})
        elif args.format == "json-details":
            rich.print({"filename": item, "tags": tags})
        elif args.format == "text":
            rich.print(f"""[cyan]{item}[/cyan]: {", ".join(tags.keys())}""")
        elif args.format == "text-details":
            rich.print(f"[yellow]{item}[/yellow]")
            for key, value in tags.items():
                rich.print(f"[bold blue]{key}[/bold blue]=[green]{value}[/green]")
            rich.print()
        else:
            rich.print(f"[red]Unknown format: {args.format}[/red]")

        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files shown.")


def get_show_tags_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "show-tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # parents=[parent_parser],
        help="Show all or selected tags",
    )
    parser.add_argument("--all", action="store_true", help="Show all tags in the library.")
    parser.add_argument("--tags", nargs="*", help="Show all or selected tags")
    parser.add_argument(
        "--format",
        choices=("json", "text", "json-details", "text-details"),
        default="text",
        help="Show output in json or text format",
    )
    parser.set_defaults(func=show_tags, command="show-tags")
    return parser
