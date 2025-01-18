"""Console script for home-media-organizer."""

from typing import Annotated, Optional
import typer

from home_media_organizer import __version__

from typer.models import Context
from .home_media_organizer import *

app = typer.Typer()


def version_callback(value: bool) -> None:
    """Callback function for the --version option.

    Parameters:
        - value: The value provided for the --version option.

    Raises:
        - typer.Exit: Raises an Exit exception if the --version option is provided,
        printing the Awesome CLI version and exiting the program.
    """
    if value:
        typer.echo(f"home-media-organizer, version {__version__}")
        raise typer.Exit()


@app.command()
def main(
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True)
    ] = None,
) -> None:
    """Console script for home-media-organizer."""
    typer.echo(
        "An Swiss Army Knife kind of tool to help fix, organize, and maitain your home media library "
    )
    typer.echo("See documentation at https://github.com/BoPeng/home-media-organizer/")


@app.callback()
def common(
    ctx: typer.Context,
    file_types: list[str] = typer.Option([], "--file-types", "-t", help="File types to process"),
    with_exif: list[str] = typer.Option(
        [], "--with-exif", help="Process only media with exif specified data"
    ),
    without_exif: list[str] = typer.Option(
        [], "--without-exif", help="Process only media without exif specified data"
    ),
    jobs: int = typer.Option(4, "--jobs", "-j", help="Number of parallel jobs"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """
    Common options for all commands.
    """
    ctx.obj = {
        "verbose": verbose,
        "file_types": file_types,
        "with_exif": with_exif,
        "without_exit": without_exif,
        "jobs": jobs,
        "yes": yes,
    }


@app.command()
def list_files(
    items: list[str] = typer.Argument(help="Files or directories to process"),
    ctx: Context = None,
):
    """List all or selected media files."""
    for item in iter_files(items, **ctx.obj):
        typer.echo(item)


if __name__ == "__main__":
    app()  # pragma: no cover
