"""Main module."""

import os
import hashlib

import fnmatch
import filecmp
import json
import os
import re
import sys
import shutil
import subprocess
from datetime import datetime, timedelta

from PIL import Image, UnidentifiedImageError

import rich

from .utils import get_response


class MediaFile:

    def __init__(self, filename, verbose=True):
        self.fullname = os.path.abspath(filename)
        self.dirname, self.filename = os.path.split(self.fullname)
        self.ext = os.path.splitext(self.filename)[-1]
        self.verbose = verbose
        self.date = None
        self.md5 = None

    def size(self):
        return os.path.getsize(self.fullname)

    def calculate_md5(self, md5_store):
        if self.fullname in md5_store:
            self.md5 = md5_store[self.fullname]
            # print(f"{self.md5} <<- {self.filename}")
            return self
        if self.md5 is None:
            # improve the following line to better handle large files by reading chunks of files
            md5 = hashlib.md5()
            with open(self.fullname, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024 * 1024), b""):
                    md5.update(chunk)
            self.md5 = md5.hexdigest()
            md5_store[self.fullname] = self.md5
            # print(f"{self.md5} <- {self.filename}")
        return self

    def get_date(self):
        if self.date is None:
            global date_func
            funcs = date_func[self.ext]
            for func in funcs:
                try:
                    self.date = func(self.fullname)
                    if not self.date:
                        continue
                    if not self.date.startswith("2"):
                        raise ValueError("Invalid date {}".format(self.date))
                    break
                except Exception as e:
                    if self.verbose:
                        print("{}: {}".format(self.fullname, e))
                    continue
            if not self.date:
                return "19000101_000000"
            self.date = self.date.replace(":", "").replace(" ", "_")
        return self.date

    def show_exif(self, keys=None, format=None):
        with ExifTool() as e:
            metadata = e.get_metadata(self.fullname)
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

    def intended_prefix(self, format="%Y%m%d_%H%M%S"):
        date = self.get_date()
        if not date:
            date = os.path.split(os.path.basename(self.fullname))[0]
            date = date.replace(":", "").replace(" ", "_")
        if format == "%Y%m%d_%H%M%S":
            return date
        filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
        return filedate.strftime(format)

    def intended_name(self, format="%Y%m%d_%H%M%S"):
        return self.intended_prefix(format=format) + self.ext.lower()

    def intended_path(self, root, dir_pattern, album):
        date = self.get_date()
        filedate = datetime.strptime(date[: len("XXXXXXXX_XXXXXX")], "%Y%m%d_%H%M%S")
        subdir = filedate.strftime(dir_pattern)
        return os.path.join(root, subdir, album or "")

    def shift_exif(
        self, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0, confirmed=False
    ):
        # add one or more 0: if the format is not YY:DD:HH:MM
        # Calculate the total shift in timedelta
        shift_timedelta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        with ExifTool() as e:
            metadata = e.get_metadata(self.fullname)
            changes = {}
            for k, v in metadata.items():
                if k.endswith("Date"):
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
                    if new_datetime <= datetime.now():
                        new_v = new_datetime.strftime("%Y:%m:%d %H:%M:%S") + sec
                        changes[k] = new_v
            for k, new_v in changes.items():
                rich.print(
                    f"Shift {k} from [magenta]{metadata[k]}[/magenta] to [blue]{new_v}[/blue]"
                )
            if confirmed or get_response(
                f"Shift dates of {os.path.basename(self.fullname)} as shown above?"
            ):
                e.update_metadata(self.fullname, **changes)

    def set_exif(self, values, override=False, confirmed=False):
        # add one or more 0: if the format is not YY:DD:HH:MM
        with ExifTool() as e:
            metadata = e.get_metadata(self.fullname)
            changes = {}
            for k, v in values.items():
                if k in metadata and not override:
                    print(f"Ignore existing {k} = {metadata[k]}")
                    continue
                rich.print(f"Set {k} of {self.filename} to [blue]{v}[/blue]")
                changes[k] = v
            if confirmed or get_response(f"Set exif of {self.fullname}"):
                e.update_metadata(self.fullname, **changes)

    def name_ok(self):
        return re.match(r"2\d{7}(_.*)?" + self.ext.lower(), self.filename)

    def path_ok(self, root, subdir=""):
        intended_path = self.intended_path(root, subdir)
        # return self.fullname == os.path.join(intended_path, self.filename)
        return self.fullname.startswith(intended_path)

    def rename(self, format="%Y%m%d_%H%M%S", confirmed=False):
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
                    else:
                        continue
                else:
                    if confirmed or get_response(f"Rename {self.fullname} to {new_file}"):
                        os.rename(self.fullname, new_file)
                    break
            #
            self.fullname = new_file
            self.filename = nn
        except Exception as e:
            print(f"Failed to rename {self.fullname}: {e}")

    def move(
        self,
        media_root="/Volumes/Public/MyPictures",
        dir_pattern="%Y/%b",
        album="",
        confirmed=False,
    ):
        intended_path = self.intended_path(media_root, dir_pattern, album)
        if self.fullname.startswith(intended_path):
            return
        if confirmed or get_response("Move {} to {}".format(self.fullname, intended_path)):
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
                        else:
                            continue
                    else:
                        shutil.move(self.fullname, new_file)
                        return
                except Exception as e:
                    print(f"Failed to move {self.fullname}: {e}")
                    raise


def Image_date(filename):
    try:
        i = Image.open(filename)
        date = str(i._getexif()[36867])
        i.close()
        return date
    except (UnidentifiedImageError, AttributeError):
        return None


class ExifTool(object):

    sentinel = "{ready}\n"

    def __init__(self, executable="exiftool"):
        self.executable = executable

    def __enter__(self):
        self.process = subprocess.Popen(
            [self.executable, "-stay_open", "True", "-@", "-"],
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.process.stdin.write("-stay_open\nFalse\n")
        self.process.stdin.flush()

    def execute(self, *args):
        args = args + ("-execute\n",)
        self.process.stdin.write(str.join("\n", args))
        self.process.stdin.flush()
        output = ""
        fd = self.process.stdout.fileno()
        while not output.endswith(self.sentinel):
            output += os.read(fd, 4096).decode("utf-8")
        return output[: -len(self.sentinel)]

    def get_metadata(self, *filenames):
        try:
            return json.loads(self.execute("-G", "-j", "-n", *filenames))[0]
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            return {}

    def update_metadata(self, filename, **kwargs):
        args = [
            f"-{k}={v}"
            for k, v in kwargs.items()
            if k not in ("File:FileAccessDate", "File:FileInodeChangeDate")
        ]
        # print(f"excute {args} {filename}")
        return self.execute(*args, filename)


def exiftool_date(filename):
    with ExifTool() as e:
        metadata = e.get_metadata(filename)
        if "QuickTime:MediaModifyDate" in metadata:
            return metadata["QuickTime:MediaModifyDate"]
        elif "QuickTime:MediaCreateDate" in metadata:
            return metadata["QuickTime:MediaCreateDate"]
        elif "EXIF:DateTimeOriginal" in metadata:
            return metadata["EXIF:DateTimeOriginal"]
        elif "Composite:DateTimeOriginal" in metadata:
            return metadata["Composite:DateTimeOriginal"]
        else:
            return None


def filename_date(filename):
    ext = os.path.splitext(filename)[-1]
    if re.match(r"\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}.\d{2}" + ext, os.path.basename(filename)):
        fn, ext = os.path.splitext(os.path.basename(filename))
        return fn.replace("-", "").replace(".", "")
    elif re.match(
        r"video-?\d{4}\.\d{2}\.\d{2}_\d{2}-\d{2}-\d{2}" + ext,
        os.path.basename(filename),
    ):
        fn, ext = os.path.splitext(os.path.basename(filename))
        return fn.replace("-", "").replace(".", "")[5:]
    elif re.match(r"\d{8}[_-].*" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{8})[_-](.*)" + ext, os.path.basename(filename)).groups()
        return "{:0>8}_{}".format(fld[0], fld[1])
    elif re.match(r"\d{8}" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{8})" + ext, os.path.basename(filename)).groups()
        return "{:0>8}".format(fld[0])
    elif re.match(r"IMG_\d{8}_\d{6}" + ext, os.path.basename(filename)):
        fld = re.match(r"IMG_(\d{8})_(\d{6})" + ext, os.path.basename(filename)).groups()
        return "{:0>8}_{:1}".format(fld[0], fld[1])
    elif re.match(r"IMG_\d{8}_\d{6}_\d" + ext, os.path.basename(filename)):
        fld = re.match(r"IMG_(\d{8})_(\d{6})_\d" + ext, os.path.basename(filename)).groups()
        return "{:0>8}_{:1}".format(fld[0], fld[1])
    elif re.match(r"VID_\d{8}_\d{6}" + ext, os.path.basename(filename)):
        fld = re.match(r"VID_(\d{8})_(\d{6})" + ext, os.path.basename(filename)).groups()
        return "{:0>8}_{:1}".format(fld[0], fld[1])
    elif re.match(r"PXL_\d{8}_\d{9}" + ext, os.path.basename(filename)):
        fld = re.match(r"PXL_(\d{8})_(\d{9})" + ext, os.path.basename(filename)).groups()
        return "{:0>8}_{:1}".format(fld[0], fld[1])
    elif re.match(r"video-\d{4}[\.-]\d{1,2}[\.-]\d{1,2}-.+" + ext, os.path.basename(filename)):
        fld = re.match(
            r"video-(\d{4})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
            os.path.basename(filename),
        ).groups()
        return "{:0>4}{:0>2}{:0>2}_{}".format(fld[0], fld[1], fld[2], fld[3])
    elif re.match(r"\d{2}[\.-]\d{1,2}[\.-]\d{1,2}-.+" + ext, os.path.basename(filename)):
        fld = re.match(
            r"(\d{2})[\.-](\d{1,2})[\.-](\d{1,2})-(.+)" + ext,
            os.path.basename(filename),
        ).groups()
        return "20{:0>2}{:0>2}{:0>2}_{}".format(fld[0], fld[1], fld[2], fld[3])
    elif re.match(r"\d{4}-\d{1,2}-\d{1,2}-.{1,3}" + ext, os.path.basename(filename)):
        fld = re.match(
            r"(\d{4})-(\d{1,2})-(\d{1,2})-(.{1,3})" + ext, os.path.basename(filename)
        ).groups()
        return "{:0>4}{:0>2}{:0>2}_{}".format(fld[0], fld[1], fld[2], fld[3])
    elif re.match(r"\d{2}-\d{2}-\d{2}_.+" + ext, os.path.basename(filename)):
        fld = re.match(r"(\d{2})-(\d{2})-(\d{2})_(.*)" + ext, os.path.basename(filename)).groups()
        return "20{:0>2}{:0>2}{:0>2}_{}".format(fld[0], fld[1], fld[2], fld[3])
    elif re.match(r"video-\d{4}-\d{2}-\d{2}" + ext, os.path.basename(filename)):
        fld = re.match(r"video-(\d{4})-(\d{2})-(\d{2})" + ext, os.path.basename(filename)).groups()
        return "{:0>4}{:0>2}{:0>2}".format(fld[0], fld[1], fld[2])
    elif re.match(r"voice-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}" + ext, os.path.basename(filename)):
        fld = re.match(
            r"voice-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})" + ext,
            os.path.basename(filename),
        ).groups()
        return "{:0>4}{:0>2}{:0>2}_{:0>2}{:0>2}".format(fld[0], fld[1], fld[2], fld[3], fld[4])
    # elif re.match(r'\d{4}-\d{1,2}-\d{1,2}
    else:
        raise ValueError("Cannot extract date from filename {}".format(filename))


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
