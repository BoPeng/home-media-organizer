"""Main module."""

import os
import hashlib


import filecmp
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta


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
            print(f"{self.md5} <<- {self.fullname}")
            return self
        if self.md5 is None:
            # improve the following line to better handle large files by reading chunks of files
            md5 = hashlib.md5()
            with open(self.fullname, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024 * 1024), b""):
                    md5.update(chunk)
            self.md5 = md5.hexdigest()
            md5_store[self.fullname] = self.md5
            print(f"{self.md5} <- {self.fullname}")
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
        return self.date

    def show_exif(self, keys=None):
        with ExifTool() as e:
            metadata = e.get_metadata(self.fullname)
        print(self.fullname)
        for k, v in metadata.items():
            if not keys or k in keys:
                print(f"{k}: {v}")
        print()

    def intended_prefix(self):
        date = self.get_date()
        if not date:
            date = os.path.split(os.path.basename(self.fullname))[0]
        return date.replace(":", "").replace(" ", "_")

    def intended_name(self):
        return self.intended_prefix() + self.ext.lower()

    def intended_path(self, root, subdir):
        date = self.get_date()
        date = date.replace(":", "").replace(" ", "_")
        year = date[:4]
        months = {
            "01": "Jan",
            "02": "Feb",
            "03": "Mar",
            "04": "Apr",
            "05": "May",
            "06": "Jun",
            "07": "Jul",
            "08": "Aug",
            "09": "Sep",
            "10": "Oct",
            "11": "Nov",
            "12": "Dec",
        }
        month = months[date[4:6]]
        if subdir:
            return os.path.join(root, year, month, subdir)
        else:
            if any(
                x in os.path.basename(self.dirname)
                for x in (list(months.values()) + list(months.keys()))
            ):
                source_subdir = os.path.basename(self.dirname).split("-")[-1]
                if (
                    not any(source_subdir.startswith(x) for x in months.values())
                    and not source_subdir.isdigit()
                ):
                    return os.path.join(root, year, month, source_subdir)
            elif os.path.dirname(self.dirname) in (list(months.values()) + list(months.keys())):
                return os.path.join(root, year, month, os.path.basename(self.dirname))
            return os.path.join(root, year, month)

    def shift(self, shift):
        # add one or more 0: if the format is not YY:DD:HH:MM
        shift = "0:" * (4 - shift.count(":")) + shift
        year, month, days, hours, minutes = map(int, shift.split(":"))
        # Calculate the total shift in timedelta
        shift_timedelta = timedelta(days=days, hours=hours, minutes=minutes)
        print(f"shift {self.fullname} by {days} {hours} {minutes}")
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
                    if year:
                        original_datetime = original_datetime.replace(
                            year=original_datetime.year + year
                        )
                    #
                    if month:
                        original_datetime = original_datetime.replace(
                            month=original_datetime.month + month
                        )
                    #
                    new_datetime = original_datetime + shift_timedelta
                    if new_datetime <= datetime.now():
                        new_v = new_datetime.strftime("%Y:%m:%d %H:%M:%S") + sec
                        changes[k] = new_v
            for k, new_v in changes.items():
                print(f"shift {k}\tfrom {metadata[k]}\tto {new_v}")
            if get_response(f"Shift dates of {self.fullname} as shown above"):
                e.update_metadata(self.fullname, **changes)

    def set_date(self, new_date):
        # add one or more 0: if the format is not YY:DD:HH:MM
        new_date = "0:" * (4 - new_date.count(":")) + new_date
        year, month, day, hour, minute = map(int, new_date.split(":"))
        # Calculate the total shift in timedelta
        new_date = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
        print(f"setting dates of {self.fullname} to new_date")
        with ExifTool() as e:
            metadata = e.get_metadata(self.fullname)
            changes = {}
            for date_key in (
                "QuickTime:CreateDate",
                "QuickTime:ModifyDate",
                "QuickTime:TrackCreateDate",
                "QuickTime:TrackModifyDate",
                "QuickTime:MediaCreateDate",
                "QuickTime:MediaModifyDate",
            ):
                if date_key in metadata:
                    print(f"Ignore existing {date_key} = {metadata[date_key]}")
                    continue
                changes[k] = new_date.strftime("%Y:%m:%d %H:%M:%S")
            for k, new_v in changes.items():
                print(f"Add {k}\twith value {new_v}")
            if get_response(f"Set dates of {self.fullname} as shown above"):
                e.update_metadata(self.fullname, **changes)

    def name_ok(self):
        return re.match(r"2\d{7}(_.*)?" + self.ext.lower(), self.filename)

    def path_ok(self, root, subdir=""):
        intended_path = self.intended_path(root, subdir)
        # return self.fullname == os.path.join(intended_path, self.filename)
        return self.fullname.startswith(intended_path)

    def rename(self):
        # allow the name to be xxxxxx_xxxxx-someotherstuff
        if self.filename.startswith(self.intended_prefix()):
            return
        intended_name = self.intended_name()

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
                        print(f"Rename {self.fullname} to an existing file {new_file}")
                        os.remove(self.fullname)
                        # switch itself to new file
                        break
                    else:
                        continue
                else:
                    print(f"Rename {self.fullname} to {new_file}")
                    os.rename(self.fullname, new_file)
                    break
            #
            self.fullname = new_file
            self.filename = nn
        except Exception as e:
            print(f"Failed to rename {self.fullname}: {e}")

    def move(self, root="/Volumes/Public/MyPictures", subdir=""):
        intended_path = self.intended_path(root, subdir)
        if get_response("Move {} to {}".format(self.fullname, intended_path)):
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
                    if i > 0:
                        print(f"{self.fullname} moved to {os.path.join(intended_path, nn)}")
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
        return json.loads(self.execute("-G", "-j", "-n", *filenames))[0]

    def update_metadata(self, filename, **kwargs):
        args = [
            f"-{k}={v}"
            for k, v in kwargs.items()
            if k not in ("File:FileAccessDate", "File:FileInodeChangeDate")
        ]
        print(f"excute {args} {filename}")
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


def iter_files(args):
    # if file is selected based on args.matches,, args.with_exif, args.without_exif
    def is_selected(filename):
        global date_func
        if args.file_types and not any(filename.endswith(x) for x in args.file_types):
            return False
        if os.path.splitext(filename)[-1] not in date_func:
            return False
        if args.with_exif or args.without_exif:
            with ExifTool() as e:
                metadata = e.get_metadata(filename)
            for cond in args.without_exif or []:
                k, v = cond.split("=")
                if k in metadata and metadata[k] == v:
                    return False
            match = True
            for cond in args.with_exif or []:
                k, v = cond.split("=")
                if k not in metadata or metadata[k] != v:
                    match = False
            return match
        return True

    for item in args.dirs:
        if os.path.isfile(item) and is_selected(item):
            yield item
        else:
            if not os.path.isdir(item):
                raise RuntimeError(f"{item} is not a filename or directory")
            for root, dirs, files in os.walk(item):
                for f in files:
                    if is_selected(f):
                        yield os.path.join(root, f)
