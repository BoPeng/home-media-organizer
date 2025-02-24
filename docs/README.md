Table of Contents:

- [General Usage](#general-usage)
  - [Getting Help](#getting-help)
  - [Configuration file](#configuration-file)
- [Explore Your Home Media Library](#explore-your-home-media-library)
  - [`hmo-list`: List media files](#hmo-list-list-media-files)
  - [`hmo show-tags`: Show tags associated with media files](#hmo-show-tags-show-tags-associated-with-media-files)
  - [`hmo show-exif`: Show EXIF metadata of media files](#hmo-show-exif-show-exif-metadata-of-media-files)
  - [`hmo compare` Compare two sets of files](#hmo-compare-compare-two-sets-of-files)
- [Organize Your Library](#organize-your-library)
  - [`hmo rename`: Rename files to their canonical names](#hmo-rename-rename-files-to-their-canonical-names)
  - [`hmo organize`: Organize files into appropriate folder](#hmo-organize-organize-files-into-appropriate-folder)
  - [`hmo validate`: Identify corrupted media files](#hmo-validate-identify-corrupted-media-files)
  - [`hmo dedup` Remove duplicated files](#hmo-dedup-remove-duplicated-files)
  - [`hmo cleanup`: Remove unwanted files and empty directories](#hmo-cleanup-remove-unwanted-files-and-empty-directories)
- [Using Tags](#using-tags)
  - [`hmo set-tags`: Tag all or similar media files](#hmo-set-tags-tag-all-or-similar-media-files)
  - [`hmo remove-tags`: Remove tags associated with media files](#hmo-remove-tags-remove-tags-associated-with-media-files)
  - [`hmo classify`: Classify and assign results as tags to media files](#hmo-classify-classify-and-assign-results-as-tags-to-media-files)
- [Working with EXIF](#working-with-exif)
  - [`hmo set-exif`: Set EXIF of media files](#hmo-set-exif-set-exif-of-media-files)
  - [`hmo shift-exif`: Shift the date EXIF of media files](#hmo-shift-exif-shift-the-date-exif-of-media-files)

## General Usage

### Getting Help

The help message is the authoritative source of information regarding Home Media Organizer

```sh
hmo --help
hmo rename -h
```

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

## Explore Your Home Media Library

### `hmo-list`: List media files

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

# all files with tag VACATION
hmo list 2009 --with-tags VACATION
# all files with some tag, but not those with tag VACATION
hmo list 2009 --with-tags --without-tags VACATION
```

Note that `--search-paths` is an option used by most `hmo` commands, which specifies a list of directories to search when you specify a file or directory that does not exist under the current working directory. It is convenient to set this option in a configuration file to directories you commonly work with.

### `hmo show-tags`: Show tags associated with media files

```sh
hmo show-tags 2009
```

shows all tags for files under folder 2009. This command, and all following tag and classification related commands, requires a parameter `--manifest` that points to a manifest database. This parameter is usually set in the configuration file as

```toml
[default]
manifest = '/path/to/library/manifest.db'
```

so we will ignore this option from the commands.

Using filters `--with-tags` and `--without-tags`, you can prefilter media files before showing tags

```sh
hmo show-tags 2009 --without-tags FACE_FEMALE FACE_MALE
```

If want to display a subset of tags, use option `--tags`

```sh
hmo show-tags 2009 --tags FACE_FEMALE FACE_MALE
```

Note that option `with-tags` is used to show all files with one of the tags and will show all tags, and option `--tags` displays a subset of tags even if the media file has more tags.

The output will by default in plain `text` format, such as

```sh
filename: tag1 tag2
```

but you can change the format to `json`, `json-details`, `text-details`, where the details version will output meta information related to tags, such as `score` from classifiers.

Finally, if you just want to see what tags have been used in your library, run

```sh
hmo show-tags --all
```

The output is by default in `--format text` format, but you can set it to `--format json-details` to see all tags and their metadata.

### `hmo show-exif`: Show EXIF metadata of media files

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

## Organize Your Library

### `hmo rename`: Rename files to their canonical names

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

### `hmo organize`: Organize files into appropriate folder

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

### `hmo validate`: Identify corrupted media files

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

### `hmo cleanup`: Remove unwanted files and empty directories

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

If you notice any bug, or have any request for new features, please submit a ticket or a PR through the GitHub ticket tracker.

## Using Tags

### `hmo set-tags`: Tag all or similar media files

Unlike `exif` which are part of the media files, tags are stored in a separate database specified with parameter `--manifest`. These tags have a name, and an arbitray set of metadata, which holds values such as `score` for some classifier.

To set tags to a set of files, run

```sh
hmo set-tags 2009/2009-10/ --tags vacation hawaii
```

The command by default adds tags to the media files. You can replace all existing tags with specified tags with option `--overwrite`. If you would like to remove a set of tags, use command `hmo unset-tags`.

The `set-tags` command can also be used to tag photos that are similar to each other, for example from the same person. To do this, you need to first identify a few example photos as the seed photo, and run

```sh
hmo set-tags 2009/ --tags Patrick --if-similar-to patrick01.jpg patrick02.jpg
```

With this command, _home-media-organizer_ will use a face recognition algorithm to compare all pictures under `2009` with these two pictures, and tag them with `Patrick` if the pictures contains faces of patrick. The default similarity score is `0.9` but you can adjust it with options like `--threshold 0.75` to allow less-similar photos to be tagged.

### `hmo remove-tags`: Remove tags associated with media files

The following command remove the tag `vacation` from specified files but leaves other tags untouched.

```sh
hmo unset-tags 2009/2009-10/ --tags vacation
```

### `hmo classify`: Classify and assign results as tags to media files

Command `hmo classify` applies a machine learning model on the media files and set the results as tags.

For example, to identify pictures that are not suitable to viewed by public, even family members, you can use a [nudenet](https://github.com/notAI-tech/nudenet) model as follows

```sh
hmo classify 2009 --model nudenet
```

to assign tags such as `FACE_FEMALE`, `BELLY_EXPOSED`, and `FEMALE_BREAST_COVERED` to medias. You can then use commands such as

```sh
hmo show-tags 2009 --tags FEMALE_BREAST_COVERED
```

to identify inappropriate photos and act accordingly.

The `nudenet` model assigns metadata such as `score` to each prediction. You can use command

```sh
hmo classify 2009 --model nudenet --threshold 0.9
```

to only assign tags if the model is confident enough.

You can also limit the tags that you would like to assign with option

```sh
hmo classify 2009 --model nudenet --threshold 0.9 --tags FEMALE_BREAST_COVERED BELLY_EXPOSED
```

_home-media-organizer_ currently supports the following models and tags

| model   | tags                       | comment                           |
| ------- | -------------------------- | --------------------------------- |
| nudenet | `FEMALE_GENITALIA_COVERED` |                                   |
|         | `FACE_FEMALE`              |                                   |
|         | `BUTTOCKS_EXPOSED`         |                                   |
|         | `FEMALE_BREAST_EXPOSED`    |                                   |
|         | `FEMALE_GENITALIA_EXPOSED` |                                   |
|         | `MALE_BREAST_EXPOSED`      |                                   |
|         | `ANUS_EXPOSED`             |                                   |
|         | `FEET_EXPOSED`             |                                   |
|         | `BELLY_COVERED`            |                                   |
|         | `FEET_COVERED`             |                                   |
|         | `ARMPITS_COVERED`          |                                   |
|         | `ARMPITS_EXPOSED`          |                                   |
|         | `FACE_MALE`                |                                   |
|         | `BELLY_EXPOSED`            |                                   |
|         | `MALE_GENITALIA_EXPOSED`   |                                   |
|         | `ANUS_COVERED`             |                                   |
|         | `FEMALE_BREAST_COVERED`    |                                   |
|         | `BUTTOCKS_COVERED`         |                                   |
| face    | `face`                     | Set `face` if a face is detected. |
| age     | `baby`                     | age < 3                           |
|         | `toddler`                  | 3 <= age < 12                     |
|         | `teenager`                 | 12 <= age < 20                    |
|         | `adult`                    | 20 <= age < 60                    |
|         | `elderly`                  | age >= 60                         |
| gender  | `Male`                     |                                   |
|         | `Female`                   |                                   |
| race    | `asian`                    |                                   |
|         | `white`                    |                                   |
|         | `middle eastern`           |                                   |
|         | `indian`                   |                                   |
|         | `latino`                   |                                   |
|         | `black`                    |                                   |
| emotion | `angry`                    |                                   |
|         | `fear`                     |                                   |
|         | `neutral`                  |                                   |
|         | `sad`                      |                                   |
|         | `disgust`                  |                                   |
|         | `happy`                    |                                   |
|         | `surprise`                 |                                   |

## Working with EXIF

### `hmo set-exif`: Set EXIF of media files

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

### `hmo shift-exif`: Shift the date EXIF of media files

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
