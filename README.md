# Home Media Organizer

<div align="center">

[![PyPI - Version](https://img.shields.io/pypi/v/home-media-organizer.svg)](https://pypi.python.org/pypi/home-media-organizer)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/home-media-organizer.svg)](https://pypi.python.org/pypi/home-media-organizer)
[![Tests](https://github.com/BoPeng/home-media-organizer/workflows/tests/badge.svg)](https://github.com/BoPeng/home-media-organizer/actions?workflow=tests)
[![Codecov](https://codecov.io/gh/BoPeng/home-media-organizer/branch/main/graph/badge.svg)](https://codecov.io/gh/BoPeng/home-media-organizer)
[![Read the Docs](https://readthedocs.org/projects/home-media-organizer/badge/)](https://home-media-organizer.readthedocs.io/)
[![PyPI - License](https://img.shields.io/pypi/l/home-media-organizer.svg)](https://pypi.python.org/pypi/home-media-organizer)

[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](https://www.contributor-covenant.org/version/2/1/code_of_conduct/)

</div>

An Swiss Army Knife kind of tool to help fix, organize, and maitain your home media library

- GitHub repo: <https://github.com/BoPeng/home-media-organizer.git>
- Documentation: <https://home-media-organizer.readthedocs.io>
- Free software: MIT

## Features

I have been using a little Python script to help organize my home media collection in the
past ten years. Over the years the script has grown longer and more complicated and I finally decided to modernize the script, make it a proper Python module, put on github
to make it easy to maintain, and release it on PyPI so that more people can benefit from
it.

This tool can

- `hmo list`: List media files, optionally by file types and w/wo certain exif tags.
- `hmo`:

## Quickstart

TODO

## How to use this tool

### Overall assumptions

The following is just how I would like to organize my home photos and videos. This tool can support the other methods but obviously the following layout is best supported.

1. Files are organized by `YEAR/MONTH/ALBUM/YYYYMMDD_MMSSSS_OTHERINFO.EXT` where

- `YEAR` is the four digit year number
- `MONTH` is usually `Jan`, `Feb` etc, but you can use other formats
- `ALBUM` is **optional**, by default all files from the same month are in the same directory.
- `YYYYMMDD_MMSSSS.EXT` is the default filename, which is used by many camera and camcorders, and usually matches

### List all or selected media files

Assuming `2000` is the folder that you keep all your old photos and videos from year 2000,

```sh
# list all supported media files
hmo list 2000

# list multiple directories
hmo list 200?

# list only certain file types
hmo list 2000 --file-types mp4

# list only files with certain exif value.
# This tends to be slow since it will need to scan the
# exif of all files.
hmo list 2009 --with-exif QuickTime:AudioFormat=mp4a
```

### Show EXIF information of one of more files

```sh
# output in colored JSON format
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4

# output selected keys
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4 --keys QuickTime:VideoCodec

# output in plain text format for easier post processing
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4 --keys QuickTime:VideoCodec --format text

# wildcard is supported
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4 --keys '*Date'
```

The last command can have output like

```json
{
  "File:FileModifyDate": "2009:12:24 19:29:36-06:00",
  "File:FileAccessDate": "2009:12:24 19:29:36-06:00",
  "File:FileInodeChangeDate": "2009:12:24 19:29:36-06:00",
  "QuickTime:CreateDate": "2009:12:24 19:29:33",
  "QuickTime:ModifyDate": "2009:12:24 19:29:36",
  "QuickTime:TrackCreateDate": "2009:12:24 19:29:33",
  "QuickTime:TrackModifyDate": "2009:12:24 19:29:36",
  "QuickTime:MediaCreateDate": "2009:12:24 19:29:33",
  "QuickTime:MediaModifyDate": "2009:12:24 19:29:36"
}
```

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
