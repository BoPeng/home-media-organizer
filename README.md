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

A versatile tool to fix, organize, and maintain your home media library.

- GitHub repo: <https://github.com/BoPeng/home-media-organizer.git>
- Documentation: <https://home-media-organizer.readthedocs.io>
- Free software: MIT

## Features

I have been using a small Python script to help organize my home media collection for the past ten years. Over time, the script has grown longer and more complicated, so I decided to modernize it, make it a proper Python module, put it on GitHub for easier maintenance, and release it on PyPI so that more people can benefit from it.

This tool can

- `list`: List media files, optionally by file types and with/without certain EXIF tags.
- `show-exif`: Show all or selected EXIF metadata of one or more files.
- `set-exif`: Set EXIF metadata of media files.
- `shift-exif`: Shift the `*Date` meta information of EXIF data by specified years, months, days, etc.
- `dedup`: Identify duplicate files and remove extra copies.
- `validate`: Locate and potentially remove corrupted JPEG files.
- `rename`: Rename files according to datetime information extracted.
- `organize`: Put files under directories such as `MyLibrary/Year/Month/Vacation`.
- `cleanup`: Clean up destination directories and remove common artifact files, such as `*.LRC` and `*.THM` files from GoPro.

## Quickstart

1. Install [exiftool](https://exiftool.org/install.html). This is the essential tool to read and write EXIF information.

2. Install **Home Media Organizer** with

   ```sh
   pip install home-media-organizer
   ```

3. (Optional) Install **ffmpeg** with

   ```sh
   conda install ffmpeg -c conda-forge
   ```

   or some other methods suitable for your environment. This tool is only used to validate if your mp4/mpg files are playable using command `hmo validate`.

## How to use this tool

### Overall assumptions

The following is just how I would like to organize my home photos and videos. This tool can support the other methods but obviously the following layout is best supported.

The following is just how I like to organize my home photos and videos. This tool can support other methods, but the following layout is best supported.

1. Files are organized by `YEAR/MONTH/ALBUM/` where:

   - `YEAR` is the four-digit year number.
   - `MONTH` is usually `Jan`, `Feb`, etc., but you can use other formats.
   - `ALBUM` is **optional**; by default, all files from the same month are in the same directory.

2. Files are named by `YYYYMMDD_HHMMSS_OTHERINFO.EXT` where

   - `YYYYNNDD` is year, month, day
   - `HHMMSS` is hour, minute, second
   - `OTHERINFO` is optional so most files should looks like `YYYYMMDD_HHMMSS.EXT`.

   This is the filename format used by many cameras and camcorders, which allows you to use files dumped from cameras
   without having to rename them. and usually matches. You can optionally add some other information to the filename.

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
# This tends to be slow since it will need to scan the EXIF data of all files
hmo list 2009 --with-exif QuickTime:AudioFormat=mp4a
# with any key
hmo list 2009 --with-exif QuickTime:AudioFormat
# without any Date related EXIF meta data (external File: date is not considered)
hmo list 2009 --without-exif '*Date'
```

### Show EXIF information of one of more files

```sh
# output in colored JSON format
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4

# output selected keys
hmo show-exif 2009/Dec/Denver/20091224_192936.mp4 --keys QuickTime:VideoCodec

# output in plain text format for easier post processing, for example,
# piping to hmo set-exif to set meta data to other files
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

Some media files do not come with EXIF data. Perhaps they are not generated by a camera, or the photos or videos have been modified and lost their original EXIF information. This is usually not a big deal since you can manually put them into the appropriate folder or album.

However, if you are using services such as a PLEX server that ignores directory structure to organize your files, these files might be placed outside of their location in the timeline view. It is therefore useful to add EXIF information to these files.

Say we have a list of photos, in TIFF format, that we bought from a studio, and would like to add EXIF dates to them. The files do not have any date information, so we can set them by:

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

where at least the first one appears to be [what PLEX server uses](https://exiftool.org/forum/index.php?topic=13287.0).

Another way to get the date is to obtain it from the filename. In this case, a pattern used by [datetime.strptime](https://docs.python.org/3/library/datetime.html) needs to be specified to extract date information from filename. For example, if the filename is `video-2000-07-29 10:32:05-party.mp4`, you can use

```
# note that the filename pattern is only needed for the starting date part.
hmo set-exif path/to/video-200-07-29 10:32:05.mp4 --from-filename 'video-%Y-%m-%d %H:%M:%S'
```

You can also specify meta information as a list of `KEY=VALUE` pairs directly, as in

```sh
hmo set-exif path/to/video-200-07-29 10:32:05.mp4 \
    --values 'QuickTime:MediaCreateDate=2000-07-29 10:32:05' \
             'QuickTime:MediaModifyDate=2000-07-29 10:32:05'
```

However, if you have meta information from another file, you can read the meta information from a pipe, as in:

```sh
hmo show-exif path/to/anotherfile --keys '*Date' --format text \
  | hmo set-exif path/to/video-200-07-29 10:32:05.mp4 --values -
```

Here we allow `hom set-exif` to read key=value pairs from standard input

**NOTE**: Writing exif to some file types (e.g. `*.mpg`) are not supported, so the operation of changing filenames may fail on some media files.

**NOTE**: Please see the notes regarding `File:FileModifyDate` if you encounter files without proper EXIF date information and cannot be modified by exiftool.

### Shift all dates by certain dates

Old pictures often have incorrect EXIF dates because you forgot to set the correct dates on your camera. The date-related EXIF information is there but could be years off from the actual date. To fix this, you can use the EXIF tool to correct it.

The first step is to check the original EXIF data:

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

Since there are multiple dates, it is better to shift the dates instead of setting them with command `hmo set-exif`. If the event actually happened in July 2020, you can shift the dates by:

```sh
hmo shift-exif 2020/Jul/20240422_023929.mp4 --years=-4 --months 3 --hours=7 --minutes=10
```

```
Shift File:FileModifyDate from 2024:04:21 21:39:34-05:00 to 2020:07:22 04:49:34-05:00
Shift File:FileAccessDate from 2024:04:21 21:39:34-05:00 to 2020:07:22 04:49:34-05:00
Shift File:FileInodeChangeDate from 2024:04:21 21:39:34-05:00 to 2020:07:22 04:49:34-05:00
Shift QuickTime:CreateDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift QuickTime:ModifyDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift QuickTime:TrackCreateDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift QuickTime:TrackModifyDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift QuickTime:MediaCreateDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift QuickTime:MediaModifyDate from 2024:04:22 02:39:29 to 2020:07:22 09:49:29
Shift dates of 20240422_023929.mp4 as shown above? (y/n/)? y
```

You can confirm the change by

```
hmo show-exif 2020/Jul/20240422_023929.mp4 --keys '*Date'
{
  "File:FileModifyDate": "2020:07:22 04:49:34-05:00",
  "File:FileAccessDate": "2020:07:22 04:49:34-05:00",
  "File:FileInodeChangeDate": "2020:07:22 04:49:34-05:00",
  "QuickTime:CreateDate": "2020:07:22 09:49:29",
  "QuickTime:ModifyDate": "2020:07:22 09:49:29",
  "QuickTime:TrackCreateDate": "2020:07:22 09:49:29",
  "QuickTime:TrackModifyDate": "2020:07:22 09:49:29",
  "QuickTime:MediaCreateDate": "2020:07:22 09:49:29",
  "QuickTime:MediaModifyDate": "2020:07:22 09:49:29"
}
```

### Identify corrupted JPEG files

Unfortunately, due to various reasons, media files stored on CDs, DVDs, thumb drives, and even hard drives can become corrupted. These corrupted files make it difficult to navigate and can cause trouble with programs such as PLEX.

HMO provides a tool called `validate` to identify and potentially remove corrupted `JPEG`, `MPG`, `MP4` files. Support for other files could be added later.

```sh
hmo validate 2014
```

If you would like to remove the corrupted files, likely after you have examined the output from the `validate` command, you can

```sh
hmo validate 2014 --remove --yes --file-types '*.jpg'
```

**NOTE**: `bmo validate` caches the result of file validation so it will be pretty fast to repeat the command with `--remove --yes`. If you do not want to use the cache, for example after you restored the file from backup, you can invalidate the cache with option `--no-cache`.

### Remove duplicated files

There can be multiple copies of the same file, which may be in different folders with different filenames. This command uses file content to determine if files are identical, and if so, removes extra copies.

The default behavior is to keep only the copy with the longest path name, likely in a specific album, and remove the "generic" copy.

```sh
hmo dedup 2000 --yes
```

## Standardize filenames

It is not absolutely necessary, but I prefer to keep files with standardized names to make it easier to sort files. The default filename in HMO is `%Y%m%d_%H%M%S.ext` , which has the format of `20000729_123929.mp4`.

The `rename` command extracts the date information from EXIF data, and from the original filename if EXIF information does not exist, and renames the file to the standardized format.

Because `%Y%m%d_%H%H%Sxxxxxx.ext` is also acceptable, it does not attempt to rename a file if the first part of the filename contains the correct date information.

For example

```sh
hmo rename 2001/Apr/22BealVillage/video-2001-04-22_041817.mpg
```

will attempt to rename to file to `20010422_041817.mpg` (remove `video-`).

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

will move all files to folders such as `/path/to/my/Library/2010/Jul`.
If this batch of data should be put under its own album, you can add option

```sh
hmo organize new_files --dest /path/to/my/Library --album vacation
```

The files will be put under `/path/to/my/Library/2010/Jul/vacation`. If you prefer another type of folder structure, you can use option such as
`--dir-pattern '%Y-%m'` for command `hmo organize`.

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

## How to get help

The help message is the authoritative source of information regarding Home Media Organizer

```sh
hmo --help
hmo rename -h
```

If you notice any bug, or have any request for new features, please submit a ticket or a PR through the GitHub ticket tracker.

## Special Notes

### Modifying `File:FileModifyDate`

For files that do not have date related EXIF information, PLEX server will use file modify date to organize them. When you check the EXIF information of a file using `hmo`, this information is shown as metadata `File:FileModifyDate`, and you can use the same `hmo shift-exif` and `hmo set-exif` interface to modify this information.

For example, if you a video about your wedding that happened last year does not come with any EXIF information,

```sh
> hmo show-exif wedding.mpg --keys '*Date'
```

```json
{
  "File:FileModifyDate": "2020:01:18 10:13:33-06:00",
  "File:FileAccessDate": "2020:01:18 10:13:33-06:00",
  "File:FileInodeChangeDate": "2025:01:19 10:48:00-06:00"
}
```

You can set the modified date as follows:

```sh
> hmo shift-exif wedding.mpg --keys File:FileModifyDate --year=-1 --month 3
> hmo show-exif wedding.mpg --keys '*Date'
```

```json
{
  "File:FileModifyDate": "2019:04:18 10:13:33-05:00",
  "File:FileAccessDate": "2019:04:18 10:13:33-05:00",
  "File:FileInodeChangeDate": "2025:01:19 10:50:23-06:00"
}
```

However, file modify date is **NOT** part of the file content. If you copy the file to another location, the new file will have a new modified date and you may need to run the `hmo set-exif --from-filename` again.

## More examples

### Scenario one: video files with correct filename but missing EXIF metadata

```sh
# use --without-exif to find all media file without `Date` metadata

hmo list 2003 --without-exif '*Date'

# use hmo to show filename and modified date, and see if they match
hmo show-exif 2003 --without-exif '*Date' --keys File:FileName File:FileModifyDate --format text

# use set-exif --from-filename to modify FileModifyDate
hmo set-exif 2003 --without-exif '*Date' --from-filename '%Y%m%d_%H%M%S' --keys File:FileModifyDate -y
```

## TODO

- Add tests
- Improve data detection from media files to handle more types of medias.
- Add a `--copy` mode to make sure that the source files will not be changed or moved during `hmo rename` or `hme organize`.
- Support for music and movies?

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
