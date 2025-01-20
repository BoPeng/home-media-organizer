"""Main module."""

import filecmp
import fnmatch
import os
import re
import shutil
from datetime import datetime, timedelta
from typing import List, Optional

import rich
from exiftool import ExifToolHelper
from PIL import Image, UnidentifiedImageError

from .utils import get_response


def Image_date(filename: str):
    try:
        i = Image.open(filename)
        date = str(i._getexif()[36867])
        i.close()
        return date
    except (UnidentifiedImageError, AttributeError):
        return None


def exiftool_date(filename: str):
    with ExifToolHelper() as e:
        metadata = e.get_metadata(filename)[0]
        if "QuickTime:MediaModifyDate" in metadata:
            return metadata["QuickTime:MediaModifyDate"]
        if "QuickTime:MediaCreateDate" in metadata:
            return metadata["QuickTime:MediaCreateDate"]
        if "EXIF:DateTimeOriginal" in metadata:
            return metadata["EXIF:DateTimeOriginal"]
        if "Composite:DateTimeOriginal" in metadata:
            return metadata["Composite:DateTimeOriginal"]
        return None


def filename_date(filename: str):
    ext = os.path.splitext(filename)[-1]
    if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}.\d{2}" + ext, os.path.basename(filename)):
        fn, ext = os.path.splitext(os.path.basename(filename))
        return fn.replace("-", "").replace(".", "")
    if re.match(
        r"video-?\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2}" + ext,
        os.path.basename(filename),
    ):
        fn, ext = os.path.splitext(os.path.basename(filename))
        return fn.replace("-", "").replace(".", "")[5:]
    if re.match(r"\d{8}[_-].*" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{8})[_-](.*)" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}_{fld[1]}"
    if re.match(r"\d{8}" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{8})" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}"
    if re.match(r"IMG_\d{8}_\d{6}" + ext, os.path.basename(filename)):
        fld = re.match(r"IMG_(\d{8})_(\d{6})" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"
    if re.match(r"IMG_\d{8}_\d{6}_\d" + ext, os.path.basename(filename)):
        fld = re.match(r"IMG_(\d{8})_(\d{6})_\d" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"
    if re.match(r"VID_\d{8}_\d{6}" + ext, os.path.basename(filename)):
        fld = re.match(r"VID_(\d{8})_(\d{6})" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"
    if re.match(r"PXL_\d{8}_\d{9}" + ext, os.path.basename(filename)):
        fld = re.match(r"PXL_(\d{8})_(\d{9})" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>8}_{fld[1]:1}"
    if re.match(r"video-\d{4}[\.-]\d{1,2}[\.-]\d{1,2}-.+" + ext, os.path.basename(filename)):
        fld = re.match(
            r"video-(\d{4})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
            os.path.basename(filename),
        ).groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"
    if re.match(r"\d{2}[\.-]\d{1,2}[\.-]\d{1,2}-.+" + ext, os.path.basename(filename)):
        fld = re.match(
            r"(\d{2})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
            os.path.basename(filename),
        ).groups()
        return f"20{fld[0]:0>2}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"
    if re.match(r"\d{4}-\d{1,2}-\d{1,2}-.{1,3}" + ext, os.path.basename(filename)):
        fld = re.match(
            r"(\d{4})-(\d{1,2})-(\d{1,2})-(.{1,3})" + ext, os.path.basename(filename)
        ).groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"
    if re.match(r"\d{2}-\d{2}-\d{2}_.+" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{2})-(\d{2})-(\d{2})_(.*)" + ext, os.path.basename(filename)).groups()
        return f"20{fld[0]:0>2}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]}"
    if re.match(r"video-\d{4}-\d{2}-\d{2}" + ext, os.path.basename(filename)):
        fld = re.match(r"video-(\d{4})-(\d{2})-(\d{2})" + ext, os.path.basename(filename)).groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}"
    if re.match(r"voice-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}" + ext, os.path.basename(filename)):
        fld = re.match(
            r"voice-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})" + ext,
            os.path.basename(filename),
        ).groups()
        return f"{fld[0]:0>4}{fld[1]:0>2}{fld[2]:0>2}_{fld[3]:0>2}{fld[4]:0>2}"
    raise ValueError(f"Cannot extract date from filename {filename}")


#
# how to handle each file type
#
date_func = {
    ".jpg": (Image_date, exiftool_date, filename_date),
    ".jpeg": (Image_date, exiftool_date, filename_date),
    ".tiff": (Image_date,),
    ".cr2": (filename_date, exiftool_date, Image_date),
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

    def __init__(self: "MediaFile", filename: str, verbose: bool = True):
        self.fullname = os.path.abspath(filename)
        self.dirname, self.filename = os.path.split(self.fullname)
        self.ext = os.path.splitext(self.filename)[-1]
        self.verbose = verbose
        self.date = None
        self.md5 = None

    def size(self: "MediaFile"):
        return os.path.getsize(self.fullname)

    def get_date(self: "MediaFile"):
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
                except Exception as e:
                    if self.verbose:
                        print(f"{self.fullname}: {e}")
                    continue
            if not self.date:
                return "19000101_000000"
            self.date = self.date.replace(":", "").replace(" ", "_")
        return self.date

    def show_exif(self: "MediaFile", keys: List[str] | None = None, format: str | None = None):
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

        if not format or format == "json":
            rich.print_json(data=metadata)
        else:
            for key, value in metadata.items():
                rich.print(f"[bold blue]{key}[/bold blue]=[green]{value}[/green]")
            rich.print()

    def intended_prefix(self: "MediaFile", format: str = "%Y%m%d_%H%M%S"):
        date = self.get_date()
        if not date:
            date = os.path.split(os.path.basename(self.fullname))[0]
            date = date.replace(":", "").replace(" ", "_")
        if format == "%Y%m%d_%H%M%S":
            return date
        filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
        return filedate.strftime(format)

    def intended_name(self: "MediaFile", format: str = "%Y%m%d_%H%M%S"):
        return self.intended_prefix(format=format) + self.ext.lower()

    def intended_path(self: "MediaFile", root: str, dir_pattern: str, album: str):
        date = self.get_date()
        filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
        subdir = filedate.strftime(dir_pattern)
        return os.path.join(root, subdir, album or "")

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
    ):  # pylint: disable=too-many-positional-arguments
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
                # print(f'{k}: {v}')
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
                    rich.print(f"[magenta]Ignore future date {new_datetime}[/magenta].")
                elif k == "File:FileModifyDate":
                    if confirmed or get_response(
                        f"Modify file modified date {os.path.basename(self.fullname)} to {new_datetime}?"
                    ):
                        # Convert the new modification time to a timestamp
                        new_mod_time = new_datetime.timestamp()
                        # Set the new modification time
                        os.utime(self.fullname, (new_mod_time, new_mod_time))
                elif k.startswith("File:"):
                    rich.print(f"[magenta]Ignore non-EXIF meta information {k}[/magenta]")
                else:
                    new_v = new_datetime.strftime("%Y:%m:%d %H:%M:%S") + sec
                    changes[k] = new_v
            if not changes:
                return
            for k, new_v in changes.items():
                rich.print(
                    f"Shift {k} from [magenta]{metadata[k]}[/magenta] to [blue]{new_v}[/blue]"
                )
            #
            if confirmed or get_response(
                f"Shift dates of {os.path.basename(self.fullname)} as shown above?"
            ):
                e.set_tags([self.fullname], tags=changes)

    def set_exif(
        self: "MediaFile", values: List[str], override: bool = False, confirmed: bool = False
    ):
        # add one or more 0: if the format is not YY:DD:HH:MM
        with ExifToolHelper() as e:
            metadata = e.get_metadata(self.fullname)[0]
            changes = {}
            for k, v in values.items():
                if k in metadata and not override and not k.startswith("File:"):
                    rich.print(f"[magenta]Ignore existing {k} = {metadata[k]}[/magenta]")
                    continue
                if k == "File:FileModifyDate":
                    if confirmed or get_response(
                        f"Modify file modified date {os.path.basename(self.fullname)} to {v}?"
                    ):
                        try:
                            new_datetime = datetime.strptime(v, "%Y:%m:%d %H:%M:%S")
                            # Convert the new modification time to a timestamp
                            new_mod_time = new_datetime.timestamp()
                            # Set the new modification time
                            os.utime(self.fullname, (new_mod_time, new_mod_time))
                            rich.print(
                                f"Set File:FileModifyDate of [magenta]{self.filename}[/magenta] to [blue]{v}[/blue]"
                            )
                        except ValueError:
                            rich.print(f"[red]Invalid date format {v}[/red]")
                elif k.startswith("File:"):
                    rich.print(f"[magenta]Ignore non-EXIF meta information {k}[/magenta]")
                else:
                    rich.print(f"Set {k} of {self.filename} to [blue]{v}[/blue]")
                    changes[k] = v
            if not changes:
                return
            if confirmed or get_response(f"Set exif of {self.fullname}"):
                rich.print(f"EXIF data of [blue]{self.filename}[/blue] is updated.")
                e.set_tags([self.fullname], tags=changes)

    def name_ok(self: "MediaFile"):
        return re.match(r"2\d{7}(_.*)?" + self.ext.lower(), self.filename)

    def path_ok(self: "MediaFile", root: str, subdir: str = ""):
        intended_path = self.intended_path(root, subdir)
        # return self.fullname == os.path.join(intended_path, self.filename)
        return self.fullname.startswith(intended_path)

    def rename(self: "MediaFile", format: str = "%Y%m%d_%H%M%S", confirmed: bool = False):
        # allow the name to be xxxxxx_xxxxx-someotherstuff
        if self.filename.startswith(self.intended_prefix(format=format)):
            return
        intended_name = self.intended_name(format=format)

        try:
            for i in range(10):
                if i > 0:
                    n, e = os.path.splitext(intended_name)
                    nn = f"{n}_{i}{e}"
                else:
                    nn = intended_name
                new_file = os.path.join(self.dirname, nn)
                if os.path.isfile(new_file):
                    if os.path.samefile(self.fullname, new_file):
                        return
                    if filecmp.cmp(self.fullname, new_file, shallow=False):
                        if confirmed or get_response(
                            f"Rename {self.fullname} to an existing file {new_file}"
                        ):
                            os.remove(self.fullname)
                        # switch itself to new file
                        break
                    continue
                if confirmed or get_response(f"Rename {self.fullname} to {new_file}"):
                    os.rename(self.fullname, new_file)
                break
            #
            self.fullname = new_file
            self.filename = nn
        except Exception as e:
            print(f"Failed to rename {self.fullname}: {e}")

    def move(
        self: "MediaFile",
        media_root: str = "/Volumes/Public/MyPictures",
        dir_pattern: str = "%Y/%b",
        album: str = "",
        confirmed: bool = False,
    ):
        intended_path = self.intended_path(media_root, dir_pattern, album)
        if self.fullname.startswith(intended_path):
            return
        if confirmed or get_response(f"Move {self.fullname} to {intended_path}"):
            if not os.path.isdir(intended_path):
                os.makedirs(intended_path)
            for i in range(10):
                try:
                    if i > 0:
                        n, e = os.path.splitext(self.filename)
                        nn = f"{n}_{i}{e}"
                    else:
                        nn = self.filename
                    new_file = os.path.join(intended_path, nn)
                    if os.path.isfile(new_file):
                        if filecmp.cmp(self.fullname, new_file, shallow=False):
                            os.remove(self.fullname)
                            print(f"Remove duplicated file {self.fullname}")
                            return
                        continue
                    shutil.move(self.fullname, new_file)
                except Exception as e:
                    print(f"Failed to move {self.fullname}: {e}")
                    raise
