# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Media Organizer (hmo) is a Python CLI tool for organizing, managing, and maintaining home media libraries. It provides functionality for:

- **Media Organization**: Automatically organize photos/videos by date from EXIF data
- **Duplicate Detection**: Find and remove duplicate media files based on content
- **AI Classification**: Face detection, emotion/age/gender detection, NSFW detection
- **Tag Management**: Add, remove, and search media files by custom tags
- **EXIF Management**: View, set, and modify EXIF metadata
- **File Validation**: Detect corrupted media files

## Development Commands

The project uses Poetry for dependency management and Invoke for task automation.

### Essential Commands

```bash
# Install dependencies and setup
poetry install
poetry run invoke install-hooks

# Run tests
poetry run invoke tests
# or via nox for multiple Python versions
nox -s tests

# Linting and formatting
poetry run invoke lint         # Run all linting (ruff, security, format check)
poetry run invoke format       # Format code with black/isort
poetry run ruff check src/ tests/  # Just ruff linting

# Type checking
poetry run invoke mypy
# or via nox
nox -s mypy

# Run the CLI tool
poetry run hmo --help
# or after installation
hmo --help

# Security scanning
poetry run invoke security

# Generate documentation
poetry run invoke docs
```

### Testing Individual Components

```bash
# Test specific file
poetry run pytest tests/test_cli.py -v

# Test with coverage
poetry run pytest --cov=home_media_organizer --cov-report=html

# Run doctests
poetry run pytest --xdoctest src/
```

## Architecture and Code Structure

### Core Architecture

The application follows a command-based CLI architecture:

- **CLI Entry Point**: `src/home_media_organizer/cli.py` - Main argparse-based CLI with subcommands
- **Core Media Handling**: `src/home_media_organizer/media_file.py` - Central MediaFile class and date extraction logic
- **Command Modules**: Each command (organize, rename, dedup, etc.) has its own module with parser and implementation
- **Configuration**: `src/home_media_organizer/config.py` - TOML-based configuration system
- **Utilities**: `src/home_media_organizer/utils.py` - Shared utilities and operation classes

### Key Classes and Patterns

- **MediaFile Class**: Core abstraction for media files with EXIF data extraction, date parsing, and metadata management
- **Operation Classes**: `OrganizeOperation`, `RemoveOperation` for tracking file operations
- **Date Extraction Pipeline**: Multiple strategies for extracting dates from files:
  1. EXIF data via PIL and exiftool
  2. Filename pattern matching
  3. File modification dates
  4. Manual date setting

### Command Structure

Each command follows this pattern:
- `get_*_parser()` function to define CLI arguments
- Main implementation function that processes files
- Integration with common argument patterns (file types, tags, search paths)

### External Dependencies

- **exiftool**: For comprehensive EXIF metadata operations (requires separate installation)
- **PIL/Pillow**: For image processing and basic EXIF reading
- **deepface**: For AI-powered face recognition and emotion detection
- **nudenet**: For NSFW content detection
- **ffmpeg-python**: For video file validation (requires ffmpeg installation)

### Configuration System

- Default config location: `~/.home-media-organizer/config.toml`
- Supports per-command configuration sections
- Key settings: search-paths, media-root, file organization patterns
- Format patterns use Python datetime format strings

### File Organization Logic

- **Date Extraction**: Prioritizes EXIF data, falls back to filename patterns, then file dates
- **Directory Patterns**: Configurable via `dir-pattern` (e.g., `%Y/%Y-%m` for year/year-month structure)
- **Album Support**: Optional album names appended to directory structure
- **Duplicate Handling**: Content-based comparison using file hashes

## Development Guidelines

### Code Style and Quality

- Line length: 99 characters (configured in pyproject.toml)
- Code formatting: Black + isort
- Linting: Ruff with extensive rule set
- Type checking: mypy with strict settings
- Pre-commit hooks enforce formatting and linting

### Testing Requirements

- Test coverage target: 100% (configured in pyproject.toml)
- Tests use pytest with xdoctest for docstring examples
- Coverage reports exclude pragma comments and debug code

### Adding New Commands

1. Create new module in `src/home_media_organizer/`
2. Implement `get_*_parser()` function for CLI arguments
3. Add parser integration to `cli.py`
4. Follow existing patterns for file processing and user interaction
5. Add comprehensive tests in `tests/` directory

### Common Patterns

- Use `add_common_arguments()` for shared CLI options
- Implement `--yes` flag for batch operations
- Use `get_response()` for interactive confirmations
- Use `manifest()` for operation logging
- Handle file paths with `Path` objects throughout
