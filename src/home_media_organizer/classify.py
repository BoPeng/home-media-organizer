import argparse
import logging
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Dict, Generic, List, Tuple, Type, TypeVar, cast

import numpy as np
from tqdm import tqdm  # type: ignore

from .home_media_organizer import iter_files
from .media_file import MediaFile
from .utils import cache


#
# tag medias with results from a classifier
#
def classify_image(
    params: Tuple[
        Path, Tuple[str], float | None, int | None, Tuple[str] | None, logging.Logger | None
    ]
) -> Tuple[Path, Dict[str, Any]]:
    filename, models, threshold, top_k, tags, logger = params
    res: Dict[str, Any] = {}
    fullname = filename.resolve()
    for model_name in models:
        model_class: Type[Classifier] = get_classifier_class(model_name)
        model = model_class(threshold, top_k, tags, logger)
        res |= model.classify(fullname)

    return fullname, res


def classify(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    processed_cnt = 0

    # download the model if needed
    with Pool(args.jobs or None) as pool:
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
            MediaFile(item).set_tags(tags, args.overwrite, args.confirmed, logger)

            processed_cnt += 1
            if tags:
                cnt += 1

    if logger is not None:
        logger.info(f"[blue]{cnt}[/blue] of {processed_cnt} files are tagged.")


def np_to_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    elif isinstance(value, dict):
        return {k: np_to_scalar(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [np_to_scalar(x) for x in value]
    return value


def get_age_label(age: int) -> str:
    # create a label of "baby", "toddler", "teenager", "adult", "elderly" based on age
    if age < 3:
        return "baby"
    elif age < 12:
        return "toddler"
    elif age < 20:
        return "teenager"
    elif age < 60:
        return "adult"
    else:
        return "elderly"


TClassifier = TypeVar("TClassifier", bound="Classifier")


class Classifier(Generic[TClassifier]):
    name = "generic"

    def __init__(
        self,
        threshold: float | None,
        top_k: int | None,
        tags: Tuple[str] | None,
        logger: logging.Logger | None,
    ) -> None:
        self.threshold = threshold
        self.top_k = top_k
        self.tags = tags
        self.logger = logger

    def _cache_key(self, filename: Path) -> Tuple[str, str]:
        return (self.name, str(filename))

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError()

    def classify(self, filename: Path) -> Dict[str, Any]:
        key = self._cache_key(filename)
        res = cache.get(key, None)
        if res is None:
            res = self._classify(filename)
            cache.set(key, res, tag="classify")
        return self._filter_tags(res)


class NudeNetClassifier(Classifier):
    name = "nudenet"

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from nudenet import NudeDetector  # type: ignore

        detector = NudeDetector()
        try:
            return cast(List[Dict[str, Any]], detector.detect(filename))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["class"]: {k: v for k, v in x.items() if k != "class"} | {"model": self.name}
            for x in res
            if "class" in x
            and (self.threshold is None or x["score"] > self.threshold)
            and (self.tags is None or x["class"] in self.tags)
        }


class AgeClassifier(Classifier):
    name = "age"

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(List[Dict[str, Any]], DeepFace.analyze(img_path=filename, actions=["age"]))
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            get_age_label(x["age"]): x | {"model": self.name}
            for x in res
            if "age" in x and (self.tags is None or get_age_label(x["age"]) in self.tags)
        }


class GenderClassifier(Classifier):
    name = "gender"

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]], DeepFace.analyze(img_path=filename, actions=["gender"])
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_gender"]: {x: np_to_scalar(y) for x, y in x.items()} | {"model": self.name}
            for x in res
            if "dominant_gender" in x
            and (
                self.threshold is None
                or any(value > self.threshold for value in x["gender"].values())
            )
            and (self.tags is None or x["dominant_gender"] in self.tags)
        }


class RaceClassifier(Classifier):
    name = "race"

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]], DeepFace.analyze(img_path=filename, actions=["race"])
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_race"]: {x: np_to_scalar(y) for x, y in x.items()} | {"model": self.name}
            for x in res
            if "dominant_race" in x
            and (
                self.threshold is None
                or any(value > self.threshold for value in x["race"].values())
            )
            and (self.tags is None or x["dominant_race"] in self.tags)
        }


class EmotionClassifier(Classifier):
    name = "emotion"

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]], DeepFace.analyze(img_path=filename, actions=["emotion"])
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_emotion"]: {x: np_to_scalar(y) for x, y in x.items()}
            | {"model": self.name}
            for x in res
            if "dominant_emotion" in x
            and (
                self.threshold is None
                or any(value > self.threshold for value in x["emotion"].values())
            )
            and (self.tags is None or x["dominant_emotion"] in self.tags)
        }


def get_classifier_class(model_name: str) -> Type[Classifier]:
    return {
        NudeNetClassifier.name: NudeNetClassifier,
        AgeClassifier.name: AgeClassifier,
        GenderClassifier.name: GenderClassifier,
        RaceClassifier.name: RaceClassifier,
        EmotionClassifier.name: EmotionClassifier,
    }[model_name]


def get_classify_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "classify",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Classify and assign results as tags to media files",
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
