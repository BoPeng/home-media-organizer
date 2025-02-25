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
        Path,
        Tuple[str],
        float | None,
        int | None,
        Tuple[str] | None,
        str | None,
        logging.Logger | None,
    ]
) -> Tuple[Path, Dict[str, Any]]:
    filename, models, threshold, top_k, tags, suffix, logger = params
    res: Dict[str, Any] = {}
    fullname = filename.resolve()
    for model_name in models:
        model_class: Type[Classifier] = get_classifier_class(model_name)
        model = model_class(model_name, threshold, top_k, tags, suffix, logger)
        res |= model.classify(fullname)

    return fullname, res


def classify(args: argparse.Namespace, logger: logging.Logger | None) -> None:
    cnt = 0
    processed_cnt = 0

    # download the model if needed
    if args.confirmed is not None:
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
                            args.suffix,
                            logger,
                        )
                        for x in iter_files(args)
                    },
                ),
                desc="Classifying media",
                disable=not args.progress,
            ):
                if not tags:
                    continue
                if logger:
                    logger.debug(f"Tagging {item} with {tags}")
                MediaFile(item).set_tags(tags, args.overwrite, args.confirmed, logger)

                processed_cnt += 1
                if tags:
                    cnt += 1
    else:
        # interactive mode
        for item in iter_files(args, logger=logger):
            tags = classify_image(
                (
                    item,
                    tuple(args.models),
                    args.threshold,
                    args.top_k,
                    (tuple(args.tags) if args.tags is not None else args.tags),
                    args.suffix,
                    logger,
                )
            )[1]
            if tags:
                MediaFile(item).set_tags(tags, args.overwrite, args.confirmed, logger)
                cnt += 1
            processed_cnt += 1
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
    feature = "generic"
    default_model = ""
    allowed_models: Tuple[str, ...] = ()
    default_option = ""
    allowed_options: Tuple[str, ...] = ()
    labels: Tuple[str, ...] = ()

    def __init__(
        self,
        full_name: str,
        threshold: float | None,
        top_k: int | None,
        tags: Tuple[str] | None,
        suffix: str | None,
        logger: logging.Logger | None,
    ) -> None:

        pieces = full_name.split(":")
        self.feature = pieces[0]
        self.model_name: str = pieces[1] if len(pieces) > 1 else self.default_model
        self.model_option: str = pieces[2] if len(pieces) > 2 else self.default_option
        self.fullname = f"{self.feature}:{self.model_name}:{self.model_option}".rstrip(":")
        self.threshold = threshold
        self.top_k = top_k
        self.tags = tags
        self.suffix = suffix or ""
        self.logger = logger
        if self.model_name not in self.allowed_models:
            raise ValueError(
                f"""{self.feature} does not support model {self.model_name}. Please choose from {", ".join(self.allowed_models)}"""
            )
        if self.model_option not in self.allowed_options:
            raise ValueError(
                f"""{self.feature} does not support model option {self.model_name}. Please choose from {", ".join(self.allowed_options)}"""
            )
        #
        # tags could be specified across models
        # for tag in self.tags or []:
        #     if tag not in self.labels:
        #         raise ValueError(f"{self.feature} does not support tag: {tag}")

    def _cache_key(self, filename: Path) -> Tuple[str, str, str, str]:
        return (self.feature, self.model_name or "", self.model_option or "", str(filename))

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError()

    def classify(self, filename: Path) -> Dict[str, Any]:
        key = self._cache_key(filename)
        res = cache.get(key, None)
        if not res:
            res = self._classify(filename)
            # if detection failed, the picture will be detected again and again
            # which might not be a good idea
            if res:
                cache.set(key, res, tag="classify")
        if self.logger is not None:
            self.logger.debug(
                f"{filename=} model={self.fullname}:{self.model_option or 'default'} {res=}"
            )
        return self._filter_tags(res)


class NSFWClassifier(Classifier):
    feature = "nsfw"
    default_model = "nudenet"
    allowed_models = ("nudenet",)
    default_option = ""
    allowed_options = ()

    labels = (
        "FEMALE_GENITALIA_COVERED",
        "FACE_FEMALE",
        "BUTTOCKS_EXPOSED",
        "FEMALE_BREAST_EXPOSED",
        "FEMALE_GENITALIA_EXPOSED",
        "MALE_BREAST_EXPOSED",
        "ANUS_EXPOSED",
        "FEET_EXPOSED",
        "BELLY_COVERED",
        "FEET_COVERED",
        "ARMPITS_COVERED",
        "ARMPITS_EXPOSED",
        "FACE_MALE",
        "BELLY_EXPOSED",
        "MALE_GENITALIA_EXPOSED",
        "ANUS_COVERED",
        "FEMALE_BREAST_COVERED",
        "BUTTOCKS_COVERED",
    )

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from nudenet import NudeDetector  # type: ignore

        detector = NudeDetector()
        try:
            return cast(List[Dict[str, Any]], detector.detect(str(filename)))
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["class"] + self.suffix: {k: v for k, v in x.items() if k != "class"}
            | {"model": self.fullname}
            for x in res
            if "class" in x
            and (self.threshold is None or x["score"] > self.threshold)
            and (self.tags is None or x["class"] in self.tags)
        }


deepface_models = (
    "VGG-Face",
    "Facenet",
    "Facenet512",
    "OpenFace",
    "DeepFace",
    "DeepID",
    "ArcFace",
    "Dlib",
    "SFace",
    "GhostFaceNet",
)

deepface_backends = (
    "opencv",
    "retinaface",
    "mtcnn",
    "ssd",
    "dlib",
    "mediapipe",
    "yolov8",
    "yolov11n",
    "yolov11s",
    "yolov11m",
    "centerface",
    "skip",
)


class FaceClassifier(Classifier):
    feature = "face"
    default_model = "deepface"
    allowed_models = ("deepface",)
    default_option = "opencv"
    allowed_options = deepface_backends
    labels = ("face",)

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]],
                DeepFace.extract_faces(
                    img_path=str(filename),
                    detector_backend=self.model_option,
                    enforce_detection=True,
                ),
            )
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "face"
            + self.suffix: np_to_scalar(
                {
                    k: v
                    for k, v in x.items()
                    if k in ("facial_area", "left_eye", "right_eye", "confidence")
                }
            )
            | {"model": self.fullname}
            for x in res
            if "face" in x
            and (self.threshold is None or x["confidence"].item() > self.threshold)
            and (self.tags is None or "Face" in self.tags)
        }


class AgeClassifier(Classifier):
    feature = "age"
    default_model = "deepface"
    allowed_models = ("deepface",)
    default_option = "opencv"
    allowed_options = deepface_backends
    labels = ("baby", "toddler", "teenager", "adult", "elderly")

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]],
                DeepFace.analyze(
                    img_path=str(filename),
                    actions=["age"],
                    detector_backend=self.model_option,
                ),
            )
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            get_age_label(x["age"]) + self.suffix: np_to_scalar(x) | {"model": self.fullname}
            for x in res
            if "age" in x and (self.tags is None or get_age_label(x["age"]) in self.tags)
        }


class GenderClassifier(Classifier):
    feature = "gender"
    default_model = "deepface"
    allowed_models = ("deepface",)
    default_option = "opencv"
    allowed_options = deepface_backends
    labels = ("Woman", "Man")

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]],
                DeepFace.analyze(
                    img_path=str(filename),
                    actions=["gender"],
                    detector_backend=self.model_option,
                    force_detection=True,
                ),
            )
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_gender"] + self.suffix: {x: np_to_scalar(y) for x, y in x.items()}
            | {"model": self.fullname}
            for x in res
            if "dominant_gender" in x
            and (
                self.threshold is None
                or any(value > self.threshold for value in x["gender"].values())
            )
            and (self.tags is None or x["dominant_gender"] in self.tags)
        }


class RaceClassifier(Classifier):
    feature = "race"
    default_model = "deepface"
    allowed_models = ("deepface",)
    default_option = "opencv"
    allowed_options = deepface_backends
    labels = ("asian", "indian", "black", "white", "middle eastern", "latino hispanic")

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]],
                DeepFace.analyze(
                    img_path=str(filename),
                    actions=["race"],
                    detector_backend=self.model_option,
                ),
            )
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_race"] + self.suffix: {x: np_to_scalar(y) for x, y in x.items()}
            | {"model": self.fullname}
            for x in res
            if "dominant_race" in x
            and (
                self.threshold is None
                or any(value > self.threshold for value in x["race"].values())
            )
            and (self.tags is None or x["dominant_race"] in self.tags)
        }


class EmotionClassifier(Classifier):
    feature = "emotion"
    default_model = "deepface"
    allowed_models = ("deepface",)
    default_option = "opencv"
    allowed_options = deepface_backends
    labels = ("angry", "disgust", "fear", "happy", "sad", "surprise", "neutral")

    def _classify(self, filename: Path) -> List[Dict[str, Any]]:
        from deepface import DeepFace  # type: ignore

        try:
            return cast(
                List[Dict[str, Any]],
                DeepFace.analyze(
                    img_path=str(filename),
                    actions=["emotion"],
                    detector_backend=self.model_option,
                    enforce_detection=True,
                ),
            )
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error classifying {filename}: {e}")
            return []

    def _filter_tags(self, res: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            x["dominant_emotion"] + self.suffix: {x: np_to_scalar(y) for x, y in x.items()}
            | {"model": self.fullname}
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
        NSFWClassifier.feature: NSFWClassifier,
        AgeClassifier.feature: AgeClassifier,
        GenderClassifier.feature: GenderClassifier,
        RaceClassifier.feature: RaceClassifier,
        EmotionClassifier.feature: EmotionClassifier,
        FaceClassifier.feature: FaceClassifier,
    }[model_name.split(":")[0]]


def get_classify_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:

    parser: argparse.ArgumentParser = subparsers.add_parser(
        "classify",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Classify and assign results as tags to media files",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="""Machine learning models used to tag media. Each model can be a
            feature such as "face", "age", "gender", "emotion", and "nsfw", followed
            by an optional model name. Please see the documentation for a list of
            supported features and models.""",
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
        "--suffix",
        help="""A suffix appended to the default labels, in case multiple models are used for the same feature.""",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove all existing tags.",
    )
    parser.set_defaults(func=classify, command="classify")
    return parser
