import argparse
import fnmatch
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from multiprocessing import Pool
from typing import Any, Dict, List, Optional, Tuple

import rich
from nudenet import NudeDetector  # type: ignore
from rich.console import Console
from rich.logging import RichHandler
from tqdm import tqdm  # type: ignore

from . import __version__
from .config import Config
from .home_media_organizer import iter_files, process_with_queue
from .media_file import MediaFile
from .utils import (
    CompareBy,
    CompareOutput,
    Manifest,
    OrganizeOperation,
    calculate_file_hash,
    clear_cache,
    extract_date_from_filename,
    get_file_hash,
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


def show_tags(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    if not args.manifest:
        rich.print("[red]No manifest file specified.[/red]")
        sys.exit(1)
    manifest = Manifest(args.manifest)
    for item in iter_files(args):
        tags = manifest.get_tags(item)
        if args.keys:
            tags = {k: v for k, v in tags.items() if k in args.keys}
        if not tags:
            if logger is not None:
                logger.debug(f"{item} has no tags.")
            continue
        if not args.format or args.format == "json":
            rich.print({item: list(tags.keys())})
        elif args.format == "json-details":
            rich.print({"filename": item, "tags": tags})
        elif args.format == "text":
            rich.print(f"""[cyan]{item}[/cyan]: {" ".join(tags.keys())}""")
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


def detect_nudity(
    filename: str, threshold: float | None, acceptable_tags: List[str] | None
) -> Tuple[str, Dict[str, Any]]:
    try:
        detector = NudeDetector()
        res = detector.detect(filename)
        # reorganize the result to be "class": {other elements}
        return filename, {
            x["class"]: {k: v for k, v in x.items() if k != "class"}
            for x in res
            if "class" in x
            and (threshold is None or x["score"] > threshold)
            and (acceptable_tags is None or x["class"] in acceptable_tags)
        }
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return filename, {}


def tag(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    if not args.manifest:
        rich.print("[red]No manifest file specified.[/red]")
        sys.exit(1)
    manifest = Manifest(args.manifest)
    if args.tags:
        for item in iter_files(args):
            if args.overwrite:
                manifest.set_tags(item, args.tags)
            else:
                manifest.add_tags(item, args.tags)
            cnt += 1
    else:
        with Pool() as pool:
            for item, tags in tqdm(
                pool.starmap(
                    detect_nudity,
                    {
                        (
                            x,
                            args.threshold,
                            (
                                tuple(args.acceptable_tags)
                                if args.acceptable_tags is not None
                                else args.acceptable_tags
                            ),
                        )
                        for x in iter_files(args)
                    },
                ),
                desc="Validate media",
            ):
                if args.overwrite:
                    manifest.set_tags(item, tags)
                else:
                    manifest.add_tags(item, tags)

        cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files tagged.")


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
            lambda x, filename_format=args.format, suffix=args.suffix or "", logger=logger: rename_file(
                x, filename_format, suffix, True, logger
            ),
        )
    else:
        for item in iter_files(args):
            if logger is not None:
                logger.info(f"Processing [blue]{item}[/blue]")
            rename_file(item, args.format, args.suffix or "", args.confirmed, logger)


def check_media_file(item: str) -> Tuple[str, str, bool]:
    return (
        item,
        calculate_file_hash(item),
        (any(item.endswith(x) for x in (".jpg", ".jpeg")) and not jpeg_openable(item))
        or (any(item.lower().endswith(x) for x in (".mp4", ".mpg")) and not mpg_playable(item)),
    )


def validate_media_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="validate")

    # if there is a manifest file, get the existing file hash
    if args.manifest:
        manifest = Manifest(args.manifest)

    if args.confirmed or not args.remove:
        with Pool() as pool:
            # get file size
            for item, new_hash, corrupted in tqdm(
                pool.imap(check_media_file, iter_files(args)),
                desc="Validate media",
            ):
                existing_hash = manifest.get_hash(item, None)
                if existing_hash is not None and existing_hash != new_hash:
                    if logger is not None:
                        logger.warning(f"[red][bold]{item}[/bold] is corrupted.[/red]")
                    continue
                if corrupted:
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is not playable.[/red]")
                    continue
                if args.manifest:
                    manifest.set_hash(item, new_hash)
    else:
        for item in iter_files(args):
            _, new_hash, corrupted = check_media_file(item)
            existing_hash = manifest.get_hash(item, None)
            if existing_hash is not None and existing_hash != new_hash:
                if logger is not None:
                    logger.warning(f"[red][bold]{item}[/bold] is corrupted.[/red]")
                if args.remove and (args.confirmed or get_response("Remove it?")):
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is removed.[/red]")
                    os.remove(item)
                continue
            if corrupted:
                if logger is not None:
                    logger.warning(f"[red][bold]{item}[/bold] is not playable.[/red]")
                if args.remove and (args.confirmed or get_response("Remove it?")):
                    if logger is not None:
                        logger.info(f"[red][bold]{item}[/bold] is removed.[/red]")
                    os.remove(item)
                continue
            if args.manifest:
                manifest.set_hash(item, new_hash)


def get_file_size(filename: str) -> Tuple[str, int]:
    return (filename, os.path.getsize(filename))


def get_file_md5(filename: str) -> Tuple[str, str]:
    return (filename, get_file_hash(os.path.abspath(filename)))


def remove_duplicated_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="dedup")

    md5_files = defaultdict(list)
    size_files = defaultdict(list)

    with Pool() as pool:
        # get file size
        for filename, filesize in tqdm(
            pool.imap(get_file_size, iter_files(args)), desc="Checking file size"
        ):
            size_files[filesize].append(filename)
        #
        # get md5 for files with the same size
        potential_duplicates = [file for x in size_files.values() if len(x) > 1 for file in x]
        for filename, md5 in tqdm(
            pool.imap(get_file_md5, potential_duplicates),
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


def compare_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="compare")

    a_sig_to_files = defaultdict(list)
    b_sig_to_files = defaultdict(list)
    a_file_to_sig = {}
    b_file_to_sig = {}

    a_files = args.items
    b_files = args.A_and_B or args.A_or_B or args.A_only or args.B_only

    with Pool() as pool:
        # get file size
        for filename, md5 in tqdm(
            pool.imap(get_file_md5, iter_files(args, a_files)), desc="Checking A file signature"
        ):
            if args.by == CompareBy.CONTENT.value:
                a_sig_to_files[md5].append(filename)
                a_file_to_sig[filename] = md5
            else:
                a_sig_to_files[(md5, os.path.basename(filename))].append(filename)
                a_file_to_sig[filename] = (md5, os.path.basename(filename))
        #
        for filename, md5 in tqdm(
            pool.imap(get_file_md5, iter_files(args, b_files)), desc="Checking B file signature"
        ):
            if args.by == CompareBy.CONTENT.value:
                b_sig_to_files[md5].append(filename)
                b_file_to_sig[filename] = md5
            else:
                b_sig_to_files[(md5, os.path.basename(filename))].append(filename)
                b_file_to_sig[filename] = (md5, os.path.basename(filename))

    def print_files(files_a: List[str], files_b: List[str]) -> None:
        if args.output == CompareOutput.A.value:
            print("=".join(files_a) if files_a else "=".join(files_b))
        elif args.output == CompareOutput.B.value:
            print("=".join(files_b) if files_b else "=".join(files_a))
        elif args.output == CompareOutput.BOTH.value:
            print("=".join(files_a + files_b))
        else:
            raise ValueError(f"Invalid value for --output: {args.output}")

    cnt = 0
    if args.A_and_B:
        # find items with the same md5
        result_sig = set(a_sig_to_files) & set(b_sig_to_files)
        filenames_in_a = sorted([a_sig_to_files[sig] for sig in result_sig], key=lambda x: x[0])
        for files_a in filenames_in_a:
            cnt += 1
            print_files(files_a, b_sig_to_files[a_file_to_sig[files_a[0]]])

    elif args.A_or_B:
        # if we compare by md5
        result_sig = set(a_sig_to_files) | set(b_sig_to_files)
        filename_sig = sorted(
            [
                (a_sig_to_files.get(sig, []) or b_sig_to_files.get(sig, []), sig)
                for sig in result_sig
            ],
            key=lambda x: x[0][0],
        )
        for _, sig in filename_sig:
            cnt += 1
            print_files(a_sig_to_files.get(sig, []), b_sig_to_files.get(sig, []))

    elif args.A_only:
        # find items with the same md5
        result_sig = set(a_sig_to_files) - set(b_sig_to_files)
        filenames_in_a = sorted([a_sig_to_files[sig] for sig in result_sig], key=lambda x: x[0])
        for files_a in filenames_in_a:
            cnt += 1
            print_files(files_a, [])

    elif args.B_only:
        # find items with the same md5
        result_sig = set(b_sig_to_files) - set(a_sig_to_files)
        filenames_in_b = sorted([b_sig_to_files[sig] for sig in result_sig], key=lambda x: x[0])
        for files_b in filenames_in_b:
            cnt += 1
            print_files([], files_b)

    if logger is not None:
        logger.info(f"[magenta]{cnt}[/magenta] files found.")


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
        "--search-paths",
        nargs="+",
        help="""Search paths for items to be processed if relative file or directory names are specified. The current directory will always be searched first.""",
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
        "--manifest",
        help="A manifest file that stores metadata such as file signature and tags.",
    )
    parser.add_argument(
        "--with-tags", nargs="*", help="Files that match one of the specified tags."
    )
    parser.add_argument(
        "--without-tags", nargs="*", help="Files that does not match any of the specified tags."
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
    # show tags of files
    #
    parser_show_tags = subparsers.add_parser(
        "show-tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parent_parser],
        help="Show all or selected tags",
    )
    parser_show_tags.add_argument("--keys", nargs="*", help="Show all or selected tags")
    parser_show_tags.add_argument(
        "--format",
        choices=("json", "text", "json-details", "text-details"),
        default="json",
        help="Show output in json or text format",
    )
    parser_show_tags.set_defaults(func=show_tags, command="show-tags")

    #
    # tag medias
    #
    parser_tag = subparsers.add_parser(
        "tag",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[parent_parser],
        help="Tag medias according to fixed tags or some machine learning model",
    )
    tag_type = parser_tag.add_mutually_exclusive_group(required=True)
    tag_type.add_argument("--tags", nargs="*", help="Tag medias")
    tag_type.add_argument(
        "--model",
        choices=("nudenet",),
        help="Machine learning model used to tag media.",
    )
    parser_tag.add_argument(
        "--acceptable-tags",
        nargs="*",
        help="Accept only specified tags. All other tags returned from the model will be ignored.",
    )
    parser_tag.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Shreshold for the model. Only classifiers with score greater than this value will be assigned.",
    )
    parser_tag.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove all existing tags.",
    )
    parser_tag.set_defaults(func=tag, command="tag")
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
    # compare: compare two sets of files or directories
    #
    parser_compare = subparsers.add_parser(
        "compare",
        parents=[parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Remove duplicated files.",
    )
    parser_compare.add_argument(
        "--no-cache",
        action="store_true",
        help="invalidate cached file signatures and re-examine all file content.",
    )
    action_parser = parser_compare.add_mutually_exclusive_group(required=True)
    action_parser.add_argument(
        "--A-and-B",
        nargs="+",
        help="Accept a list of files or directories, output files that exists in both collections.",
    )
    action_parser.add_argument(
        "--A-only",
        nargs="+",
        help="Accept a list of files or directories, output files that exists in A but not in B.",
    )
    action_parser.add_argument(
        "--B-only",
        nargs="+",
        help="Accept a list of files or directories, output files that exists in B but not in A.",
    )
    action_parser.add_argument(
        "--A-or-B",
        nargs="+",
        help="Accept a list of files or directories, output files that exists in either A or B.",
    )
    parser_compare.add_argument(
        "--by",
        choices=[x.value for x in CompareBy],
        default="content",
        help="""How to compare files. By default, files are considered the same as long as
            their contents are the same. If set to `name-and-content`, they need to have the
            same filename as well.""",
    )
    parser_compare.add_argument(
        "--output",
        choices=[x.value for x in CompareOutput],
        default="Both",
        help="""How to output a file if it exists in both A and B, potentially as multiple copies.
            By default filenames from two sets will be outputted on the same line, separate by a '='.
            For example, the output of "compare --A-and-B" will output fileA=fileB, potentially
            fileA=fileB1=fileB2 if fileB1 and fileB2 have the same file content. With option
            --output A, only "fileA" or "fileB1=fileB2" will be outputted.
            """,
    )
    parser_compare.set_defaults(func=compare_files, command="compare")
    #
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
    parser_organize.add_argument(
        "--operation",
        default="move",
        choices=[x.value for x in OrganizeOperation],
        help="How to organize the files. By default, files will be moved.",
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
    # if args if specified, manifest should be specified.
    if (args.with_tags or args.without_tags) and not args.manifest:
        raise ValueError("A manifest file is needed if with_tags or without_tags is specified.")
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
