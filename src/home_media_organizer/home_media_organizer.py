import fnmatch
import os
import threading
from queue import Queue

import rich
from exiftool import ExifToolHelper
from tqdm import tqdm

from .media_file import ExifTool, date_func


def iter_files(args):
    # if file is selected based on args.matches,, args.with_exif, args.without_exif
    def is_selected(filename):
        if args.file_types and not any(fnmatch.fnmatch(filename, x) for x in args.file_types):
            return False
        if os.path.splitext(filename)[-1] not in date_func:
            return False
        if args.with_exif or args.without_exif:
            with ExifToolHelper() as e:
                metadata = {
                    x: y for x, y in e.get_metadata(filename).items() if not x.startswith("File:")
                }
            for cond in args.without_exif or []:
                if "=" in cond:
                    k, v = cond.split("=")
                    if "*" in k:
                        raise ValueError(
                            f"Invalid condition {cond}: '*' is not allowed when key=value is specified."
                        )
                    if k in metadata and metadata[k] == v:
                        return False
                elif "*" in cond:
                    if any(fnmatch.fnmatch(x, cond) for x in metadata.keys()):
                        return False
                else:
                    if cond in metadata:
                        return False
            match = True
            for cond in args.with_exif or []:
                if "=" in cond:
                    k, v = cond.split("=")
                    if "*" in k:
                        raise ValueError(
                            f"Invalid condition {cond}: '*' is not allowed when key=value is specified."
                        )
                    if k not in metadata or metadata[k] != v:
                        match = False
                elif "*" in cond:
                    if not any(fnmatch.fnmatch(x, cond) for x in metadata.keys()):
                        match = False
                else:
                    if cond not in metadata:
                        match = False
            return match
        return True

    for item in args.items:
        if os.path.isfile(item) and is_selected(item):
            yield item
        else:
            if not os.path.isdir(item):
                rich.print(f"[red]{item} is not a filename or directory[/red]")
                continue
            for root, _, files in os.walk(item):
                for f in files:
                    if is_selected(os.path.join(root, f)):
                        yield os.path.join(root, f)


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
