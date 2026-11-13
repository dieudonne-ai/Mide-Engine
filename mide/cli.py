"""Command line entry point: ``mide ...``."""

from __future__ import annotations

import typer

from mide import __version__
from mide.hardware.profiler import profile_hardware

app = typer.Typer(help="MIDE Engine - local market intelligence engine.", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mide {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version."
    ),
) -> None:
    """MIDE Engine command line."""


@app.command()
def doctor() -> None:
    """Check that the installation works and show the hardware report."""
    report = profile_hardware()
    typer.echo("OK")
    typer.echo(f"RAM: {report.ram_gb} GB")
    typer.echo(f"CPU cores: {report.cpu_cores}")
    typer.echo(f"OS: {report.os_name}")
    gpu = f"{report.gpu.name} ({report.gpu.vram_gb} GB VRAM)" if report.gpu else "none"
    typer.echo(f"GPU: {gpu}")
    typer.echo(f"Disk free: {report.disk_free_gb} GB")
    typer.echo(f"Profile: {report.profile}")


if __name__ == "__main__":
    app()
