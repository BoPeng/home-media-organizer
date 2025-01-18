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
    for item in args.items:
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

    for item in args.items:
        if os.path.isfile(item) and is_selected(item):
            yield item
        else:
            if not os.path.isdir(item):
                raise RuntimeError(f"{item} is not a filename or directory")
            for root, dirs, files in os.walk(item):
                for f in files:
                    if is_selected(os.path.join(root, f)):
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
