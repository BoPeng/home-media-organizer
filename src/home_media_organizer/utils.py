import platform
import tempfile

import joblib
import rich
from PIL import Image, UnidentifiedImageError

try:
    import ffmpeg
except ImportError:
    ffmpeg = None

cachedir = "/tmp" if platform.system() == "Darwin" else tempfile.gettempdir()
mem = joblib.Memory(cachedir, verbose=0)


def get_response(msg, allowed=None):
    while True:
        res = input(f'{msg} (y/n{"/" if allowed else ""}{"/".join(allowed or [])})? ')
        if res == "y":
            return True
        if res == "n":
            return False
        if allowed and res in allowed:
            return res
        print("Invalid response, please try again")


@mem.cache
def jpeg_openable(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()  # verify that it is, in fact an image
            return True
        #
        # i = Image.open(item)
        # i.close()
        #
    except UnidentifiedImageError:
        return False


@mem.cache
def mpg_playable(file_path):
    if not ffmpeg:
        rich.print("[red]ffmpeg not installed, skip[/red]")
        return True
    try:
        # Try to probe the file using ffmpeg
        probe = ffmpeg.probe(file_path)

        # Check if 'streams' exist in the probe result
        if "streams" in probe:
            video_streams = [s for s in probe["streams"] if s["codec_type"] == "video"]
            if len(video_streams) > 0:
                return True
        return False
    except ffmpeg.Error:
        # print(f"Error: {e.stderr.decode('utf-8')}")
        return False
