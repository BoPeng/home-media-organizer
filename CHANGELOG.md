# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.7]

- Add command `hmo tag` to set specified tag or tags returned by some models
- Add option `--with-tags` and `--without-tags` to filter files by tags
- Add option `--manifest` to `hmo validate`

## [0.3.6]

- Add subcommand `compare`
- Add option `--operation copy|move` to command `hmo organize`.

## [0.3.4]

- Add option `--search-paths`

## [0.3.4]

- Fix a bug on renaming files
- Add option `--suffix` to `hmo rename`

## [0.3.2]

- Fix a bug in `hmo organize.
- Improved prompt (allow default).
- Allow for configuration files

## [0.3.0]

- Expand `--with-exif` and `--without-exif` to allow single `key` and allow `*` in `key`.
- Caching expensive operations such as md5 calculation and file viewable/playable tests, and add option `--no-cache` to invalidate the cache.

## [0.2.0] - 2025-01-18

- Add `hmo validate`

## [0.1.0] - 2025-01-18

- Initial release

### Added

- First release on PyPI.

[Unreleased]: https://github.com/BoPeng/home-media-organizer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/BoPeng/home-media-organizer/compare/releases/tag/v0.1.0
