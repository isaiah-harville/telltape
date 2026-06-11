"""Command-line entry point that launches the terminal interface."""

from __future__ import annotations

import click

from .tui import TelltapeApp


@click.command()
@click.version_option(package_name="telltape")
def cli() -> None:
    """Launch telltape, a live financial and world news terminal."""
    TelltapeApp().run()


def main() -> None:
    """Console-script entry point."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
