"""Command line entry point: ``mide ...``."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from mide import __version__
from mide.agent.decision import detect_tables, recommend, run_modules
from mide.agent.router import route_question
from mide.automl.auto import AutoReport, fingerprint, retrain_if_changed
from mide.automl.evaluator import evaluate
from mide.automl.registry import list_models as list_trained_models
from mide.automl.registry import save_model
from mide.automl.trainer import train as train_model
from mide.config import Config, ConfigError, load_config
from mide.connectors.base import is_url
from mide.connectors.sources import add_source, list_sources, remove_source
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import TabularConnector
from mide.hardware.profiler import profile_hardware
from mide.ingestion.catalog import build_catalog
from mide.llm.chat import ChatHistory
from mide.llm.downloader import DownloadError, download_model, list_models, model_path
from mide.llm.prompts import build_rag_prompt, sources_footer
from mide.llm.runtime import LLM, load_llm
from mide.rag.embeddings import Embedder, load_embedder
from mide.rag.indexer import index_sources
from mide.rag.retriever import Retriever
from mide.rag.store import VectorStore

logger = logging.getLogger(__name__)
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


models_app = typer.Typer(help="Manage local LLM weights.", no_args_is_help=True)
app.add_typer(models_app, name="models")


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


@models_app.command("trained")
def models_trained(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List the models trained by `mide train`."""
    cfg = load_config(config_dir)
    records = list_trained_models(cfg.app_dir / "models_trained")
    if not records:
        typer.echo("No trained models. Use `mide train --dataset X --target Y`.")
        return
    for r in records:
        m = r.metadata
        score = m["metrics"].get(m["primary_metric"])
        typer.echo(
            f"{r.name} v{r.version} [{m['task']}] target={m['target']} "
            f"{m['primary_metric']}={score:.4g} beats_baseline={m['beats_baseline']}"
        )


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


def _get_embedder(cfg: Config) -> Embedder:
    """Load the embedder of the detected hardware profile (patched in tests)."""
    return load_embedder(cfg, profile_hardware().profile)


@app.command("index")
def index_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Index the authorized sources (only new or modified files are processed)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    sources = list_sources(config_dir)
    if not sources:
        typer.echo("No authorized sources. Use `mide sources add`.")
        return
    try:
        report = index_sources(
            sources,
            cfg.app_dir / "index",
            _get_embedder(cfg),
            cfg.general.chunk_size,
            cfg.general.chunk_overlap,
            cfg.general.max_file_size_mb,
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"Indexed: {len(report.new_items)} new, {len(report.updated_items)} updated, "
        f"{len(report.unchanged_items)} unchanged, {len(report.removed_items)} removed "
        f"({report.new_chunks} new chunks)."
    )
    for item, message in report.errors.items():
        typer.echo(f"[error] {item}: {message}")


def _load_dataset(dataset: str, sources: list[str]):
    """Read one authorized dataset, matched by full item name or file/table name."""
    from mide.connectors.tabular import split_item

    for source in sources:
        conn = SQLConnector(source, sources) if is_url(source) else None
        if conn is None:
            if not Path(source).expanduser().exists():
                continue
            conn = TabularConnector(source, sources)
        for item in conn.discover():
            base = Path(split_item(item)[0]).stem if not is_url(source) else item
            if dataset in (item, base, Path(item).name):
                return item, conn.read(item)
    raise ValueError(f"Dataset not found in authorized sources: {dataset}")


@app.command("train")
def train_command(
    dataset: str = typer.Option(..., "--dataset", help="Dataset name (file stem or table)."),
    target: str = typer.Option(..., "--target", help="Column to predict."),
    date_column: str | None = typer.Option(None, "--date-column", help="Date column override."),
    seed: int = typer.Option(42, "--seed"),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Train a model on an authorized dataset and save it in the registry."""
    try:
        cfg = load_config(config_dir)
        _item, df = _load_dataset(dataset, list_sources(config_dir))
        result = train_model(
            df, target, profile=profile_hardware().profile, seed=seed, date_column=date_column
        )
        metrics = evaluate(result, df)
        record = save_model(
            result,
            cfg.app_dir / "models_trained",
            f"{dataset}-{target}",
            {"evaluation": metrics, "dataset": dataset, "data_hash": fingerprint(df)},
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Task: {result.task.task.value} - {result.task.reason}")
    typer.echo(f"Saved {record.name} v{record.version}")
    for key, value in result.metrics.items():
        typer.echo(f"  CV {key}: {value:.4g} (baseline {result.baseline_metrics[key]:.4g})")
    verdict = "beats" if result.beats_baseline else "does NOT beat"
    typer.echo(f"The model {verdict} the baseline.")
    top = ", ".join(f"{k} ({v:.0%})" for k, v in list(result.feature_importance.items())[:5])
    typer.echo(f"Top features: {top}")


def _get_llm(cfg: Config) -> LLM:
    """Load the local LLM of the detected profile (patched in tests)."""
    report = profile_hardware()
    spec = cfg.models.profiles[report.profile].llm  # type: ignore[index]
    path = model_path(cfg.app_dir / "models", spec)
    if not path.exists():
        raise DownloadError(f"Model not installed: run `mide models pull` ({path.name}).")
    return load_llm(path, report)


def _load_all_datasets(sources: list[str]) -> dict:
    """Read every tabular dataset of the authorized sources (read-only)."""
    frames: dict = {}
    for source in sources:
        try:
            if is_url(source):
                conn = SQLConnector(source, sources)
            elif Path(source).expanduser().exists():
                conn = TabularConnector(source, sources)
            else:
                continue
            for item in conn.discover():
                try:
                    frames[item] = conn.read(item)
                except Exception as exc:  # noqa: BLE001 - unreadable item: skip it
                    logger.debug("Skipping %s: %s", item, exc)
        except Exception as exc:  # noqa: BLE001 - unreachable source: skip it
            logger.debug("Skipping source %s: %s", type(exc).__name__, exc)
    return frames


class EmptyIndexError(Exception):
    """The vector index is empty and no business data can answer."""


def ask_answer(question: str, config_dir: Path | None = None, source: str | None = None,
               top_k: int = 5) -> tuple[str, str, str]:
    """Answer a question; returns (answer, figures used, sources footer)."""
    cfg = load_config(config_dir)
    route = route_question(question)
    passages: list = []
    findings: list = []
    if route.modules:
        findings = run_modules(route.modules, detect_tables(_load_all_datasets(list_sources(config_dir))))
        if not findings and not route.use_rag:
            route.use_rag = True  # no usable business data: fall back to documents
    if route.use_rag:
        store = VectorStore(cfg.app_dir / "index")
        if store.count() == 0 and not findings:
            raise EmptyIndexError(
                "Index vide. Lancez `mide index`." if cfg.language == "fr"
                else "Empty index. Run `mide index`.")
        if store.count() > 0:
            passages = Retriever(store, _get_embedder(cfg), top_k).retrieve(question, source=source)
    llm = _get_llm(cfg)
    if findings:
        rec = recommend(question, findings, llm, passages, cfg.language)
        answer, used = rec.text, rec.data_used(cfg.language)
    else:
        prompt = build_rag_prompt(question, passages, cfg.language)
        answer, used = llm.generate(prompt, max_tokens=512, temperature=0.2), ""
    return answer.strip(), used, sources_footer(passages)


@app.command("ask")
def ask_command(
    question: str,
    source: str | None = typer.Option(None, help="Restrict to one indexed source."),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Number of excerpts."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Answer a question: documents (RAG), business modules, or both (agent)."""
    try:
        answer, used, footer = ask_answer(question, config_dir, source, top_k)
    except (ConfigError, DownloadError, EmptyIndexError) as exc:
        typer.echo(f"Error: {exc}" if not isinstance(exc, EmptyIndexError) else str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(answer)
    if used:
        typer.echo("\n" + used)
    if footer:
        typer.echo("\n" + footer)


@app.command("ui")
def ui_command(
    port: int = typer.Option(8501, help="Port of the dashboard."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Launch the Streamlit dashboard (needs `pip install mide-engine[ui]`)."""
    import importlib.util
    import os
    import subprocess
    import sys

    from mide.dashboard_data import CONFIG_ENV

    if importlib.util.find_spec("streamlit") is None:
        typer.echo("Streamlit is not installed: pip install 'mide-engine[ui]'", err=True)
        raise typer.Exit(1)
    script = Path(__file__).resolve().parent.parent / "app" / "dashboard.py"
    if not script.exists():
        typer.echo(f"Dashboard not found: {script}", err=True)
        raise typer.Exit(1)
    env = dict(os.environ)
    if config_dir is not None:
        env[CONFIG_ENV] = str(config_dir.resolve())
    cmd = [sys.executable, "-m", "streamlit", "run", str(script), "--server.port", str(port),
           "--browser.gatherUsageStats", "false"]
    raise typer.Exit(subprocess.call(cmd, env=env))


REPORT_FORMAT_OPTION = typer.Option("md", "--format", help="md or html.")
REPORT_OUTPUT_OPTION = typer.Option(None, "--output", "-o", help="Output file (default: stdout).")


@app.command("report")
def report_command(
    fmt: str = REPORT_FORMAT_OPTION,
    output: Path | None = REPORT_OUTPUT_OPTION,
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Generate the weekly report (KPIs, forecasts, alerts, 3 priority actions)."""
    from mide.report import build_report, render_html, render_markdown

    if fmt not in ("md", "html"):
        typer.echo("Format must be 'md' or 'html'.", err=True)
        raise typer.Exit(2)
    cfg = load_config(config_dir)
    tables = detect_tables(_load_all_datasets(list_sources(config_dir)))
    report = build_report(tables, cfg.language)
    text = render_html(report) if fmt == "html" else render_markdown(report)
    if output is None:
        typer.echo(text)
    else:
        output.write_text(text, encoding="utf-8")
        typer.echo(f"Report written: {output}")


@app.command("auto")
def auto_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Scan, index incrementally, retrain changed models (kept only if better), report."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    sources = list_sources(config_dir)
    if not sources:
        typer.echo("No authorized sources. Use `mide sources add`.")
        return
    report = AutoReport(n_datasets=len(build_catalog(sources)))
    try:
        idx = index_sources(
            sources,
            cfg.app_dir / "index",
            _get_embedder(cfg),
            cfg.general.chunk_size,
            cfg.general.chunk_overlap,
            cfg.general.max_file_size_mb,
        )
        report.index_summary = (
            f"{len(idx.new_items)} new, {len(idx.updated_items)} updated, "
            f"{len(idx.unchanged_items)} unchanged, {len(idx.removed_items)} removed"
        )
        report.outcomes = retrain_if_changed(
            _load_all_datasets(sources),
            cfg.app_dir / "models_trained",
            cfg.app_dir / "auto_state.json",
            profile=profile_hardware().profile,
        )
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"Scan: {report.n_datasets} datasets/documents.")
    typer.echo(f"Index: {report.index_summary}.")
    if not report.outcomes:
        typer.echo("No trained models. Use `mide train --dataset X --target Y`.")
    for o in report.outcomes:
        scores = "" if o.new_score is None else f" ({o.old_score:.4g} -> {o.new_score:.4g})"
        typer.echo(f"Model {o.name}: {o.status}{scores} {o.detail}".rstrip())


@app.command("chat")
def chat_command(
    source: str | None = typer.Option(None, help="Restrict to one indexed source."),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Number of excerpts."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Interactive conversation over the indexed data (type `exit` to quit)."""
    try:
        cfg = load_config(config_dir)
        store = VectorStore(cfg.app_dir / "index")
        if store.count() == 0:
            typer.echo(
                "Index vide. Lancez `mide index`." if cfg.language == "fr"
                else "Empty index. Run `mide index`."
            )
            raise typer.Exit(1)
        retriever = Retriever(store, _get_embedder(cfg), top_k)
        llm = _get_llm(cfg)
    except (ConfigError, DownloadError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    history = ChatHistory()
    typer.echo(
        "Posez vos questions (`exit` pour quitter, `/clear` pour oublier)."
        if cfg.language == "fr"
        else "Ask your questions (`exit` to quit, `/clear` to forget)."
    )
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            break
        if question.lower() in {"exit", "quit", "/exit", "/quit"}:
            break
        if question == "/clear":
            history.clear()
            continue
        if not question:
            continue
        passages = retriever.retrieve(question, source=source)
        prompt = build_rag_prompt(question, passages, cfg.language, history.render(cfg.language))
        answer = llm.generate(prompt, max_tokens=512, temperature=0.2).strip()
        history.add(question, answer)
        typer.echo(answer)
        footer = sources_footer(passages)
        if footer:
            typer.echo("\n" + footer)


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
