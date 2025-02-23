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

- [Features](#features)
- [Installation](#installation)
- [How to use this tool](#how-to-use-this-tool)
  - [Assumptions](#assumptions)
  - [Configuration file](#configuration-file)
- [Detailed Usages](#detailed-usages)
  - [`hmo-list`: List all or selected media files](#hmo-list-list-all-or-selected-media-files)
  - [`hmo show-tags`: Show tags assciated with media files](#hmo-show-tags-show-tags-assciated-with-media-files)
  - [`hmo set-tags`: Set tags to media files](#hmo-set-tags-set-tags-to-media-files)
  - [`hmo unset-tags`: Remove specified tags from media files](#hmo-unset-tags-remove-specified-tags-from-media-files)
  - [`hmo classify`: Classify media files with a machine learning model](#hmo-classify-classify-media-files-with-a-machine-learning-model)
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
- [Advanced Topics](#advanced-topics)
  - [Modifying `File:FileModifyDate`](#modifying-filefilemodifydate)
  - [Filtering by tags](#filtering-by-tags)
- [TODO](#todo)
- [Credits](#credits)

## Features

- **Smart Organization**: Automatically organize photos and videos by date from EXIF data
- **Duplicate Detection**: Find and remove duplicate media files
- **Tag Management**: Add, remove, and search media files by custom tags
- **AI-Powered Classification**:
  - Face detection and recognition, tag photos with names
  - Age and gender detection
  - Content classification (NSFW detection)
- **EXIF Management**: View, set, and modify EXIF metadata
- **File Validation**: Detect corrupted media files
- **Flexible Configuration**: Customizable organization patterns and rules

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
manifest = '/Volumes/NAS/MyPictures/manifest.db'

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


## How to get help

The help message is the authoritative source of information regarding Home Media Organizer

```sh
hmo --help
hmo rename -h
```

If you notice any bug, or have any request for new features, please submit a ticket or a PR through the GitHub ticket tracker.

## Advanced Topics

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

### Filtering by tags

Options `--with-tags` and `--without-tags` can be used to select media files for all operations if operations `hmo set-tags` and `hmo classify` has been used to set various tags to media files.

You can use command

```sh
hmo show-tags 2009
```

to show all files with any tags, or use

```sh
hmo list 2009 --with-tags happy
```

to see all pictures with a happy face (classified by `hmo classify --model emotion`).

By default

```sh
hmo list 2009 --with-tags  baby happy
```

will show all media files with either a `baby` or a `happy` tag, but you can narrow down the search by photos with happy babies as well

```sh
hmo list 2009 --with-tags  'baby AND happy'
```

Conditions such as `baby AND (happy OR sad)` if allowed, and you will need to quote tags if the tags contains special characters.

## TODO

- `hmo backup` and `hmo restore` to backup lirary to other (cloud) storages.
- Add a `--copy` mode to make sure that the source files will not be changed or moved during `hmo rename` or `hme organize`.
- Improve data detection from media files without EXIF information to handle more types of medias.
- Support for music and movies?

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
