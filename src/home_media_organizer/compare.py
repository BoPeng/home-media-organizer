import argparse
import logging
import os
from collections import defaultdict
from multiprocessing import Pool
from typing import List

from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .utils import CompareBy, CompareOutput, clear_cache, get_file_hash


#
# compare: compare two sets of files or directories
#
def compare_files(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    if args.no_cache:
        clear_cache(tag="compare")

    a_sig_to_files = defaultdict(list)
    b_sig_to_files = defaultdict(list)
    a_file_to_sig = {}
    b_file_to_sig = {}

    a_files = args.items
    b_files = args.A_and_B or args.A_or_B or args.A_only or args.B_only

    with Pool(args.jobs or None) as pool:
        # get file size
        for filename, md5 in tqdm(
            pool.imap(get_file_hash, iter_files(args, a_files)), desc="Checking A file signature"
        ):
            if args.by == CompareBy.CONTENT.value:
                a_sig_to_files[md5].append(filename)
                a_file_to_sig[filename] = md5
            else:
                a_sig_to_files[(md5, os.path.basename(filename))].append(filename)
                a_file_to_sig[filename] = (md5, os.path.basename(filename))
        #
        for filename, md5 in tqdm(
            pool.imap(get_file_hash, iter_files(args, b_files)), desc="Checking B file signature"
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


def get_compare_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser_compare: argparse.ArgumentParser = subparsers.add_parser(
        "compare",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Compare two sets of files",
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
    return parser_compare
