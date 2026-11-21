"""Command line entry point: ``mide ...``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import typer

from mide import __version__
from mide.agent.decision import (
    Recommendation,
    detect_tables,
    french_numbers,
    recommend,
    run_modules,
)
from mide.agent.router import route_question
from mide.automl.auto import AutoReport, ModelOutcome, fingerprint, retrain_if_changed
from mide.automl.evaluator import evaluate
from mide.automl.registry import list_models as list_trained_models
from mide.automl.registry import save_model
from mide.automl.task_detector import TargetError, TaskInfo
from mide.automl.trainer import TrainingError
from mide.automl.trainer import train as train_model
from mide.config import Config, ConfigError, load_config
from mide.connectors.base import is_url
from mide.connectors.sources import (
    EmptySource,
    SourceCovered,
    add_source,
    list_sources,
    remove_source,
    source_missing,
    source_owning,
)
from mide.connectors.sql import SQLConnector
from mide.connectors.tabular import TabularConnector, split_item
from mide.hardware.profiler import profile_hardware
from mide.ingestion.catalog import build_catalog
from mide.llm.chat import ChatHistory
from mide.llm.downloader import DownloadError, download_model, list_models, model_path
from mide.llm.lora import finetune, load_documents, peft_trainer, unavailable_reason
from mide.llm.prompts import build_rag_prompt, sources_footer
from mide.llm.runtime import LLM, LLMError, load_llm
from mide.rag.embeddings import Embedder, EmbeddingError, load_embedder
from mide.rag.indexer import index_sources
from mide.rag.retriever import Retriever
from mide.rag.store import VectorStore
from mide.utils.errors import MissingDependencyError, friendly_message
from mide.utils.french import NBSP, french_spacing
from mide.utils.privacy import build_privacy_report

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


SOURCES_MESSAGES: dict[str, dict[str, str]] = {
    "added": {"fr": "Source ajoutée : {value}", "en": "Source added: {value}"},
    "covered": {
        "fr": "Déjà autorisé par le dossier {folder} : {value} n'a pas été ajouté.",
        "en": "Already authorized by the folder {folder}: {value} was not added.",
    },
    "removed": {"fr": "Source retirée : {value}", "en": "Source removed: {value}"},
    "none": {"fr": "Aucune source autorisée.", "en": "No authorized sources."},
    "none_hint": {
        "fr": "Aucune source autorisée. Utilisez `mide sources add`.",
        "en": "No authorized sources. Use `mide sources add`.",
    },
    "listed": {"fr": "Sources autorisées : {value}", "en": "Authorized sources: {value}"},
    "not_listed": {
        "fr": "Erreur : source non listée : {value}. {hint}",
        "en": "Error: source not listed: {value}. {hint}",
    },
    "empty_source": {
        "fr": "Erreur : la source est vide ; indiquez un dossier, un fichier ou une URL SQL.",
        "en": "Error: the source is empty; give a folder, a file or a SQL URL.",
    },
    "missing_path": {
        "fr": "Erreur : le chemin n'existe pas : {value}",
        "en": "Error: path does not exist: {value}",
    },
    "password": {
        "fr": ("Erreur : ne mettez pas de mot de passe dans l'URL ; utilisez une variable "
               "d'environnement (ex. ${{DB_PASSWORD}})."),
        "en": ("Error: do not put a password in the URL; use an environment variable "
               "(e.g. ${{DB_PASSWORD}})."),
    },
    "no_models_hint": {
        "fr": "Aucun modèle entraîné. Utilisez `mide train --dataset X --target Y`.",
        "en": "No trained models. Use `mide train --dataset X --target Y`.",
    },
    "trained_line": {
        "fr": "{name} v{version} [{task}] cible={target} {metric}={score} bat_reference={beats}",
        "en": ("{name} v{version} [{task}] target={target} {metric}={score} "
               "beats_baseline={beats}"),
    },
    "yes": {"fr": "oui", "en": "True"},
    "no": {"fr": "non", "en": "False"},
    "report_format": {
        "fr": "Le format doit être 'md' ou 'html'.",
        "en": "Format must be 'md' or 'html'.",
    },
    "report_written": {"fr": "Rapport écrit : {value}", "en": "Report written: {value}"},
    "train_task": {"fr": "Tâche : {task} - {reason}", "en": "Task: {task} - {reason}"},
    "task_regression": {"fr": "régression", "en": "regression"},
    "task_classification": {"fr": "classification", "en": "classification"},
    "task_time_series": {"fr": "série temporelle", "en": "time_series"},
    "reason_non_numeric": {
        "fr": "cible non numérique avec {n} classes",
        "en": "non-numeric target with {n} classes",
    },
    "reason_few_integers": {
        "fr": "cible entière avec seulement {n} valeurs",
        "en": "integer target with only {n} values",
    },
    "reason_dated": {
        "fr": "cible numérique avec la colonne de date '{date}'",
        "en": "numeric target with date column '{date}'",
    },
    "reason_continuous": {
        "fr": "cible numérique continue, pas de colonne de date utilisable",
        "en": "continuous numeric target, no usable date column",
    },
    "train_saved": {
        "fr": "Modèle enregistré : {name} v{version}",
        "en": "Saved {name} v{version}",
    },
    "train_cv": {
        "fr": "  VC {metric} : {value} (référence {baseline})",
        "en": "  CV {metric}: {value} (baseline {baseline})",
    },
    "train_beats": {
        "fr": "Le modèle bat la référence.",
        "en": "The model beats the baseline.",
    },
    "train_not_beats": {
        "fr": "Le modèle ne bat PAS la référence.",
        "en": "The model does NOT beat the baseline.",
    },
    "train_leak": {
        "fr": ("Attention : score presque parfait, fuite de la cible probable. Vérifiez que "
               "{columns} ne sont pas calculées à partir de '{target}' ni connues après lui ; "
               "sinon retirez-les des données avant d'entraîner."),
        "en": ("Warning: near-perfect score, likely target leakage. Check that {columns} "
               "are not computed from '{target}' or only known after it; if so, remove "
               "them from the data before training."),
    },
    "train_top": {"fr": "Variables principales : {value}", "en": "Top features: {value}"},
    "doctor_ram": {"fr": "RAM : {value} Go", "en": "RAM: {value} GB"},
    "doctor_cpu": {"fr": "Cœurs CPU : {value}", "en": "CPU cores: {value}"},
    "doctor_os": {"fr": "OS : {value}", "en": "OS: {value}"},
    "doctor_gpu": {"fr": "GPU : {value}", "en": "GPU: {value}"},
    "doctor_gpu_vram": {"fr": "{name} ({vram} Go de VRAM)", "en": "{name} ({vram} GB VRAM)"},
    "doctor_gpu_none": {"fr": "aucun", "en": "none"},
    "doctor_disk": {"fr": "Espace disque libre : {value} Go", "en": "Disk free: {value} GB"},
    "doctor_profile": {"fr": "Profil : {value}", "en": "Profile: {value}"},
    "models_installed": {"fr": "installé", "en": "installed"},
    "models_not_installed": {"fr": "non installé", "en": "not installed"},
    "models_no_profile": {
        "fr": ("Erreur : aucun modèle configuré pour le profil '{name}'. "
               "Profils configurés : {configured}"),
        "en": "Error: no model configured for profile '{name}'. Configured profiles: {configured}",
    },
    "models_none": {"fr": "aucun", "en": "none"},
    "models_confirm": {
        "fr": "Télécharger {url} ({size}) depuis internet ?",
        "en": "Download {url} ({size}) from the internet?",
    },
    "models_ready": {"fr": "Modèle prêt : {value}", "en": "Model ready: {value}"},
    "ui_no_streamlit": {
        "fr": "Erreur : Streamlit n'est pas installé : pip install 'mide-engine[ui]'",
        "en": "Error: Streamlit is not installed: pip install 'mide-engine[ui]'",
    },
    "ui_no_dashboard": {
        "fr": "Erreur : tableau de bord introuvable : {value}",
        "en": "Error: dashboard not found: {value}",
    },
    "error": {"fr": "Erreur : {value}", "en": "Error: {value}"},
    "dashboard_config_error": {
        "fr": "Erreur de configuration : {value}",
        "en": "Configuration error: {value}",
    },
    "item_error": {"fr": "[erreur] {item} : {message}", "en": "[error] {item}: {message}"},
    "source_missing": {
        "fr": "Attention : source introuvable, ignorée : {value}",
        "en": "Warning: source not found, skipped: {value}",
    },
    "index_done": {
        "fr": ("Indexation : {new} nouveaux, {updated} mis à jour, {unchanged} inchangés, "
               "{removed} retirés ({chunks} nouveaux extraits)."),
        "en": ("Indexed: {new} new, {updated} updated, {unchanged} unchanged, "
               "{removed} removed ({chunks} new chunks)."),
    },
    "scan_size": {"fr": " - {rows} lignes x {cols} colonnes", "en": " - {rows} rows x {cols} cols"},
    "scan_dates": {"fr": "    colonnes de date : {value}", "en": "    date columns: {value}"},
    "scan_targets": {"fr": "    cibles possibles : {value}", "en": "    target candidates: {value}"},
    "auto_scan": {
        "fr": "Analyse : {value} jeux de données/documents.",
        "en": "Scan: {value} datasets/documents.",
    },
    "auto_index": {"fr": "Indexation : {value}.", "en": "Index: {value}."},
    "auto_index_counts": {
        "fr": "{new} nouveaux, {updated} mis à jour, {unchanged} inchangés, {removed} retirés",
        "en": "{new} new, {updated} updated, {unchanged} unchanged, {removed} removed",
    },
    "auto_index_skipped": {"fr": "ignorée ({value})", "en": "skipped ({value})"},
    "auto_model": {"fr": "Modèle {name} : {status}", "en": "Model {name}: {status}"},
    "auto_unchanged": {"fr": "inchangé", "en": "unchanged"},
    "auto_kept": {"fr": "conservé", "en": "kept"},
    "auto_kept_leak": {"fr": "conservé", "en": "kept"},
    "auto_promoted": {"fr": "remplacé", "en": "promoted"},
    "auto_skipped": {"fr": "ignoré", "en": "skipped"},
    "auto_error": {"fr": "erreur", "en": "error"},
    "auto_detail_promoted": {"fr": "le nouveau modèle est meilleur", "en": "new model is better"},
    "auto_detail_kept": {"fr": "l'ancien modèle est conservé", "en": "previous model kept"},
    "auto_detail_kept_leak": {
        "fr": "fuite de la cible probable dans le nouveau modèle, l'ancien est conservé",
        "en": "likely target leakage in the new model, previous model kept",
    },
    "auto_detail_skipped": {
        "fr": "le jeu de données n'est plus disponible",
        "en": "dataset no longer available",
    },
    "dataset_not_found": {
        "fr": "Jeu de données introuvable dans les sources autorisées : {dataset}.{hint}",
        "en": "Dataset not found in authorized sources: {dataset}.{hint}",
    },
    "dataset_ambiguous": {
        "fr": "Plusieurs jeux de données s'appellent '{dataset}' : {value}. "
              "Indiquez le chemin complet avec --dataset.",
        "en": "Several datasets are named '{dataset}': {value}. "
              "Pass the full path with --dataset.",
    },
    "dataset_hint": {
        "fr": " Jeux de données disponibles : {value}",
        "en": " Available datasets: {value}",
    },
    "column_not_found": {
        "fr": "Colonne {kind} '{column}' introuvable dans le jeu de données. "
              "Colonnes disponibles : {columns}",
        "en": "{kind_cap} column '{column}' not found in dataset. Available columns: {columns}",
    },
    "column_kind_target": {"fr": "cible", "en": "target"},
    "config_invalid_yaml": {
        "fr": "YAML invalide dans {path} : {detail}",
        "en": "Invalid YAML in {path}: {detail}",
    },
    "config_not_mapping": {
        "fr": "{path} doit contenir un dictionnaire (clé: valeur) au premier niveau.",
        "en": "{path} must contain a mapping at top level.",
    },
    "config_invalid_config": {
        "fr": "Configuration invalide dans {path} : {detail}",
        "en": "Invalid configuration in {path}: {detail}",
    },
    "config_invalid_sources": {
        "fr": "Fichier de sources invalide {path} : {detail}",
        "en": "Invalid sources file {path}: {detail}",
    },
    "training_not_enough_rows": {
        "fr": "Pas assez de lignes pour entraîner ({n}) ; il en faut au moins 20",
        "en": "Not enough rows to train ({n}); at least 20 are needed",
    },
    "training_no_features": {
        "fr": "Aucune colonne utilisable comme variable explicative",
        "en": "No usable feature columns found",
    },
    "training_cv_failed": {
        "fr": "La validation croisée a échoué : jeu de données trop petit ou dégénéré",
        "en": "Cross-validation failed: dataset too small or degenerate",
    },
    "target_no_values": {
        "fr": "La colonne cible '{column}' ne contient aucune valeur",
        "en": "Target column '{column}' has no values",
    },
    "target_single_value": {
        "fr": "La colonne cible '{column}' a moins de 2 valeurs distinctes",
        "en": "Target column '{column}' has fewer than 2 distinct values",
    },
    "target_unique_values": {
        "fr": "Chaque valeur de la colonne cible '{column}' est unique (un identifiant ?) : "
              "choisissez une colonne dont les valeurs se répètent",
        "en": "Every value of target column '{column}' is unique (an identifier?): "
              "pick a column whose values repeat",
    },
    "target_target_is_date": {
        "fr": "La colonne cible '{column}' contient des dates : choisissez une colonne à "
              "prédire (montant, quantité…) et passez la date avec --date-column",
        "en": "Target column '{column}' contains dates: pick a column to predict "
              "(amount, quantity…) and pass the date with --date-column",
    },
    "target_not_a_date": {
        "fr": "La colonne '{column}' ne contient pas de dates : choisissez une colonne de date "
              "pour --date-column",
        "en": "Column '{column}' does not contain dates: pick a date column for --date-column",
    },
    "column_kind_date": {"fr": "de date", "en": "date"},
    "llm_missing": {
        "fr": "Modèle non installé : lancez `mide models pull` ({value}).",
        "en": "Model not installed: run `mide models pull` ({value}).",
    },
}


def _cli_language(config_dir: Path | None) -> str:
    """Language of the CLI messages; ``fr`` when the config cannot be read."""
    try:
        language = load_config(config_dir, create_app_dir=False).language
    except Exception:  # noqa: BLE001 - a broken config must not block source management
        return _default_yaml_language(config_dir)
    return _language_of(language)


def _default_yaml_language(config_dir: Path | None) -> str:
    """``language`` read from ``default.yaml`` alone (another config file may be broken)."""
    import yaml

    from mide.config import DEFAULT_CONFIG_DIR

    path = (Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR) / "default.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - unreadable file: French default
        return "fr"
    language = data.get("language") if isinstance(data, dict) else None
    return _language_of(language) if isinstance(language, str) else "fr"


def _authorized_sources(config_dir: Path | None, language: str) -> list[str]:
    """Authorized sources; a broken ``sources.yaml`` prints a clear error and exits 1."""
    try:
        return list_sources(config_dir)
    except ConfigError as exc:
        _echo_error(exc, language)
        raise typer.Exit(1) from exc


def _warn_missing_sources(sources: list[str], language: str) -> None:
    """Print a localized warning (stderr) for each authorized file, folder or SQLite database
    that no longer exists."""
    for source in sources:
        if source_missing(source):
            typer.echo(_sources_msg("source_missing", language, value=source), err=True)


def _language_of(language: str) -> str:
    return language if language in ("fr", "en") else "fr"


def _sources_msg(key: str, language: str, **values: str) -> str:
    template = SOURCES_MESSAGES[key][language]
    if language == "fr":
        template = french_spacing(template)
    return template.format(**values)


def _task_line(info: TaskInfo, language: str) -> str:
    """The "Task: <task> - <reason>" line of ``mide train`` in ``language``.

    Unknown task types or reason codes fall back to the raw value / English reason.
    """
    task_key = f"task_{info.task.value}"
    task = (_sources_msg(task_key, language) if task_key in SOURCES_MESSAGES
            else info.task.value)
    reason_key = f"reason_{info.reason_code}"
    reason = info.reason
    if info.reason_code and reason_key in SOURCES_MESSAGES:
        reason = _sources_msg(reason_key, language, n=str(info.n_classes),
                              date=str(info.date_column))
    return _sources_msg("train_task", language, task=task, reason=reason)


def _error_text(exc: BaseException, language: str) -> str:
    """Text of ``exc`` in ``language``: coded target/training/config errors and missing
    optional dependencies are localized."""
    if isinstance(exc, TrainingError) and f"training_{exc.code}" in SOURCES_MESSAGES:
        return _sources_msg(f"training_{exc.code}", language, n=str(exc.n_rows))
    if isinstance(exc, TargetError) and f"target_{exc.code}" in SOURCES_MESSAGES:
        return _sources_msg(f"target_{exc.code}", language, column=exc.column)
    if isinstance(exc, MissingDependencyError):
        return friendly_message(exc, language)
    if isinstance(exc, ConfigError) and f"config_{exc.code}" in SOURCES_MESSAGES:
        return _sources_msg(f"config_{exc.code}", language, path=str(exc.path),
                            detail=exc.detail)
    return str(exc)


def _echo_error(exc: BaseException, language: str) -> None:
    """Print ``exc`` on stderr behind the "Erreur :" / "Error:" prefix of ``language``."""
    lang = _language_of(language)
    typer.echo(_sources_msg("error", lang, value=_error_text(exc, lang)), err=True)


@sources_app.command("add")
def sources_add(source: str, config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Authorize a folder, file or SQL URL."""
    language = _cli_language(config_dir)
    try:
        value = add_source(source, config_dir)
    except ConfigError as exc:
        _echo_error(exc, language)
        raise typer.Exit(1) from exc
    except EmptySource as exc:
        typer.echo(_sources_msg("empty_source", language), err=True)
        raise typer.Exit(1) from exc
    except FileNotFoundError as exc:
        typer.echo(_sources_msg("missing_path", language, value=source.strip()), err=True)
        raise typer.Exit(1) from exc
    except SourceCovered as exc:
        typer.echo(_sources_msg("covered", language, value=exc.path, folder=exc.folder))
        return
    except ValueError as exc:
        typer.echo(_sources_msg("password", language), err=True)
        raise typer.Exit(1) from exc
    typer.echo(_sources_msg("added", language, value=value))


@sources_app.command("list")
def sources_list(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List authorized sources."""
    language = _cli_language(config_dir)
    sources = _authorized_sources(config_dir, language)
    if not sources:
        typer.echo(_sources_msg("none", language))
    for src in sources:
        typer.echo(src)


@sources_app.command("remove")
def sources_remove(source: str, config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Revoke an authorized source."""
    language = _cli_language(config_dir)
    try:
        removed = remove_source(source, config_dir)
    except ConfigError as exc:
        _echo_error(exc, language)
        raise typer.Exit(1) from exc
    if not removed:
        listed = _authorized_sources(config_dir, language)
        hint = (
            _sources_msg("listed", language, value=", ".join(listed))
            if listed else _sources_msg("none", language)
        )
        typer.echo(_sources_msg("not_listed", language, value=source, hint=hint), err=True)
        raise typer.Exit(1)
    typer.echo(_sources_msg("removed", language, value=source.strip()))


@app.command()
def scan(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Show the catalog of datasets found in the authorized sources."""
    language = _cli_language(config_dir)
    sources = _authorized_sources(config_dir, language)
    if not sources:
        typer.echo(_sources_msg("none_hint", language))
        return
    _warn_missing_sources(sources, language)
    for entry in build_catalog(sources):
        if entry.error:
            typer.echo(_sources_msg("item_error", language, item=entry.item, message=entry.error))
            continue
        size = "" if entry.rows is None else _sources_msg(
            "scan_size", language, rows=_num(entry.rows, language, ","),
            cols=str(entry.n_columns),
        )
        typer.echo(f"[{entry.kind}] {entry.item}{size}")
        if entry.profile:
            if entry.profile.date_columns:
                value = ", ".join(entry.profile.date_columns)
                typer.echo(_sources_msg("scan_dates", language, value=value))
            if entry.profile.target_candidates:
                value = ", ".join(entry.profile.target_candidates)
                typer.echo(_sources_msg("scan_targets", language, value=value))


models_app = typer.Typer(help="Manage local LLM weights.", no_args_is_help=True)
app.add_typer(models_app, name="models")


def _num(value: float, language: str, spec: str = "") -> str:
    """Format ``value`` with ``spec``, in the French number format when ``language`` is fr.

    '17,037' -> '17 037', '313.4' -> '313,4', '31%' -> '31 %' (non-breaking spaces)."""
    text = format(value, spec)
    return french_numbers(text) if language == "fr" else text


def _fmt_size(size: int | None, language: str = "en") -> str:
    unit = "Go" if language == "fr" else "GB"
    return "?" if size is None else f"{_num(size / 1e9, language, '.2f')} {unit}"


@models_app.command("list")
def models_list(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List the models of each hardware profile and whether they are installed."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    language = _language_of(cfg.language)
    for info in list_models(cfg.models.profiles, cfg.app_dir / "models"):
        key = "models_installed" if info.installed else "models_not_installed"
        state = _sources_msg(key, language)
        typer.echo(f"{info.profile}: {info.repo}/{info.file} [{state}]")


@models_app.command("trained")
def models_trained(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """List the models trained by `mide train`."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    language = _language_of(cfg.language)
    records = list_trained_models(cfg.app_dir / "models_trained")
    if not records:
        typer.echo(_sources_msg("no_models_hint", language))
        return
    for r in records:
        typer.echo(_trained_line(r.name, r.version, r.metadata, language))
        if r.metadata.get("leakage_suspects"):
            typer.echo("  " + _leak_line(str(r.metadata.get("target")),
                                         list(r.metadata["leakage_suspects"]), language))


def _trained_line(name: str, version: int, meta: dict[str, Any], language: str) -> str:
    """One line of ``mide models trained`` in ``language`` (task names localized)."""
    task_key = f"task_{meta.get('task')}"
    task = (_sources_msg(task_key, language) if task_key in SOURCES_MESSAGES
            else str(meta.get("task")))
    metric = str(meta.get("primary_metric"))
    score = meta.get("metrics", {}).get(metric)
    score_text = _num(score, language, ".4g") if isinstance(score, int | float) else "?"
    beats = _sources_msg("yes" if meta.get("beats_baseline") else "no", language)
    return _sources_msg("trained_line", language, name=name, version=str(version), task=task,
                        target=str(meta.get("target")), metric=metric, score=score_text,
                        beats=beats)


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
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    language = _language_of(cfg.language)
    name = profile.strip().lower() if profile and profile.strip() else profile_hardware().profile
    models = cfg.models.profiles.get(name)  # type: ignore[call-overload]
    if models is None:
        configured = ", ".join(cfg.models.profiles) or _sources_msg("models_none", language)
        typer.echo(
            _sources_msg("models_no_profile", language, name=name, configured=configured),
            err=True,
        )
        raise typer.Exit(1)

    def confirm(url: str, size: int | None) -> bool:
        if yes:
            return True
        return typer.confirm(
            _sources_msg("models_confirm", language, url=url, size=_fmt_size(size, language))
        )

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
        _echo_error(exc, language)
        raise typer.Exit(1) from exc
    typer.echo(_sources_msg("models_ready", language, value=str(path)))


def _get_embedder(cfg: Config) -> Embedder:
    """Load the embedder of the detected hardware profile (patched in tests)."""
    return load_embedder(cfg, profile_hardware().profile)


@app.command("index")
def index_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Index the authorized sources (only new or modified files are processed)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    sources = list_sources(config_dir)
    if not sources:
        typer.echo(_sources_msg("none_hint", _language_of(cfg.language)))
        return
    _warn_missing_sources(sources, _language_of(cfg.language))
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
        _echo_error(exc, _language_of(cfg.language))
        raise typer.Exit(1) from exc
    language = _language_of(cfg.language)
    typer.echo(
        _sources_msg(
            "index_done",
            language,
            new=str(len(report.new_items)),
            updated=str(len(report.updated_items)),
            unchanged=str(len(report.unchanged_items)),
            removed=str(len(report.removed_items)),
            chunks=str(report.new_chunks),
        )
    )
    for item, message in report.errors.items():
        typer.echo(_sources_msg("item_error", language, item=item, message=message))


def dataset_label(item: str, source: str) -> str:
    """Short, path-free name of a dataset item: file stem, ``file.xlsx::sheet`` or table."""
    if is_url(source):
        return item
    path, sheet = split_item(item)
    return Path(item).name if sheet else Path(path).stem


def _dataset_connector(source: str, sources: list[str]) -> SQLConnector | TabularConnector | None:
    """Connector for an authorized source, or ``None`` when the source is missing."""
    if source_missing(source):
        return None
    if is_url(source):
        return SQLConnector(source, sources)
    if not Path(source).expanduser().exists():
        return None
    return TabularConnector(source, sources)


def _read_item(source: str, sources: list[str], item: str):
    conn = _dataset_connector(source, sources)
    assert conn is not None
    try:
        return conn.read(item)
    finally:
        if isinstance(conn, SQLConnector):
            conn.close()


def _load_dataset(dataset: str, sources: list[str], language: str = "fr"):
    """Read one authorized dataset, matched by full item name or file/table name.

    Returns ``(item, label, frame)``. A full item name always wins; a short name that
    matches several datasets is refused instead of silently taking the first one.
    Errors are written in ``language`` (``fr`` or ``en``).
    """
    names: list[str] = []
    matches: dict[str, str] = {}  # item -> source
    for source in sources:
        conn = _dataset_connector(source, sources)
        if conn is None:
            continue
        try:
            items = conn.discover()
        finally:
            if isinstance(conn, SQLConnector):
                conn.close()
        for item in items:
            if dataset == item:
                return item, dataset_label(item, source), _read_item(source, sources, item)
            base = item if is_url(source) else Path(split_item(item)[0]).stem
            if dataset in (base, Path(item).name):
                matches.setdefault(item, source)
            names.append(base)
    lang = _language_of(language)
    if len(matches) > 1:
        raise ValueError(_sources_msg(
            "dataset_ambiguous", lang, dataset=dataset, value=", ".join(matches)))
    if matches:
        item, source = next(iter(matches.items()))
        return item, dataset_label(item, source), _read_item(source, sources, item)
    hint = (_sources_msg("dataset_hint", lang, value=", ".join(sorted(set(names))))
            if names else "")
    raise ValueError(_sources_msg("dataset_not_found", lang, dataset=dataset, hint=hint))


def _match_column(df, column: str | None) -> str | None:
    """``column`` as spelled in ``df``: exact name first, then without stray spaces."""
    if column is None or column in df.columns:
        return column
    stripped = column.strip()
    return stripped if stripped in df.columns else column


def _check_columns(df, target: str, date_column: str | None, language: str) -> None:
    """Raise a ``ValueError`` in ``language`` when ``target`` or ``date_column`` is missing."""
    lang = _language_of(language)
    columns = ", ".join(str(c) for c in df.columns)
    for kind, column in (("target", target), ("date", date_column)):
        if column is None or column in df.columns:
            continue
        label = _sources_msg(f"column_kind_{kind}", lang)
        raise ValueError(_sources_msg(
            "column_not_found", lang, kind=label, kind_cap=label.capitalize(),
            column=column, columns=columns,
        ))


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
        item, label, df = _load_dataset(dataset.strip(), list_sources(config_dir), cfg.language)
        target = _match_column(df, target) or target
        date_column = _match_column(df, date_column) or None
        _check_columns(df, target, date_column, cfg.language)
        result = train_model(
            df, target, profile=profile_hardware().profile, seed=seed, date_column=date_column
        )
        metrics = evaluate(result, df)
        record = save_model(
            result,
            cfg.app_dir / "models_trained",
            f"{label}-{target}",
            {"evaluation": metrics, "dataset": label, "item": item,
             "data_hash": fingerprint(df)},
        )
    except Exception as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    language = _language_of(cfg.language)
    typer.echo(_task_line(result.task, language))
    typer.echo(_sources_msg(
        "train_saved", language, name=record.name, version=str(record.version)
    ))
    for key, value in result.metrics.items():
        typer.echo(_sources_msg(
            "train_cv", language, metric=key, value=_num(value, language, ".4g"),
            baseline=_num(result.baseline_metrics[key], language, ".4g"),
        ))
    typer.echo(_sources_msg("train_beats" if result.beats_baseline else "train_not_beats",
                            language))
    top = ", ".join(f"{k} ({_num(v, language, '.0%')})"
                    for k, v in list(result.feature_importance.items())[:5])
    typer.echo(_sources_msg("train_top", language, value=top))
    if result.leakage_suspects:
        typer.echo(_leak_line(target, result.leakage_suspects, language))


def _get_llm(cfg: Config) -> LLM:
    """Load the local LLM of the detected profile (patched in tests)."""
    report = profile_hardware()
    spec = cfg.models.profiles[report.profile].llm  # type: ignore[index]
    path = model_path(cfg.app_dir / "models", spec)
    if not path.exists():
        raise DownloadError(
            _sources_msg("llm_missing", _language_of(cfg.language), value=path.name))
    return load_llm(path, report)


def _load_all_datasets(sources: list[str]) -> dict:
    """Read every tabular dataset of the authorized sources (read-only)."""
    frames: dict = {}
    for source in sources:
        try:
            conn: SQLConnector | TabularConnector
            if source_missing(source):
                continue
            if is_url(source):
                conn = SQLConnector(source, sources)
            elif Path(source).expanduser().exists():
                conn = TabularConnector(source, sources)
            else:
                continue
            try:
                for item in conn.discover():
                    try:
                        frames[item] = conn.read(item)
                    except Exception as exc:  # noqa: BLE001 - unreadable item: skip it
                        logger.debug("Skipping %s: %s", item, type(exc).__name__)
            finally:
                if isinstance(conn, SQLConnector):
                    conn.close()
        except Exception as exc:  # noqa: BLE001 - unreachable source: skip it
            logger.debug("Skipping a source: %s", type(exc).__name__)
    return frames


class EmptyIndexError(Exception):
    """The vector index is empty and no business data can answer."""


class EmptyQuestionError(ValueError):
    """The question is blank, so there is nothing to answer."""


class UnknownSourceError(ValueError):
    """``--source`` names no indexed item, so the search would find nothing."""


def _check_source(store: VectorStore, source: str | None, language: str) -> str | None:
    """Return the indexed item ``source`` names, or fail clearly listing the valid ones.

    An exact match wins; otherwise surrounding spaces (copy-paste) are ignored.
    A blank ``source`` means "no filter" and returns ``None``.
    """
    if source is None or not source.strip():
        return None
    items = store.items()
    for candidate in (source, source.strip()):
        if candidate in items:
            return candidate
    if language == "fr":
        hint = (f"Sources indexées{NBSP}: {', '.join(items)}" if items
                else "Index vide. Lancez `mide index`.")
        raise UnknownSourceError(f"Source non indexée{NBSP}: {source}. {hint}")
    hint = f"Indexed sources: {', '.join(items)}" if items else "Empty index. Run `mide index`."
    raise UnknownSourceError(f"Source not indexed: {source}. {hint}")


def _no_llm_note(reason: str, language: str) -> str:
    """Answer shown when no LLM is installed but business figures are available."""
    reason = reason.rstrip(".")
    if language == "fr":
        return (f"LLM local indisponible ({reason}). Voici les chiffres calculés, "
                "sans recommandation rédigée.")
    return f"Local LLM unavailable ({reason}). Here are the computed figures, without written advice."


def ask_answer(question: str, config_dir: Path | None = None, source: str | None = None,
               top_k: int = 5) -> tuple[str, str, str]:
    """Answer a question; returns (answer, figures used, sources footer)."""
    cfg = load_config(config_dir)
    if not question.strip():
        raise EmptyQuestionError(
            french_spacing("Question vide. Exemple : mide ask \"Quels produits se vendent le mieux ?\"")
            if cfg.language == "fr"
            else "Empty question. Example: mide ask \"Which products sell best?\"")
    if source is not None:
        source = _check_source(VectorStore(cfg.app_dir / "index"), source, cfg.language)
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
    try:
        llm = _get_llm(cfg)
    except (DownloadError, LLMError) as exc:
        if not findings:
            raise
        # Graceful degradation: the figures are computed without the LLM.
        note = _no_llm_note(_error_text(exc, _language_of(cfg.language)), cfg.language)
        rec = Recommendation(note, findings, passages)
        return rec.text, rec.data_used(cfg.language), sources_footer(passages)
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
    source: str | None = typer.Option(None, help="Restrict to one indexed item (its full path)."),
    top_k: int = typer.Option(5, "--top-k", "-k", min=1, help="Number of excerpts."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Answer a question: documents (RAG), business modules, or both (agent)."""
    try:
        answer, used, footer = ask_answer(question, config_dir, source, top_k)
    except (ConfigError, DownloadError, EmbeddingError, EmptyIndexError, EmptyQuestionError,
            LLMError, UnknownSourceError) as exc:
        plain = isinstance(exc, EmptyIndexError | EmptyQuestionError | UnknownSourceError)
        if plain:
            typer.echo(str(exc), err=True)
        else:
            _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    typer.echo(answer)
    if used:
        typer.echo("\n" + used)
    if footer:
        typer.echo("\n" + footer)


def _dashboard_script() -> Path:
    """Path of the Streamlit dashboard script (patched in tests)."""
    return Path(__file__).resolve().parent.parent / "app" / "dashboard.py"


@app.command("ui")
def ui_command(
    port: int = typer.Option(8501, help="Port of the dashboard."),
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    r"""Launch the Streamlit dashboard (needs `pip install mide-engine\[ui]`)."""
    import importlib.util
    import os
    import subprocess
    import sys

    from mide.dashboard_data import CONFIG_ENV

    language = _cli_language(config_dir)
    if importlib.util.find_spec("streamlit") is None:
        typer.echo(_sources_msg("ui_no_streamlit", language), err=True)
        raise typer.Exit(1)
    script = _dashboard_script()
    if not script.exists():
        typer.echo(_sources_msg("ui_no_dashboard", language, value=str(script)), err=True)
        raise typer.Exit(1)
    env = dict(os.environ)
    if config_dir is not None:
        env[CONFIG_ENV] = str(config_dir.resolve())
    cmd = [sys.executable, "-m", "streamlit", "run", str(script), "--server.port", str(port),
           "--browser.gatherUsageStats", "false"]
    raise typer.Exit(subprocess.call(cmd, env=env))


REPORT_FORMAT_OPTION = typer.Option("md", "--format", help="md or html.")
REPORT_OUTPUT_OPTION = typer.Option(None, "--output", "-o", help="Output file (default: stdout).")


def _refuse_source_overwrite(output: Path, sources: list[str], language: str) -> None:
    """Exit with an error when ``output`` would overwrite a file of an authorized source."""
    owner = source_owning(output, sources)
    if owner is None:
        return
    if language == "fr":
        msg = (f"Erreur{NBSP}: {output} fait partie de la source autorisée {owner}. "
               f"MIDE ne modifie jamais vos données{NBSP}; choisissez un autre fichier de sortie.")
    else:
        msg = (f"Error: {output} belongs to the authorized source {owner}. "
               "MIDE never modifies your data; choose another output file.")
    typer.echo(msg, err=True)
    raise typer.Exit(1)


@app.command("report")
def report_command(
    fmt: str = REPORT_FORMAT_OPTION,
    output: Path | None = REPORT_OUTPUT_OPTION,
    config_dir: Path | None = CONFIG_DIR_OPTION,
) -> None:
    """Generate the weekly report (KPIs, forecasts, alerts, 3 priority actions)."""
    from mide.report import build_report, render_html, render_markdown

    fmt = fmt.strip().lower()
    if fmt not in ("md", "html"):
        typer.echo(_sources_msg("report_format", _cli_language(config_dir)), err=True)
        raise typer.Exit(2)
    cfg = load_config(config_dir)
    sources = list_sources(config_dir)
    if output is not None:
        _refuse_source_overwrite(output, sources, cfg.language)
    tables = detect_tables(_load_all_datasets(sources))
    report = build_report(tables, cfg.language)
    text = render_html(report) if fmt == "html" else render_markdown(report)
    if output is None:
        typer.echo(text)
    else:
        output.write_text(text, encoding="utf-8")
        typer.echo(_sources_msg("report_written", _language_of(cfg.language), value=str(output)))


@app.command("auto")
def auto_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Scan, index incrementally, retrain changed models (kept only if better), report."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    sources = list_sources(config_dir)
    if not sources:
        typer.echo(_sources_msg("none_hint", _language_of(cfg.language)))
        return
    language = _language_of(cfg.language)
    _warn_missing_sources(sources, language)
    report = AutoReport(n_datasets=len(build_catalog(sources)))
    try:
        try:
            embedder = _get_embedder(cfg)
        except EmbeddingError as exc:
            # Graceful degradation: without the `rag` extra, still retrain the models.
            report.index_summary = _sources_msg(
                "auto_index_skipped", language, value=_error_text(exc, language).rstrip(".")
            )
        else:
            idx = index_sources(
                sources,
                cfg.app_dir / "index",
                embedder,
                cfg.general.chunk_size,
                cfg.general.chunk_overlap,
                cfg.general.max_file_size_mb,
            )
            report.index_summary = _sources_msg(
                "auto_index_counts",
                language,
                new=str(len(idx.new_items)),
                updated=str(len(idx.updated_items)),
                unchanged=str(len(idx.unchanged_items)),
                removed=str(len(idx.removed_items)),
            )
        report.outcomes = retrain_if_changed(
            _load_all_datasets(sources),
            cfg.app_dir / "models_trained",
            cfg.app_dir / "auto_state.json",
            profile=profile_hardware().profile,
        )
    except Exception as exc:
        _echo_error(exc, language)
        raise typer.Exit(1) from exc
    typer.echo(_sources_msg("auto_scan", language, value=str(report.n_datasets)))
    typer.echo(_sources_msg("auto_index", language, value=report.index_summary))
    if not report.outcomes:
        typer.echo(_sources_msg("no_models_hint", language))
    for o in report.outcomes:
        typer.echo(_auto_outcome_line(o, language))
        if o.leakage_suspects:
            typer.echo(_leak_line(o.target, o.leakage_suspects, language))


def _leak_line(target: str, suspects: list[str], language: str) -> str:
    """Target-leakage warning naming the suspect columns, in ``language``."""
    return _sources_msg("train_leak", language, target=target, columns=", ".join(suspects))


def _auto_outcome_line(outcome: ModelOutcome, language: str) -> str:
    """One `mide auto` model line; status and known details follow ``language``."""
    status_key = f"auto_{outcome.status}"
    status = (
        _sources_msg(status_key, language) if status_key in SOURCES_MESSAGES else outcome.status
    )
    line = _sources_msg("auto_model", language, name=outcome.name, status=status)
    if outcome.new_score is not None:
        old, new = outcome.old_score, outcome.new_score
        old_text = "?" if old is None else _num(old, language, ".4g")
        line += f" ({old_text} -> {_num(new, language, '.4g')})"
    detail_key = f"auto_detail_{outcome.status}"
    # Error details are exception texts: they are shown as they are.
    detail = (
        _sources_msg(detail_key, language) if detail_key in SOURCES_MESSAGES else outcome.detail
    )
    return f"{line} {detail}".rstrip()




@app.command("chat")
def chat_command(
    source: str | None = typer.Option(None, help="Restrict to one indexed item (its full path)."),
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
        try:
            source = _check_source(store, source, cfg.language)
        except UnknownSourceError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        retriever = Retriever(store, _get_embedder(cfg), top_k)
        llm = _get_llm(cfg)
    except (ConfigError, DownloadError, EmbeddingError, LLMError) as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    history = ChatHistory()
    typer.echo(
        "Posez vos questions (`exit` pour quitter, `/clear` pour oublier)."
        if cfg.language == "fr"
        else "Ask your questions (`exit` to quit, `/clear` to forget)."
    )
    try:
        _chat_loop(cfg.language, history, retriever, llm, source)
    except KeyboardInterrupt:
        typer.echo("\n" + ("Au revoir." if cfg.language == "fr" else "Goodbye."))


def _chat_loop(
    language: str, history: ChatHistory, retriever: Retriever, llm: Any, source: str | None
) -> None:
    """Read questions until `exit` or end of input; Ctrl+C is handled by the caller."""
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            break
        command = question.lower()
        if command in {"exit", "quit", "/exit", "/quit"}:
            break
        if command == "/clear":
            history.clear()
            continue
        if not question:
            continue
        passages = retriever.retrieve(question, source=source)
        prompt = build_rag_prompt(question, passages, language, history.render(language))
        answer = llm.generate(prompt, max_tokens=512, temperature=0.2).strip()
        history.add(question, answer)
        typer.echo(answer)
        footer = sources_footer(passages)
        if footer:
            typer.echo("\n" + footer)


@app.command("finetune")
def finetune_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Optional LoRA fine-tuning on company documents (GPU only; otherwise RAG is used)."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    hw = profile_hardware()
    spec = cfg.models.profiles.get(hw.profile)  # type: ignore[call-overload]
    allows = bool(spec and spec.lora)
    reason = unavailable_reason(hw, allows, cfg.language)
    if reason:
        typer.echo(reason)
        return
    docs = load_documents(list_sources(config_dir), cfg.general.max_file_size_mb)
    try:
        llm = _get_llm(cfg)
    except DownloadError as exc:
        _echo_error(exc, cfg.language)
        raise typer.Exit(1) from exc
    base = spec.llm.repo.replace("-GGUF", "")  # type: ignore[union-attr]
    res = finetune(hw, allows, docs, llm, cfg.app_dir / "lora", peft_trainer(base),
                   lambda holdout, adapter: 0.0, cfg.language)
    typer.echo(res.message)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Show version."
    ),
) -> None:
    """MIDE Engine command line."""


@app.command("privacy")
def privacy_command(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Show what MIDE reads, what it stores locally, and its network policy."""
    try:
        cfg = load_config(config_dir)
    except ConfigError as exc:
        _echo_error(exc, _cli_language(config_dir))
        raise typer.Exit(1) from exc
    typer.echo(build_privacy_report(cfg, config_dir).to_text(cfg.language))


@app.command()
def doctor(config_dir: Path | None = CONFIG_DIR_OPTION) -> None:
    """Check that the installation works and show the hardware report."""
    report = profile_hardware()
    lang = _cli_language(config_dir)
    gpu = (
        _sources_msg("doctor_gpu_vram", lang, name=report.gpu.name,
                     vram=_num(report.gpu.vram_gb, lang))
        if report.gpu
        else _sources_msg("doctor_gpu_none", lang)
    )
    typer.echo("OK")
    typer.echo(_sources_msg("doctor_ram", lang, value=_num(report.ram_gb, lang)))
    typer.echo(_sources_msg("doctor_cpu", lang, value=str(report.cpu_cores)))
    typer.echo(_sources_msg("doctor_os", lang, value=report.os_name))
    typer.echo(_sources_msg("doctor_gpu", lang, value=gpu))
    typer.echo(_sources_msg("doctor_disk", lang, value=_num(report.disk_free_gb, lang)))
    typer.echo(_sources_msg("doctor_profile", lang, value=report.profile))


def run() -> None:
    """Console entry point: runs the CLI and turns unexpected errors into clear messages."""
    from mide.utils.errors import run_safely

    try:
        language = load_config().language
    except Exception:  # noqa: BLE001 - config may be what is broken
        language = _default_yaml_language(None)
    raise SystemExit(run_safely(app, language))


if __name__ == "__main__":
    run()
