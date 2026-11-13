"""Command line entry point: ``mide ...``."""

from __future__ import annotations

from pathlib import Path

import typer

from mide import __version__
from mide.connectors.sources import add_source, list_sources, remove_source
from mide.hardware.profiler import profile_hardware

app = typer.Typer(help="MIDE Engine - local market intelligence engine.", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mide {__version__}")
        raise typer.Exit()


sources_app = typer.Typer(help="Manage authorized data sources.", no_args_is_help=True)
app.add_typer(sources_app, name="sources")

CONFIG_DIR_OPTION = typer.Option(None, "--config-dir", help="Config folder (default: repo config/).")


@sources_app.command("add")
def sources_add(source: str, config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Authorize a folder, file or SQL URL."""
    try:
        value = add_source(source, config_dir)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Source added: {value}")


@sources_app.command("list")
def sources_list(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List authorized sources."""
    sources = list_sources(config_dir)
    if not sources:
        typer.echo("No authorized sources.")
    for src in sources:
        typer.echo(src)


@sources_app.command("remove")
def sources_remove(source: str, config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Revoke an authorized source."""
    if not remove_source(source, config_dir):
        typer.echo(f"Error: source not listed: {source}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Source removed: {source}")


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
