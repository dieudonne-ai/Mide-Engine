"""Command line entry point: ``mide ...``."""

from __future__ import annotations

from pathlib import Path

import typer

from mide import __version__
from mide.config import ConfigError, load_config
from mide.connectors.sources import add_source, list_sources, remove_source
from mide.hardware.profiler import profile_hardware
from mide.ingestion.catalog import build_catalog
from mide.llm.downloader import DownloadError, download_model, list_models, model_path
from mide.llm.prompts import SOURCES_LABEL
from mide.llm.runtime import load_llm
from mide.rag.embeddings import load_embedder
from mide.rag.indexer import index_sources
from mide.rag.retriever import ChatSession, Retriever, answer_question
from mide.rag.store import VectorStore

app = typer.Typer(help="MIDE Engine - local market intelligence engine.", no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"mide {__version__}")
        raise typer.Exit()


sources_app = typer.Typer(help="Manage authorized data sources.", no_args_is_help=True)
app.add_typer(sources_app, name="sources")

CONFIG_DIR_OPTION = typer.Option(
    None, "--config-dir", help="Config folder (default: repo config/)."
)


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


@app.command()
def scan(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Show the catalog of datasets found in the authorized sources."""
    sources = list_sources(config_dir)
    if not sources:
        typer.echo("No authorized sources. Use `mide sources add`.")
        return
    for entry in build_catalog(sources):
        if entry.error:
            typer.echo(f"[error] {entry.item}: {entry.error}")
            continue
        size = "" if entry.rows is None else f" - {entry.rows} rows x {entry.n_columns} cols"
        typer.echo(f"[{entry.kind}] {entry.item}{size}")
        if entry.profile:
            if entry.profile.date_columns:
                typer.echo(f"    date columns: {', '.join(entry.profile.date_columns)}")
            if entry.profile.target_candidates:
                typer.echo(f"    target candidates: {', '.join(entry.profile.target_candidates)}")


@app.command()
def index(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Index authorized sources (only new or modified items are processed)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    if not cfg.sources.sources:
        typer.echo("No authorized sources. Use `mide sources add`.")
        return
    try:
        embedder = load_embedder(cfg, profile_hardware().profile)
    except Exception as exc:  # missing optional dependency or model
        typer.echo(f"Error: cannot load the embedding model: {exc}", err=True)
        raise typer.Exit(1) from exc
    store = VectorStore(cfg.app_dir / "index")
    report = index_sources(
        cfg.sources.sources,
        store,
        embedder,
        cfg.app_dir / "index" / "manifest.json",
        cfg.general.chunk_size,
        cfg.general.chunk_overlap,
        cfg.general.max_file_size_mb,
    )
    typer.echo(
        f"Indexed {len(report.indexed_items)} item(s), {report.new_chunks} new chunk(s); "
        f"{len(report.skipped_items)} unchanged, {len(report.removed_items)} removed."
    )
    for item, err in report.errors.items():
        typer.echo(f"[error] {item}: {err}")


def _load_models(cfg):  # type: ignore[no-untyped-def]
    """Load the embedder and LLM for this machine's profile, or exit with a clear error."""
    report = profile_hardware()
    models = cfg.models.profiles.get(report.profile)
    path = model_path(cfg.app_dir / "models", models.llm) if models else None
    if path is None or not path.is_file():
        typer.echo("Error: model not installed. Run `mide models pull`.", err=True)
        raise typer.Exit(1)
    try:
        return load_embedder(cfg, report.profile), load_llm(path, report)
    except Exception as exc:  # missing optional dependency or model
        typer.echo(f"Error: cannot load the models: {exc}", err=True)
        raise typer.Exit(1) from exc


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask about your indexed data."),
    source: str | None = typer.Option(None, help="Restrict retrieval to one source."),
    top_k: int = typer.Option(5, "--top-k", min=1, help="Number of excerpts retrieved."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Answer a question from the indexed data, citing the sources."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    embedder, llm = _load_models(cfg)
    retriever = Retriever(VectorStore(cfg.app_dir / "index"), embedder, k=top_k)
    answer = answer_question(question, retriever, llm, cfg.language, source=source)
    typer.echo(answer.text)
    if answer.sources:
        typer.echo(f"\n{SOURCES_LABEL.get(cfg.language, 'Sources')}:")
        for line in answer.sources:
            typer.echo(f"  {line}")


models_app = typer.Typer(help="Manage local LLM weights.", no_args_is_help=True)
app.add_typer(models_app, name="models")


@app.command()
def chat(
    top_k: int = typer.Option(5, "--top-k", min=1, help="Number of excerpts retrieved."),
    max_turns: int = typer.Option(4, "--max-turns", min=1, help="Turns kept as history."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Interactive conversation over the indexed data (type `exit` to quit)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    embedder, llm = _load_models(cfg)
    retriever = Retriever(VectorStore(cfg.app_dir / "index"), embedder, k=top_k)
    run_chat(ChatSession(retriever, llm, cfg.language, max_turns))


def run_chat(session: ChatSession) -> None:
    """Read questions from stdin until `exit`/`quit`/EOF; `/reset` clears the history."""
    label = SOURCES_LABEL.get(session.language, "Sources")
    while True:
        try:
            question = typer.prompt(">", prompt_suffix=" ", default="", show_default=False)
        except (EOFError, typer.Abort):
            break
        question = question.strip()
        if question.lower() in {"exit", "quit"}:
            break
        if question == "/reset":
            session.reset()
            continue
        if not question:
            continue
        answer = session.ask(question)
        typer.echo(answer.text)
        if answer.sources:
            typer.echo(f"\n{label}:")
            for line in answer.sources:
                typer.echo(f"  {line}")


def _fmt_size(size: int | None) -> str:
    return "?" if size is None else f"{size / 1e9:.2f} GB"


@models_app.command("list")
def models_list(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List the models of each hardware profile and whether they are installed."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for info in list_models(cfg.models.profiles, cfg.app_dir / "models"):
        state = "installed" if info.installed else "not installed"
        typer.echo(f"{info.profile}: {info.repo}/{info.file} [{state}]")


@models_app.command("pull")
def models_pull(
    profile: str | None = typer.Option(None, help="Profile (default: detected)."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm the download."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Download the model of a profile (asks for confirmation first)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    name = profile or profile_hardware().profile
    models = cfg.models.profiles.get(name)  # type: ignore[call-overload]
    if models is None:
        typer.echo(f"Error: no model configured for profile '{name}'.", err=True)
        raise typer.Exit(1)

    def confirm(url: str, size: int | None) -> bool:
        if yes:
            return True
        return typer.confirm(f"Download {url} ({_fmt_size(size)}) from the internet?")

    last = {"pct": -1}

    def progress(done: int, total: int | None) -> None:
        if total:
            pct = done * 100 // total
            if pct // 10 != last["pct"] // 10:
                typer.echo(f"  {pct}%")
            last["pct"] = pct

    try:
        path = download_model(models.llm, cfg.app_dir / "models", confirm, progress=progress)
    except DownloadError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Model ready: {path}")


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
