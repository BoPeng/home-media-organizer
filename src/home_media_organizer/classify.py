import argparse
import logging
import sys
from multiprocessing import Pool
from typing import Any, Dict, Tuple

import rich
from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .media_file import MediaFile
from .utils import Manifest


#
# tag medias with results from a classifier
#
def classify_image(
    params: Tuple[
        str, Tuple[str], float | None, int | None, Tuple[str] | None, logging.Logger | None
    ]
) -> Tuple[str, Dict[str, Any]]:
    filename, models, threshold, top_k, tags, logger = params
    m = MediaFile(filename)
    return m.fullname, m.classify(models, threshold, top_k, tags, logger)


def classify(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    processed_cnt = 0
    if not args.manifest:
        rich.print("[red]No manifest file specified.[/red]")
        sys.exit(1)
    manifest = Manifest(args.manifest, logger=logger)

    # download the model if needed
    with Pool(1) as pool:
        for item, tags in tqdm(
            pool.imap(
                classify_image,
                {
                    (
                        x,
                        tuple(args.models),
                        args.threshold,
                        args.top_k,
                        (tuple(args.tags) if args.tags is not None else args.tags),
                        logger,
                    )
                    for x in iter_files(args)
                },
            ),
            desc="Classifying media",
        ):
            if "error" in tags:
                if logger is not None:
                    logger.error(f"Error processing {item}: {tags['error']}")
                continue
            if not tags:
                continue
            if logger:
                logger.debug(f"Tagging {item} with {tags}")
            if args.overwrite:
                manifest.set_tags(item, tags)
            else:
                manifest.add_tags(item, tags)

            processed_cnt += 1
            if tags:
                cnt += 1

    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] of {processed_cnt} files are tagged.")


def get_classify_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "classify",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        # parents=[parent_parser],
        help="Classify photos and assign results as tags to media files.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["nudenet", "age", "gender", "race", "emotion"],
        help="Machine learning models used to tag media.",
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        help="Accept only specified tags. All other tags returned from the model will be ignored.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Shreshold for the model. Only classifiers with score greater than this value will be assigned.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Choose the top k predictor.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove all existing tags.",
    )
    parser.set_defaults(func=classify, command="classify")
    return parser
