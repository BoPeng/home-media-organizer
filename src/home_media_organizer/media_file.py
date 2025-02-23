"""Main module."""

import filecmp
import fnmatch
import os
import re
import shutil
from datetime import datetime, timedelta
from logging import Logger
from pathlib import Path
from typing import Dict, List, Optional

import rich
from exiftool import ExifToolHelper  # type: ignore
from PIL import Image, UnidentifiedImageError

from .utils import OrganizeOperation, get_response


def image_date(filename: Path) -> str | None:
    try:
        i = Image.open(filename)
        date = None
        if hasattr(i, "_getexif"):
            exif_data = i._getexif()
            date = str(exif_data[36867])
        i.close()
        return date
    except (UnidentifiedImageError, AttributeError):
        return None


def exiftool_date(filename: Path) -> str | None:
    with ExifToolHelper() as e:
        metadata = e.get_metadata(filename)[0]
        if "QuickTime:MediaModifyDate" in metadata:
            return str(metadata["QuickTime:MediaModifyDate"])
        if "QuickTime:MediaCreateDate" in metadata:
            return str(metadata["QuickTime:MediaCreateDate"])
        if "EXIF:DateTimeOriginal" in metadata:
            return str(metadata["EXIF:DateTimeOriginal"])
        if "Composite:DateTimeOriginal" in metadata:
            return str(metadata["Composite:DateTimeOriginal"])
        return None


def filename_date(filename: Path) -> str:
    ext = filename.suffix
    basename = filename.name

    if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}.\d{2}" + ext, basename):
        return Path(basename).stem.replace("-", "").replace(".", "")

    if re.match(
        r"video-?\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2}" + ext,
        basename,
    ):
        return Path(basename).stem.replace("-", "").replace(".", "")[5:]

    matched = re.match(r"(\d{8})[_-](.*)" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}_{fld[1]}"

    matched = re.match(r"(\d{8})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}"

    matched = re.match(r"IMG_(\d{8})_(\d{6})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"
    matched = re.match(r"IMG_(\d{8})_(\d{6})_\d" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"

    matched = re.match(r"VID_(\d{8})_(\d{6})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"

    matched = re.match(r"PXL_(\d{8})_(\d{9})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"

    matched = re.match(
        r"video-(\d{4})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
        basename,
    )
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"

    matched = re.match(
        r"(\d{2})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
        basename,
    )
    if matched:
        fld = matched.groups()
        return f"20{fld[0]:0>2}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"

    matched = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})-(.{1,3})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"

    matched = re.match(r"(\d{2})-(\d{2})-(\d{2})_(.*)" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"20{fld[0]:0>2}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"

    matched = re.match(r"video-(\d{4})-(\d{2})-(\d{2})" + ext, basename)
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}"

    matched = re.match(
        r"voice-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})" + ext,
        basename,
    )
    if matched:
        fld = matched.groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]:0>2}{fld[4]:0>2}"

    raise ValueError(f"Cannot extract date from filename {filename}")


#
# how to handle each file type
#
date_func = {
    ".jpg": (image_date, exiftool_date, filename_date),
    ".jpeg": (image_date, exiftool_date, filename_date),
    ".tiff": (image_date,),
    ".cr2": (filename_date, exiftool_date, image_date),
    ".mp4": (exiftool_date, filename_date),
    ".mov": (exiftool_date,),
    ".3gp": (filename_date, exiftool_date),
    ".m4a": (exiftool_date, filename_date),
    ".mpg": (exiftool_date, filename_date),
    ".mp3": (exiftool_date, filename_date),
    ".wmv": (exiftool_date, filename_date),
    ".wav": (exiftool_date, filename_date),
    ".avi": (exiftool_date, filename_date),
    ".HEIC": (exiftool_date, filename_date),
}


date_func.update({x.upper(): y for x, y in date_func.items()})


class MediaFile:

    def __init__(self: "MediaFile", filename: Path) -> None:
        self.fullname = filename.resolve()
        self.dirname = filename.parent
        self.filename = filename.name
        self.ext: str = filename.suffix
        self.date: str | None = None

    @property
    def exif(self) -> Dict[str, str]:
        try:
            with ExifToolHelper() as e:
                return e.get_metadata([self.fullname])[0] or {}
        except Exception:
            return {}

    def get_date(self: "MediaFile") -> str:
        if self.date is None:
            funcs = date_func[self.ext]
            for func in funcs:
                try:
                    self.date = func(self.fullname)
                    if not self.date:
                        continue
                    if not self.date.startswith("2"):
                        raise ValueError(f"Invalid date {self.date}")
                    break
                except Exception:
                    continue
            if not self.date:
                return "19000101_000000"
            self.date = self.date.replace(":", "").replace(" ", "_")
        return self.date

    def show_exif(
        self: "MediaFile", keys: List[str] | None = None, output_format: str | None = None
    ) -> None:
        with ExifToolHelper() as e:
            metadata = e.get_metadata(self.fullname)[0]
            if keys is not None:
                if all("*" not in key for key in keys):
                    metadata = {k: metadata.get(k, "NA") for k in keys}
                else:
                    metadata = {
                        k: v
                        for k, v in metadata.items()
                        if any(fnmatch.fnmatch(k, key) for key in keys)
                    }

        if not output_format or output_format == "json":
            rich.print_json(data=metadata)
        else:
            for key, value in metadata.items():
                rich.print(f"[bold blue]{key}[/bold blue]=[green]{value}[/green]")
            rich.print()

    def intended_prefix(self: "MediaFile", filename_format: str = "%Y%m%d_%H%M%S") -> str:
        date = self.get_date()
        if not date:
            date = Path(self.filename).stem
            date = date.replace(":", "").replace(" ", "_")
        try:
            filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
            if filedate.year < 1980:
                raise ValueError(f"Invalid date {date}")
            return filedate.strftime(filename_format)
        except Exception:
            # do not rename
            return Path(self.filename).stem

    def intended_name(
        self: "MediaFile", filename_format: str = "%Y%m%d_%H%M%S", suffix: str = ""
    ) -> str:
        return self.intended_prefix(filename_format=filename_format) + suffix + self.ext.lower()

    def intended_path(
        self: "MediaFile", root: str, dir_pattern: str, album: str, album_sep: str
    ) -> Path:
        date = self.get_date()
        try:
            filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
            subdir = filedate.strftime(
                dir_pattern if not album else dir_pattern + album_sep + album
            )
            if filedate.year < 1980:
                raise ValueError(f"Invalid date {date}")
        except Exception:
            return self.dirname
        return Path(root) / subdir

    def shift_exif(
        self: "MediaFile",
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        keys: Optional[List[str]] = None,
        confirmed: bool = False,
        logger: Optional[Logger] = None,
    ) -> None:  # pylint: disable=too-many-positional-arguments
        # add one or more 0: if the format is not YY:DD:HH:MM
        # Calculate the total shift in timedelta
        shift_timedelta = timedelta(
            days=days, hours=hours, weeks=weeks, minutes=minutes, seconds=seconds
        )
        with ExifToolHelper() as e:
            metadata = e.get_metadata(self.fullname)[0]
            changes = {}
            for k, v in metadata.items():
                if not k.endswith("Date") or (keys and k not in keys):
                    continue
                if "-" in v:
                    hrs, sec = v.split("-")
                    sec = "-" + sec
                elif "+" in v:
                    hrs, sec = v.split("+")
                    sec = "+" + sec
                else:
                    hrs = v
                    sec = ""
                original_datetime = datetime.strptime(hrs, "%Y:%m:%d %H:%M:%S")
                if years:
                    original_datetime = original_datetime.replace(
                        year=original_datetime.year + years
                    )
                #
                if months:
                    new_month = original_datetime.month + months
                    if new_month > 12:
                        original_datetime = original_datetime.replace(
                            year=original_datetime.year + new_month // 12
                        )
                        new_month = new_month % 12
                    elif new_month < 1:
                        original_datetime = original_datetime.replace(
                            year=original_datetime.year + new_month // 12 - 1
                        )
                        new_month = new_month % 12 + 12
                    #
                    original_datetime = original_datetime.replace(month=new_month)
                #
                new_datetime = original_datetime + shift_timedelta
                if new_datetime >= datetime.now():
                    if logger is not None:
                        logger.info(f"[magenta]Ignore future date {new_datetime}[/magenta].")
                elif k == "File:FileModifyDate":
                    if confirmed or get_response(
                        f"Modify file modified date {self.fullname.name} to {new_datetime}?"
                    ):
                        # Convert the new modification time to a timestamp
                        new_mod_time = new_datetime.timestamp()
                        # Set the new modification time
                        os.utime(self.fullname, (new_mod_time, new_mod_time))
                elif k.startswith("File:"):
                    if logger is not None:
                        logger.info(f"[magenta]Ignore non-EXIF meta information {k}[/magenta]")
                else:
                    new_v = new_datetime.strftime("%Y:%m:%d %H:%M:%S") + sec
                    changes[k] = new_v
            if not changes:
                return
            for k, new_v in changes.items():
                if logger is not None:
                    logger.info(
                        f"Shift {k} from [magenta]{metadata[k]}[/magenta] to [blue]{new_v}[/blue]"
                    )
            #
            if confirmed or get_response(f"Shift dates of {self.fullname.name} as shown above?"):
                e.set_tags([self.fullname], tags=changes)

    def set_exif(
        self: "MediaFile",
        values: Dict[str, str],
        override: bool = False,
        confirmed: bool = False,
        logger: Logger | None = None,
    ) -> None:
        # add one or more 0: if the format is not YY:DD:HH:MM
        with ExifToolHelper() as e:
            metadata = e.get_metadata(self.fullname)[0]
            changes = {}
            for k, v in values.items():
                if k in metadata and not override and not k.startswith("File:"):
                    if logger is not None:
                        logger.info(f"[magenta]Ignore existing {k} = {metadata[k]}[/magenta]")
                    continue
                if k == "File:FileModifyDate":
                    if confirmed or get_response(
                        f"Modify file modified date {self.fullname.name} to {v}?"
                    ):
                        try:
                            new_datetime = datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
                            # Convert the new modification time to a timestamp
                            new_mod_time = new_datetime.timestamp()
                            # Set the new modification time
                            os.utime(self.fullname, (new_mod_time, new_mod_time))
                            if logger is not None:
                                logger.info(
                                    f"Set File:FileModifyDate of [magenta]{self.filename}[/magenta] to [blue]{v}[/blue]"
                                )
                        except ValueError:
                            if logger:
                                logger.error(f"[red]Invalid date format {v}[/red]")
                elif k.startswith("File:"):
                    if logger is not None:
                        logger.info(f"[magenta]Ignore non-EXIF meta information {k}[/magenta]")
                else:
                    if logger is not None:
                        logger.info(
                            f"Set {k} of [magenta]{self.filename}[/magenta] to [blue]{v}[/blue]"
                        )
                    changes[k] = v
            if not changes:
                return
            if confirmed or get_response(f"Set exif of {self.fullname}"):
                if logger is not None:
                    logger.info(f"EXIF data of [blue]{self.filename}[/blue] is updated.")
                e.set_tags([self.fullname], tags=changes, params=["-P", "-overwrite_original"])
                exif = self.exif
                for k, v in changes.items():
                    if k not in exif or exif[k] != v:
                        raise ValueError(
                            f"Failed to set {k} to {v}. Operation might not be supported."
                        )

    # def name_ok(self: "MediaFile") -> bool:
    #     return re.match(r"2\d{7}(_.*)?" + self.ext.lower(), self.filename)

    # def path_ok(self: "MediaFile", root: str, subdir: str = "") -> bool:
    #     intended_path = self.intended_path(root, subdir)
    #     return self.fullname.startswith(intended_path)

    def rename(
        self: "MediaFile",
        filename_format: str = "%Y%m%d_%H%M%S",
        suffix: str = "",
        confirmed: bool = False,
        logger: Logger | None = None,
        attempt: int = 0,
    ) -> None:
        intended_name = self.intended_name(filename_format=filename_format, suffix=suffix)
        # allow the name to be xxxxxx_xxxxx-someotherstuff
        if self.filename == intended_name:
            return
        elif self.filename.startswith(self.intended_prefix(filename_format=filename_format)):
            if logger is not None:
                logger.info(
                    f"File [blue]{self.filename}[/blue] already has the intended date prefix."
                )
            return

        if attempt > 10:
            if logger is not None:
                logger.info("Failed to rename after 10 attempts. There must be something wrong.")
            return
        elif attempt > 0:
            n, e = Path(intended_name).stem, Path(intended_name).suffix
            nn = f"{n}_{attempt}{e}"
        else:
            nn = intended_name

        new_file = self.dirname / nn

        try:
            if new_file.is_file():
                if self.fullname.samefile(new_file):
                    return
                if filecmp.cmp(self.fullname, new_file, shallow=False):
                    if confirmed or get_response(
                        f"Rename {self.fullname} to an existing file {new_file}"
                    ):
                        os.remove(self.fullname)
                        if logger is not None:
                            logger.info(
                                f"Removed duplicated file [blue]{self.fullname.name}[/blue]"
                            )
                    return
                return self.rename(filename_format, suffix, confirmed, logger, attempt + 1)

            if confirmed or get_response(
                f"Rename [blue]{self.fullname}[/blue] to [blue]{new_file.name}[/blue]"
            ):
                os.rename(self.fullname, new_file)
                if logger is not None:
                    logger.info(
                        f"Renamed [blue]{self.fullname.name}[/blue] to [green]{new_file}[/green]"
                    )
        except Exception as e:
            return self.rename(filename_format, suffix, confirmed, logger, attempt + 1)

    def organize(
        self: "MediaFile",
        media_root: str,
        dir_pattern: str,
        album: str = "",
        album_sep: str = "-",
        operation: OrganizeOperation = OrganizeOperation.MOVE,
        confirmed: bool = False,
        logger: Logger | None = None,
        attempt: int = 0,
    ) -> None:
        intended_path = self.intended_path(media_root, dir_pattern, album, album_sep)
        if intended_path.is_relative_to(self.fullname):
            return

        if attempt > 10:
            if logger is not None:
                logger.info("Failed to rename after 10 attempts. There must be something wrong.")
            return
        elif attempt > 0:
            n, e = Path(self.filename).stem, Path(self.filename).suffix
            nn = f"{n}_{attempt}{e}"
        else:
            nn = self.filename

        new_file = intended_path / nn

        if confirmed or get_response(
            f"{operation.value.capitalize()} [blue]{self.fullname}[/blue] to [blue]{intended_path}[/blue]"
        ):
            os.makedirs(intended_path, exist_ok=True)

            try:
                if new_file.is_file():
                    if filecmp.cmp(self.fullname, new_file, shallow=False):
                        if operation == OrganizeOperation.MOVE:
                            os.remove(self.fullname)
                            if logger is not None:
                                logger.info(f"Remove duplicated file {self.fullname}")
                        else:
                            if logger is not None:
                                logger.info(f"Retain duplicated file {self.fullname}")
                        return
                    return self.organize(
                        media_root,
                        dir_pattern,
                        album,
                        album_sep,
                        operation,
                        confirmed,
                        logger,
                        attempt + 1,
                    )
                if operation == OrganizeOperation.COPY:
                    shutil.copy2(self.fullname, new_file)
                    if logger is not None:
                        logger.info(
                            f"Copied [blue]{self.fullname.name}[/blue] to [green]{new_file}[/green]"
                        )
                else:
                    shutil.move(self.fullname, new_file)
                    if logger is not None:
                        logger.info(
                            f"Moved [blue]{self.fullname.name}[/blue] to [green]{new_file}[/green]"
                        )
            except Exception as e:
                return self.organize(
                    media_root,
                    dir_pattern,
                    album,
                    album_sep,
                    operation,
                    confirmed,
                    logger,
                    attempt + 1,
                )
