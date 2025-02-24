import argparse
import logging
import sys
from multiprocessing import Pool
from pathlib import Path
from typing import List, Tuple, cast

import rich
from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .media_file import MediaFile

#
# set tags to media files
#


def verify_files(
    params: Tuple[Path, Tuple[str, ...] | None, float, logging.Logger | None]
) -> Tuple[Path, bool]:
    filename, benchmark_files, threshold, logger = params
    if benchmark_files is None:
        return filename, True
    from deepface import DeepFace  # type: ignore

    for benchmark_file in benchmark_files:
        try:
            res = DeepFace.verify(img1_path=filename, img2_path=benchmark_file)
            if logger is not None:
                logger.debug(f"Comparing {filename} with {benchmark_file}: {res}")
            if res["threshold"] > threshold:
                return filename, True
        except Exception as e:
            if logger is not None:
                logger.debug(f"Error comparing {filename} with {benchmark_file}: {e}")
            continue
    return filename, False


def set_tags(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    metadata = {}
    for item in args.metadata or []:
        if "=" not in item:
            rich.print(f"[red]Invalid metadata: {item}[/red]")
            sys.exit(1)
        k, v = item.split("=", 1)
        metadata[k] = v
    tags = {x: metadata for x in args.tags}

    if args.confirmed is not None:
        with Pool(args.jobs or None) as pool:
            for item, match in tqdm(
                pool.imap(
                    verify_files,
                    {
                        (
                            x,
                            (
                                tuple(cast(List[str], args.if_similar_to))
                                if args.if_similar_to is not None
                                else None
                            ),
                            float(args.threshold),
                            logger,
                        )
                        for x in iter_files(args)
                    },
                ),
                desc="Comparing media",
            ):
                if not match:
                    continue
                MediaFile(item).set_tags(tags, args.overwrite, args.confirmed, logger)
                cnt += 1
    else:
        # do the samething sequentially
        for item in tqdm(iter_files(args)):
            match = verify_files(
                (
                    item,
                    (
                        tuple(cast(List[str], args.if_similar_to))
                        if args.if_similar_to is not None
                        else None
                    ),
                    float(args.threshold),
                    logger,
                )
            )[1]
            if match:
                MediaFile(item).set_tags(tags, args.overwrite, args.confirmed, logger)
                cnt += 1
    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] files tagged.")


def get_set_tags_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "set-tags",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Tag all or similar media files",
    )
    parser.add_argument("--tags", nargs="*", help="Tags to be set to medis files")
    parser.add_argument(
        "--metadata",
        nargs="*",
        help="""Meta data set to tags, in the format of KEY=VALUE. These valuws will only
          be displayed with json-details or text-details of show-tags command.""",
    )
    parser.add_argument(
        "--if-similar-to",
        nargs="*",
        help="""A list of files that with which the files will be compared to. Only files that are
             similar to these files will be tagged.""",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="""A threshold for similarity between pictures. If multiple --if-similar-to files are specified,
            the media need to be similar to at least one of the files.""",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove all existing tags. By default this command will overwrite existing tags.",
    )
    parser.set_defaults(func=set_tags, command="set_tags")
    return parser
