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

- `list`: List media files, optionally by file types and w/wo certain exif tags.
- `dedup`: Identify duplicated files and remove extra copies.
- `check-jpeg`: Locate and potentially remove corrupted JPEG files.
- `show-exif`: Show all or selected exif metadata of one or more files.
- `shift-exif`: Shift the `*Date` meta information of exif of media files by specified year, month, day, etc.
- `set-exif`: Set exif metadata of media files.
- `rename`: rename files according to datetime information extracted.
- `organize`: Put files under directories such as `MyLibrary/Year/Month/Vacation`.
- `cleanup`: Clean up the destination directories and remove common artifact files, such as `*.LRC` and `*.THM` files from GoPro.

## Quickstart

1. Install [exiftool](https://exiftool.org/install.html). This is the essential tool to read and write exif information.

2. Install home media organizer with

```
pip install home-media-organizer
```

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
hmo list 2000 --file-types '*.mp4'

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

### Set exif metadata to media files

Some media files do not come with exif data. Perhaps they are not generated by a camera, or the photos or videos have been modified and lost their original exif information. This is usually not a big deal since you can manually put them into appropriate folder or album.

However, if you are using services such as a PLEX server that ignores directory structure to organize your files, these files might be placed out side of their location in the timeline view. It is therefore useful to add exif information to these files.

Say we have a list of photos, in tiff format, that we bought from a studio, and would like to add EXIF dates to them. The files do not have any date information
so we can set them by

```sh
hmo set-exif 2000 --file-types tiff --from-date 20190824_203205
```

This operation will set

- `EXIF:DateTimeOriginal`
- `QuickTime:CreateDate`
- `QuickTime:ModifyDate`
- `QuickTime:TrackCreateDate`
- `QuickTime:TrackModifyDate`
- `QuickTime:MediaCreateDate`
- `QuickTime:MediaModifyDate`

where at least the first one [appears to be what PLEX server uses](https://exiftool.org/forum/index.php?topic=13287.0).

Another way to get date is to obtaining them from filename. In this case
a pattern used by [datetime.strptime](https://docs.python.org/3/library/datetime.html) needs to be specified to extract date information from filename (excluding extension). For example, if the filename is `video-2000-07-29 10:32:05.mp4`, you can use

```
hmo set-exif path/to/video-200-07-29 10:32:05.mp4 --from-filename 'video-%Y-%m-%d %H:%M:%S'
```

Finally, you can specify meta information as a list of `KEY=VALUE` pairs directly, as in

```sh
hmo set-exif path/to/video-200-07-29 10:32:05.mp4 \
    --values 'QuickTime:MediaCreateDate=2000-07-29 10:32:05' \
             'QuickTime:MediaModifyDate=2000-07-29 10:32:05'
```

However, if you have metain formation from another file, you can read the meta information from a pipe, as in

```sh
hmo show-exif path/to/anotherfile --keys '*Date' --format text \
  | hmo set-exif path/to/video-200-07-29 10:32:05.mp4 --values -
```

Here we allow `hom set-exif` to read key=value pairs from standard input

### Shift all dates by certain dates

Old pictures often have wrong exif dates because you forgot to
set the correct dates for your camera. The date related exif information are there, but could be years before the actual date. To fix this, you can use the exif tool to correct it.

The first step is of course to check the original exif

```sh
 hmo show-exif 2024/Apr/20240422_023929.mp4
```

```json
{
  "File:FileModifyDate": "2024:04:21 21:39:34-05:00",
  "File:FileAccessDate": "2024:04:21 21:39:34-05:00",
  "File:FileInodeChangeDate": "2024:04:21 21:39:34-05:00",
  "QuickTime:CreateDate": "2024:04:22 02:39:29",
  "QuickTime:ModifyDate": "2024:04:22 02:39:29",
  "QuickTime:TrackCreateDate": "2024:04:22 02:39:29",
  "QuickTime:TrackModifyDate": "2024:04:22 02:39:29",
  "QuickTime:MediaCreateDate": "2024:04:22 02:39:29",
  "QuickTime:MediaModifyDate": "2024:04:22 02:39:29"
}
```

Because there are multiple dates, it is better to shift the dates instead of
setting them. Since the event actually happened on July, 2000, so let us shift
by

```sh
hmo shift-exif 2000/Jul/20240422_023929.mp4 --years=-24 --months 3 --hours=7 --minutes=10
```

```
Shift File:FileModifyDate from 2024:04:21 21:39:34-05:00 to 2000:07:22 04:49:34-05:00
Shift File:FileAccessDate from 2024:04:21 21:39:34-05:00 to 2000:07:22 04:49:34-05:00
Shift File:FileInodeChangeDate from 2024:04:21 21:39:34-05:00 to 2000:07:22 04:49:34-05:00
Shift QuickTime:CreateDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift QuickTime:ModifyDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift QuickTime:TrackCreateDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift QuickTime:TrackModifyDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift QuickTime:MediaCreateDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift QuickTime:MediaModifyDate from 2024:04:22 02:39:29 to 2000:07:22 09:49:29
Shift dates of 20240422_023929.mp4 as shown above? (y/n/)? y
excute ['-File:FileModifyDate=2000:07:22 04:49:34-05:00', '-QuickTime:CreateDate=2000:07:22 09:49:29', '-QuickTime:ModifyDate=2000:07:22 09:49:29', '-QuickTime:TrackCreateDate=2000:07:22 09:49:29', '-QuickTime:TrackModifyDate=2000:07:22 09:49:29', '-QuickTime:MediaCreateDate=2000:07:22 09:49:29', '-QuickTime:MediaModifyDate=2000:07:22 09:49:29'] /Volumes/Public/MyPictures/2000/Jul/20240422_023929.mp4
```

You can confirm the change by

```
hmo show-exif 2000/Jul/20240422_023929.mp4 --keys '*Date'
{
  "File:FileModifyDate": "2000:07:22 04:49:34-05:00",
  "File:FileAccessDate": "2000:07:22 04:49:34-05:00",
  "File:FileInodeChangeDate": "2000:07:22 04:49:34-05:00",
  "QuickTime:CreateDate": "2000:07:22 09:49:29",
  "QuickTime:ModifyDate": "2000:07:22 09:49:29",
  "QuickTime:TrackCreateDate": "2000:07:22 09:49:29",
  "QuickTime:TrackModifyDate": "2000:07:22 09:49:29",
  "QuickTime:MediaCreateDate": "2000:07:22 09:49:29",
  "QuickTime:MediaModifyDate": "2000:07:22 09:49:29"
}
```

### Identify corrupted JPEG files

Unfortunately, due to various reasons, media files stored on CD, DVD, thumbdrives, even harddrives can become corrupted. These corrupted files make it difficult to navigate, and can cause trouble with programs such as PLEX.

hmo provides a tool called `check-jpeg` to identify and potentially remove corrupted jpeg files.

```sh
hmo check-jpeg 2014
```

If you would like to remove the corrupted files, likely after you have examined the output from the `check-jpeg` command, you can

```sh
hmo check-jpeg 2014 --remove --yes
```

### Remove duplicated files

There can be multiple copies of the same file, which makes can be in different folders with different filenames. This command use file content to determine if files are identical, and if so, remove extra copies.

The default behavior is to keep only the copy with the longest path name, likely in a specific album, and remove the "generic" copy.

```sh
hmo dedup 2000 --yes
```

## Standardize filenames

It is not absolutely necessary but I would love to keep files in standardize names. The default filename in HMO is `%Y%m%d_%H%M%S.ext` , which has the format of `20000729_123929.mp4`.

The `rename` command extract the date information from exif, and from origin filename if exif information does not exist, and rename the file to the standardard format.

Because `%Y%m%d_%H%H%Sxxxxxx.ext` is also acceptable, it does not attempt to rename a file if the first part of the filename contains the correct date information.

For example

```sh
hmo rename 2001/Apr/22BealVillage/video-2001-04-22_041817.mpg
```

will attempt to rename to file to `20010422_041817.mpg`.

If you prefer another format, you can use the `--format` option

```sh
hmo rename 2001/Apr/22BealVillage/video-2001-04-22_041817.mpg --format '%Y-%m-%d_%H%M-vacation'
```

Please refer to the [Python datetime module](https://docs.python.org/3/library/datetime.html) on the format string used here.

## Organize media files

Once you have obtained a list of files, with proper names, it makes sense to send files to their respective folder such as `2010/July`. The command

```sh
hmo organize new_files --dest /path/to/my/Library
```

will move all files to folders such as `/path/to/my/Library/2010/July`.
If this batch of data should be put under its own album, you can add option

```sh
hmo organize new_files --dest /path/to/my/Library --album vacation
```

The files will be put under `/path/to/my/Library/2010/July/vacation`

### Clean up library

Finally, command

```sh
hmo cleanup -y
```

will remove files that are commonly copied from cameras, such as `*.LRV` and `*.THM` files from GoPro cameras. It will also remove any empty directories. You can control the file types to be removed by adding options such as `*.CR2` (single quote is needed to avoid shell expansion), namely

```sh
hmo cleanup '*.CR2'
```

To check the file types that will be removed, run

```
hmo cleanup -h
```

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
