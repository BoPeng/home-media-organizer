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

Table of Contents:

- [Installation](#installation)
- [How to use this tool](#how-to-use-this-tool)
  - [Assumptions](#assumptions)
  - [Configuration file](#configuration-file)
  - [`hmo-list`: List all or selected media files](#hmo-list-list-all-or-selected-media-files)
  - [`hmo show-exif`: Show EXIF information of one of more files](#hmo-show-exif-show-exif-information-of-one-of-more-files)
  - [`hmo set-exif`: Set exif metadata to media files](#hmo-set-exif-set-exif-metadata-to-media-files)
  - [`hmo shift-exif`: Shift all dates by certain dates](#hmo-shift-exif-shift-all-dates-by-certain-dates)
  - [`hmo validate`: Identify corrupted JPEG files](#hmo-validate-identify-corrupted-jpeg-files)
  - [`hmo dedup` Remove duplicated files](#hmo-dedup-remove-duplicated-files)
  - [`hmo compare` Compare two sets of files](#hmo-compare-compare-two-sets-of-files)
  - [`hmo rename`: Standardize filenames](#hmo-rename-standardize-filenames)
  - [`hmo organize`: Organize media files](#hmo-organize-organize-media-files)
  - [`hmo cleanup`: Clean up library](#hmo-cleanup-clean-up-library)
- [How to get help](#how-to-get-help)
- [Special Notes](#special-notes)
  - [Modifying `File:FileModifyDate`](#modifying-filefilemodifydate)
- [More examples](#more-examples)
  - [Scenario one: video files with correct filename but missing EXIF metadata](#scenario-one-video-files-with-correct-filename-but-missing-exif-metadata)
- [TODO](#todo)
- [Credits](#credits)

## Installation

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

### Assumptions

HMO dose not assume any particular way for you to organize your media files. Its operation is however largely based on date and time of the photos and videos. It goes great a long way to determine datetime information from EXIF information, and from filenames if no EXIF is unavailable. It then provides rules for you to rename and organize the file, according to patterns based on datetime.

The pattern for file and directory names are based on [Python datetime module](https://docs.python.org/3/library/datetime.html). For example,

- A directory structure specified by `hmo organize --dir-pattern=%Y/%b` tries to organize albums by `YEAR/MONTH-ALBUM/` like `2020/Jan`, `2020/Feb`, `2020/Feb-vacation` etc.

- A directory structure specified by `hmo organize --dir-pattern=%Y/%Y-%m` tries to organize albums by `YEAR/YEAR-MONTH-ALBUM/` such as `2020/2020-01`, `2020/2020-02` etc. This structure has the advantage that all "albums" have unique names.

- With option `--album-sep=/` the albums can be put under the `dir-pattern` to create directory structure such as `2020/2020-02/Vacation`.

- With option `hmo rename --format %Y%m%d_%H%M%S` will rename files to format such as `20200312_100203.jpg`. This is the format for many phones and cameras.

### Configuration file

Although all parameters can be specified via command line, it is a good practice to list values of some parameters in configuration files so that you do not have to specify them each time.

HMO recognizes

- `~/.home-media-organizer/config.toml`
- `./.home-media-organizer.toml`
- And any configuration file specified with option `--config`

The format of the configuration is [TOML](https://toml.io/en/), and a typical configuration file looks like:

```toml
[default]
search-paths = ['/Volumes/NAS/incoming']
media-root = '/Volumes/NAS/MyPictures'

[rename]
format = '%Y%m%d_%H%M%S'

[organize]
dir-pattern = '%Y/%Y-%m'
album-sep = '-'

[cleanup]
file_types = [
    "*.MOI",
    "*.PGI",
    ".LRC",
    "*.THM",
    "Default.PLS",
    ".picasa*.ini",
    "Thumbs.db",
    "*.ini",
    "*.bat",
    "autprint*"
  ]
```

The entries and values in this configuration file correspond to subcommand and options of `hmo`, except for `default`, which specifies parameters for all commands. You can learn more about these parameters with command like

```
hmo -h
hmo rename -h
```

**NOTE**: If you have multiple configuration files, their values will be merged.

### `hmo-list`: List all or selected media files

Assuming `2000` is the folder that you keep all your old photos and videos from year 2000,

```sh
# list all supported media files
hmo list 2000

# list multiple directories
hmo list 200? --search-paths /path/to/storage

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

Note that `--search-paths` is an option used by most `hmo` commands, which specifies a list of directories to search when you specify a file or directory that does not exist under the current working directory. It is convenient to set this option in a configuration file to directories you commonly work with.

### `hmo show-exif`: Show EXIF information of one of more files

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

### `hmo set-exif`: Set exif metadata to media files

Some media files do not come with EXIF data. Perhaps they are not generated by a camera, or the photos or videos have been modified and lost their original EXIF information. This is usually not a big deal since you can manually put them into the appropriate folder or album.

However, if you are using services such as a PLEX server that ignores directory structure to organize your files, these files might be placed outside of their location in the timeline view. It is therefore useful to add EXIF information to these files.

Say we have a list of photos, in TIFF format, that we bought from a studio, and would like to add EXIF dates to them. The files do not have any date information, so we can set them by:

```sh
hmo set-exif 2000 --file-types tiff --from-date 20190824_203205
```

This operation will set

- `EXIF:DateTimeOriginal`

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

**NOTE**: Not all exif metadata can be set and the program may exit with an error if `exiftool` fails to update.

**NOTE**: Please see the notes regarding `File:FileModifyDate` if you encounter files without proper EXIF date information and cannot be modified by exiftool.

### `hmo shift-exif`: Shift all dates by certain dates

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

### `hmo validate`: Identify corrupted JPEG files

Unfortunately, due to various reasons, media files stored on CDs, DVDs, thumb drives, and even hard drives can become corrupted. These corrupted files make it difficult to navigate and can cause trouble with programs such as PLEX.

HMO provides a tool called `validate` to identify and potentially remove corrupted `JPEG`, `MPG`, `MP4` files. Support for other files could be added later.

```sh
hmo validate 2014
```

If you would like to remove the corrupted files, likely after you have examined the output from the `validate` command, you can

```sh
hmo validate 2014 --remove --yes --file-types '*.jpg'
```

If option `--manifest` is specified, it should be a manifest file that contains filenames and their hash values. This command will calculate the hash value of the files and print a warning message if the hash value if different from the value saved in the menifest file.

**NOTE**:

- `bmo validate` caches the result of file validation so it will be pretty fast to repeat the command with `--remove --yes`. If you do not want to use the cache, for example after you restored the file from backup, you can invalidate the cache with option `--no-cache`.
- You can remove the manifest files and re-run the `hmo validate` command if the manifest file is outdated.

### `hmo dedup` Remove duplicated files

There can be multiple copies of the same file, which may be in different folders with different filenames. This command uses file content to determine if files are identical, and if so, removes extra copies.

The default behavior is to keep only the copy with the longest path name, likely in a specific album, and remove the "generic" copy.

```sh
hmo dedup 2000 --yes
```

### `hmo compare` Compare two sets of files

The `compare` action compares two sets of files and list their differences.

For example,

```sh
hmo compare files_or_folders --A-and-B folders
```

find all files that exists in both folders, and

- `--A-or-B` for files exists in either of them, essentially a superset.
- `--A-and-B` for files exists in both collections.
- `--A-only` for files exist only in A
- `--B-only` for files exist only in B

By default, the operations are performed for file content only so filenames do not matter. This can be changed by option

- `--by` which can be set to either `content` (default) or `filename`.

This option can be used to compare the working copy and backup of your library, compare photos you downloaded from cloud storages such as google photos, and check if all files have been properly organized.

Note that options such as `--file-types` applies to both list of files.

### `hmo rename`: Standardize filenames

It is not absolutely necessary, but I prefer to keep files with standardized names to make it easier to sort files.

The `rename` command extracts the date information from EXIF data, and from the original filename if EXIF information does not exist, and renames the file according to specified format.
For example, `--format %Y%m%d_%H%M%S` will format files to for example `20010422_041817.mpg`. An option `--suffix` is provided if you would like to add an suffix to the filename.

For example

```sh
hmo rename 2001/video-2001-04-22_041817.mpg --format %Y%m%d_%H%M%S`
```

will attempt to rename to file to `20010422_041817.mpg` (remove `video-`).

and

```sh
hmo rename 201010* --format %Y%m%d_%H%M%S` --suffix=-vacation
```

will generate files like `20101005_129493-vacation.jpg`.

Please refer to the [Python datetime module](https://docs.python.org/3/library/datetime.html) on the format string used here.

### `hmo organize`: Organize media files

Once you have obtained a list of files, with proper names, it makes sense to send files to their respective folder such as `2010/July`. The command

```sh
hmo organize new_files --media-root /path/to/my/Library --dir-pattern %Y/%Y-%m
```

will move all files to folders such as `/path/to/my/Library/2010/2010-10`.
If this batch of data should be put under its own album, you can add option

```sh
hmo organize new_files --dest /path/to/my/Library --dir-pattern %Y/%Y-%m --album vacation
```

The files will be put under `/path/to/my/Library/2010/2010-10-vacation`. If you prefer a structure like `2010-10/vacation`, you can set `--album-sep=/` (default to `-`).

Since these options need to be kept consistent for your media library, they are usually kept in a configuration file.

**NOTE**: `/` in `--dir-pattern %Y/%Y-%m` works under both Windows and other operating systems.

By default, the `organize` command moves the files to their destination directories. If you would rather keep the original files intact, use option `--operation copy`.

### `hmo cleanup`: Clean up library

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

- `hmo backup` and `hmo restore` to backup lirary to other (cloud) storages.
- Add a `--copy` mode to make sure that the source files will not be changed or moved during `hmo rename` or `hme organize`.
- Improve data detection from media files without EXIF information to handle more types of medias.
- Support for music and movies?

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
