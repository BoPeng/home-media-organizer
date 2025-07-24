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

- **Smart Organization**: Automatically organize photos and videos by date from EXIF data
- **Duplicate Detection**: Find and remove duplicate media files
- **Efficient File Search**: Database-backed pattern matching for fast file discovery across large collections
- **Safe File Removal**: Remove files with recycle bin protection and permanent deletion options
- **Tag Management**: Add, remove, and search media files by custom tags
- **AI-Powered Classification**:
  - Face detection and recognition, tagging photos with names
  - Age, gender, emotion detection
  - Content classification (NSFW detection)
- **EXIF Management**: View, set, and modify EXIF metadata
- **File Validation**: Detect corrupted media files
- **Flexible Configuration**: Customizable organization patterns and rules

At its simplest, the command

```sh
hmo organize mypictures -y
```

moves media files from the mypictures directory into folders like 2025-03, based on predefined naming rules, a specified target location, and timestamp of media files.

Table of Contents:

- [Quick Start](#quick-start)
- [Basic Usages](#basic-usages)
  - [List and count all photos](#list-and-count-all-photos)
  - [Rename files according to their date and time](#rename-files-according-to-their-date-and-time)
  - [Organize files](#organize-files)
  - [Remove duplicated files](#remove-duplicated-files)
- [Advanced Topics](#advanced-topics)
  - [Do you have a happy family?](#do-you-have-a-happy-family)
  - [Find all photos with you](#find-all-photos-with-you)
  - [Compare against a separate collection of files](#compare-against-a-separate-collection-of-files)
  - [Modifying `File:FileModifyDate`](#modifying-filefilemodifydate)
- [TODO](#todo)
- [Credits](#credits)

## Quick Start

1. Install **Home Media Organizer** with

   ```sh
   pip install home-media-organizer
   ```

2. (Optional) Install [exiftool](https://exiftool.org/install.html) for EXIF related operations.

3. (Optional) Install **ffmpeg** with

   ```sh
   conda install ffmpeg -c conda-forge
   ```

   or some other methods suitable for your environment. This tool is only used to validate if your mp4/mpg files are playable using command `hmo validate`.

4. (Optional) Create a configuration file `~/.home-media-organizer/config.toml` that reflect the configuration of your home media library. These options define default parameters for the `hmo` commands. Adding them to a configuration file greatly simplifies the use of `hmo`.

```toml
[default]
search-paths = ['/Volumes/NAS/incoming', '/Volumes/NAS/MyPictures']
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

See [Configuration file](docs/README.md#configuration-file) for details.

5. Start using **Home Media Organizer**

```sh
hmo -h
```

For details usages of each command, please visit [Home Media Organizer Documentation](docs/README.md).

## Common Options

**Home Media Organizer** provides several common options that work across all commands:

### File Search Options

- **`--search` / `-s`**: Enable database-based file pattern matching. When searching for files by pattern (e.g., `*.jpg`, `IMG_*.png`), this option allows efficient searching across large directory structures using a local database.

- **`--update-db`**: Force database refresh by checking directory timestamps. Use this when you've added new files and want to ensure the database is up-to-date before searching.

- **`--search-paths`**: Specify additional directories to search when files aren't found in the current directory.

### Examples:

```sh
# Fast search using cached database
hmo list "IMG_*.jpg" --search

# Search with database refresh (slower but thorough)
hmo list "IMG_*.jpg" --search --update-db

# Search in specific directories
hmo rename "vacation*.jpg" --search --search-paths /Photos/2024 /Photos/2023
```

## Basic Usages

### List and count all photos

```sh
hmo list 2020 --file-types '*.jpg'
```

will print the name of all files under directory `2020`, with a message showing the number of files at the end. Note that

1. If `2020` is not under the current directory, it will be searched from `--search-paths`.
2. `--file-types` is a file pattern, so you can use options such as `--file-types '202012*.jpg'` to list all files starting with `202012`.

### Rename files according to their date and time

```sh
hmo rename incoming_folder
```

will

1. Retrieve the datatime information of all media files under `incoming_folder`
2. Calculate canonical names for each file according to a `--format` specification, which is usually specified in the configuration files.
3. Rename files interactively or in batch mode if `--yes` is specified.

Note that

1. `--format` uses patterns defined by [Python datetime module](https://docs.python.org/3/library/datetime.html). For example, `%Y%m%d_%H%M%S` rename files to names such as `20201225_212917.jpg`.

It is sometimes desired to add some suffix to filenames, for example to show who took the pictures, which camera was used, where the picture was taken. This can be achieved by

```sh
hmo rename incoming_folder --suffix=-kat
```

which renames files to `20201225_212917-kat.jpg`.

### Organize files

`hmo` organize files according to `media_root` and `dir-pattern`. If you have `dir-pattern` defined as `%Y/%Y-%m`,

```sh
hmo organize incoming_folder
```

will move files under `incoming_folder` to `/path/to/library/2020/2020-12/`.

If you would like to put the files into an album-specific folder, you can use

```sh
hmo organize incoming_folder --album hawaii
```

to move files to paths such as `/path/to/library/2020/2020-12-hawaii/`.

The album name is appended to `dir-pattern` with a dash ( `album-sep="-"`, default). You can set `album-sep="/"` if you would like albums to be organized as `/path/to/library/2020/2020-12/hawaii/`.

### Remove duplicated files

```sh
hmo dedup 2024
```

will find duplicated files under directory `2024` and ask you which copy you would like to keep. If you run in batch mode

```sh
hmo dedup 2024 --yes
```

The command will keep the file with the longest paths, under the assumption that the file with longer path contains more information (suffix, album etc.).

Note that `hmo dedup` checks file contents so files with different filenames but the same contents are considered as duplicates.

### Remove files

```sh
hmo remove unwanted_files/
```

will remove files from the specified directory. The command supports two removal modes:

- **Recycle mode (default)**: Moves files to a recycle bin (`~/.home-media-organizer/recycled/`) for safety
- **Permanent removal**: Permanently deletes files (use with `--operation remove`)

```sh
# Move files to recycle bin (safe, default)
hmo remove old_photos/ --yes

# Permanently delete files (dangerous!)
hmo remove old_photos/ --operation remove --yes

# Remove files matching a pattern with database search
hmo remove "IMG_*.jpg" --search --file-types "*.jpg"
```

**Safety Features:**
- Interactive confirmation for each file (unless `--yes` is used)
- Recycle bin mode allows recovery of accidentally removed files
- Integration with file database and manifest system for tracking

## Advanced Topics

### Do you have a happy family?

To find out the emotions of people in the photos, you first need to annotate all pictures with appropriate tags, with command

```sh
hmo classify 2025 --models emotion --yes
```

This command will tag all photos with faces with emotions such as `angry`, `fear`, `neutral`, `sad`, and `happy`. With tags assigned to these photos, you can count the number of `happy` photos with command

```sh
hmo list 2025 --with-tags happy | wc -l
```

and compare that to the results with

```sh
hmo list 2025 --with-tags sad | wc -l
```

Following the same idea, you can assign photos with tags such as `baby`, `toddler`, and `adult` using the `age` model and list photos with sad adults using

```sh
hmo classify 2025 --models age emotion -y
hmo list 2025 --with-tags 'sad AND adult'
```

Note that

1. `sad AND adult` is needed because `--with-tags sad adult` will list all photos with `sad` or `adult` tags.
2. If you want to see how this command works, find a picture and run the classifier with `-v` (verbose) option.

```sh
hmo classify 2025/2025-01/20250117_123847.jpg --model emotion -v
```

This step is actually recommended because some models may require additional downloads and dependencies (e.g. `emotion:deepface:dlib` needs a separate installation of `dlib`), so it is best to test a model before apply it to a large number of files.

### Find all photos with you

Your library contains tens of thousands of photos and it is challenging to find ones with you, your wife, or your children. Face recognition can be used to address this issue by tagging photos with names.

To start tagging all photos with you, you need to find a few reference photos, preferably portraits that clearly show your facial characteristics. You should first try to see if `hmo` considers them the same person, using command

```sh
hmo set-tags 2020/20200102_123847.jpg --tags John --if-similar-to  2020/20200305_023047.jpg
```

and adjust `threshold` (default to 0.8) if necessary

```sh
hmo set-tags 2020/20200102_123847.jpg --tags John --if-similar-to  2020/20200305_023047.jpg --threshold 0.70
```

You then let `hmo` identify photo with faces resemble one of these photos, using command

```sh
hmo set-tags 2020 --tags John --if-similar-to 2020/20200102_123847.jpg 2020/20200305_023047.jpg --yes --threshold 0.70
```

If you are unsatisfied with the command, you can run

```sh
hmo remove-tags 2020 --tags John
```

to remove the tags and try different reference photos and threshold. Otherwise, enjoy an easy way to find all your photos

```sh
hmo list 2020 --with-tags 'John AND happy'
```

### Compare against a separate collection of files

You may have a separate copy of files, for example, files backed up to DVD or some other media, or files dumped from your camera a while ago, and you would like to know if any files have been changed, removed, or if they have been properly organized into your home library.

Such problems involves the comparison between two sets of files and are performed by command `hmo compare`. This command accepts parameters such as `--A-and-B`, `--A-only`, `--B-only`, and `--A-or-B` where `A` refers to the targets of `hmo compare` command and `B` refers to the files or directories after parameter `--B-only`.

For example

```sh
hmo compare 2025 --B-only my_local_directory
```

list files under `my_local_directory` that are not under `2025`. This command compares based on the **content of the files** so it does not matter if the files have been renamed before copying into `2025`.

If you would like to include files that have been renamed as `--B-only`, use the `--by` option:

```sh
hmo compare 2025 --B-only my_local_directory --by name_and_content
```

If you would like to see how the files have been mapped between two sets of files, you can do something like

```sh
hmo compare 2025 --A-and-B my_local_directory
```

The output will be similar to

```text
2025/20250102_020305.jpg=my_local_directory/IMG_4885.jpg
```

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

## TODO

- `hmo backup` and `hmo restore` to backup lirary to other (cloud) storages.
- Add a `--copy` mode to make sure that the source files will not be changed or moved during `hmo rename` or `hme organize`.
- Improve data detection from media files without EXIF information to handle more types of medias.
- Support for music and movies?

## Credits

This package was created with [Cookiecutter][cookiecutter] and the [fedejaure/cookiecutter-modern-pypackage][cookiecutter-modern-pypackage] project template.

[cookiecutter]: https://github.com/cookiecutter/cookiecutter
[cookiecutter-modern-pypackage]: https://github.com/fedejaure/cookiecutter-modern-pypackage
