"""Main module."""

import threading

import fnmatch
import json
import os
import threading
from collections import defaultdict
from multiprocessing import Pool
from queue import Queue

from PIL import Image, UnidentifiedImageError
from tqdm import tqdm
from .media_file import MediaFile, ExifTool, date_func


confirmed = False


def get_response(msg, allowed=None):
    global confirmed
    if confirmed:
        print(msg)
        return True
    while True:
        res = input(f'{msg} (y/n/a{"/" if allowed else ""}{"/".join(allowed or [])})? ')
        if res == "a":
            confirmed = True
            return True
        elif res == "y":
            return True
        elif res == "n":
            return False
        elif allowed and res in allowed:
            return res


def cleanup(args):
    for item in args.dirs:
        for root, dirs, files in os.walk(item):
            for f in files:
                if any(fnmatch.fnmatch(f, x) for x in args.removable_files):
                    print(f"Remove {os.path.join(root, f)}")
                    os.remove(os.path.join(root, f))
            # empty directories are always removed when traverse the directory
            if not os.listdir(root):
                try:
                    print(f"Remove empty directory {root}")
                    os.rmdir(root)
                except:
                    pass


class Worker(threading.Thread):
    def __init__(self, queue, task):
        threading.Thread.__init__(self)
        self.queue = queue
        self.task = task
        self.daemon = True

    def run(self):
        while True:
            item = self.queue.get()
            if item is None:
                break
            self.task(item)
            self.queue.task_done()


def iter_files(items, file_types=None, with_exif=None, without_exif=None, **kwargs):
    # if file is selected based on args.matches,, args.with_exif, args.without_exif
    def is_selected(filename):

        if file_types and not any(filename.endswith(x) for x in file_types):
            return False
        if os.path.splitext(filename)[-1] not in date_func:
            return False
        if with_exif or without_exif:
            with ExifTool() as e:
                metadata = e.get_metadata(filename)
            for cond in without_exif or []:
                k, v = cond.split("=")
                if k in metadata and metadata[k] == v:
                    return False
            match = True
            for cond in with_exif or []:
                k, v = cond.split("=")
                if k not in metadata or metadata[k] != v:
                    match = False
            return match
        return True

    for item in items:
        if os.path.isfile(item) and is_selected(item):
            yield item
        else:
            if not os.path.isdir(item):
                raise RuntimeError(f"{item} is not a filename or directory")
            for root, dirs, files in os.walk(item):
                for f in files:
                    if is_selected(f):
                        yield os.path.join(root, f)


def process_with_queue(args, func):
    q = Queue()
    # Create worker threads
    num_workers = args.jobs or 10
    for _ in range(num_workers):
        t = Worker(q, func)
        t.start()

    for item in tqdm(iter_files(args)):
        q.put(item)
    q.join()


def show_exif(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.show_exif(args.keys)


def rename_file(item):
    m = MediaFile(item)
    m.rename()


def rename_files(args):
    global confirmed
    if confirmed:
        process_with_queue(args, rename_file)
    else:
        for item in iter_files(args):
            print(f"Processing {item}")
            rename_file(item)


def check_jpeg(item, remove=False):
    if not any(item.endswith(x) for x in (".jpg", ".jpeg")):
        return
    try:
        i = Image.open(item)
        i.close()
    except UnidentifiedImageError:
        if remove:
            print(f"Remove {item}")
            os.remove(item)
        else:
            print(f"Corrupted {item}")
        return


def check_jpeg_files(args):
    process_with_queue(args, lambda x, remove=args.remove: check_jpeg(x, remove=remove))


def get_file_size(filename):
    return (filename, os.path.getsize(filename))


def get_file_md5(filename, md5_cache):
    return (filename, MediaFile(filename).calculate_md5(md5_cache).md5)


def remove_duplicated_files(args):
    md5_files = defaultdict(list)
    size_files = defaultdict(list)

    if os.path.isfile("md5.json"):
        md5_cache = json.load(open("md5.json"))
    else:
        md5_cache = {}

    with Pool() as pool:
        # get file size
        for filename, filesize in pool.map(get_file_size, iter_files(args)):
            size_files[filesize].append(filename)
        #
        # get md5 for files with the same size
        potential_duplicates = sum([x for x in size_files.values() if len(x) > 1], [])
        for filename, md5 in pool.starmap(
            get_file_md5,
            zip(potential_duplicates, [md5_cache] * len(potential_duplicates)),
        ):
            md5_files[md5].append(filename)

    with open("md5.json", "w") as store:
        json.dump(md5_cache, store, indent=4)

    #
    for md5, files in md5_files.items():
        if len(files) == 1:
            continue
        # print(f"Found {len(files)} files with md5 {md5}")
        # keep the one with the deepest path name
        sorted_files = sorted(files, key=len)
        for filename in sorted_files[:-1]:
            print(f"Remove {filename} that duplicates {sorted_files[-1]} ")
            os.remove(filename)


def organize_files(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.move(args.media_root, subdir=args.subdir if args.subdir else m.get_subdir())


def shift_exif_date(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.shift(args.shift)


def set_exif_date(args):
    for item in iter_files(args):
        m = MediaFile(item)
        m.set_dates(args.set_date)
