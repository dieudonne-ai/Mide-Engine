"""Data layer of the Streamlit dashboard (no Streamlit import: fully testable)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from mide.agent.decision import BusinessData, detect_tables
from mide.automl.registry import list_models as list_trained_models
from mide.business import customers, insights, marketing, sales
from mide.config import Config, load_config
from mide.connectors.sources import list_sources
from mide.hardware.profiler import HardwareReport, profile_hardware
from mide.llm.downloader import list_models

CONFIG_ENV = "MIDE_CONFIG_DIR"


def config_error_message(exc: BaseException, config_dir: Path | None) -> str:
    """Dashboard text of a config error, in the ``language`` of ``default.yaml``."""
    from mide.cli import SOURCES_MESSAGES, _default_yaml_language, _error_text

    language = _default_yaml_language(config_dir)
    value = _error_text(exc, language)
    return SOURCES_MESSAGES["dashboard_config_error"][language].format(value=value)


PAGE_KEYS = ["home", "sales", "customers", "marketing", "ask", "sources", "hardware"]

UI_TEXT: dict[str, dict[str, str]] = {
    "page_home": {"fr": "Accueil", "en": "Home"},
    "page_sales": {"fr": "Ventes", "en": "Sales"},
    "page_customers": {"fr": "Clients", "en": "Customers"},
    "page_marketing": {"fr": "Marketing", "en": "Marketing"},
    "page_ask": {"fr": "Poser une question", "en": "Ask a question"},
    "page_sources": {"fr": "Sources de données", "en": "Data sources"},
    "page_hardware": {"fr": "Matériel & modèles", "en": "Hardware & models"},
    "sidebar_page": {"fr": "Page", "en": "Page"},
    "refresh": {"fr": "Actualiser les données", "en": "Refresh data"},
    "loading": {"fr": "Chargement des données...", "en": "Loading data..."},
    "no_data": {
        "fr": "Aucune donnée {what} trouvée. Ajoutez une source dans la page *{page}*.",
        "en": "No {what} data found. Add a source in the *{page}* page.",
    },
    "what_sales": {"fr": "de ventes", "en": "sales"},
    "what_customers": {"fr": "clients", "en": "customer"},
    "what_marketing": {"fr": "marketing", "en": "marketing"},
    "revenue": {"fr": "Chiffre d'affaires", "en": "Revenue"},
    "orders": {"fr": "Commandes", "en": "Orders"},
    "avg_order": {"fr": "Panier moyen", "en": "Average order"},
    "last_30d": {"fr": "30 derniers jours", "en": "Last 30 days"},
    "anomalies": {"fr": "Anomalies", "en": "Anomalies"},
    "no_anomaly": {"fr": "Aucun jour anormal détecté.", "en": "No abnormal day detected."},
    "forecast": {"fr": "Prévision {h} j", "en": "Forecast {h} d"},
    "monthly_revenue": {"fr": "Chiffre d'affaires mensuel", "en": "Monthly revenue"},
    "trend": {"fr": "Tendance : {value}", "en": "Trend: {value}"},
    "trend_up": {"fr": "hausse", "en": "up"},
    "trend_down": {"fr": "baisse", "en": "down"},
    "trend_flat": {"fr": "stable", "en": "flat"},
    "seasonality": {
        "fr": "Mois le plus fort : **{peak}**, le plus faible : **{trough}**, "
              "meilleur jour : **{weekday}**",
        "en": "Peak month: **{peak}**, trough: **{trough}**, best weekday: **{weekday}**",
    },
    "top_products": {"fr": "Meilleurs produits", "en": "Top products"},
    "flop_products": {"fr": "Produits les plus faibles", "en": "Flop products"},
    "rfm_segments": {"fr": "Segments RFM", "en": "RFM segments"},
    "revenue_at_risk": {"fr": "Chiffre d'affaires à risque", "en": "Revenue at risk"},
    "high_risk": {"fr": "{n} clients à risque élevé", "en": "{n} high-risk customers"},
    "reallocation": {"fr": "Réallocation de budget suggérée",
                     "en": "Suggested budget reallocation"},
    "no_reallocation": {"fr": "Aucune réallocation nécessaire.",
                        "en": "No reallocation needed."},
    "move": {
        "fr": "- {src} → {dst} : **{amount}** ({reason} ; jusqu'à +{extra} de chiffre "
              "d'affaires, borne haute linéaire)",
        "en": "- {src} → {dst}: **{amount}** ({reason}; up to +{extra} revenue, "
              "linear upper bound)",
    },
    "your_question": {"fr": "Votre question", "en": "Your question"},
    "thinking": {"fr": "Réflexion...", "en": "Thinking..."},
    "sources_caption": {"fr": "MIDE ne lit que les sources listées ici (lecture seule).",
                        "en": "MIDE only reads the sources listed here (read-only)."},
    "remove": {"fr": "Retirer", "en": "Remove"},
    "add_prompt": {"fr": "Ajouter un dossier, un fichier ou une URL SQL",
                   "en": "Add a folder, file or SQL URL"},
    "add": {"fr": "Ajouter", "en": "Add"},
    "datasets": {"fr": "Jeux de données", "en": "Datasets"},
    "dataset_line": {"fr": "**{name}** - {rows} lignes x {cols} colonnes",
                     "en": "**{name}** - {rows} rows x {cols} columns"},
    "gpu_none": {"fr": "aucun", "en": "none"},
    "hardware_line": {
        "fr": "RAM {ram} Go - {cores} cœurs - {os} - GPU : {gpu} - disque libre {disk} Go",
        "en": "RAM {ram} GB - {cores} cores - {os} - GPU: {gpu} - disk free {disk} GB",
    },
    "gpu_vram": {"fr": "{name} ({vram} Go)", "en": "{name} ({vram} GB)"},
    "profile": {"fr": "Profil", "en": "Profile"},
    "llm_weights": {"fr": "Poids du LLM", "en": "LLM weights"},
    "installed": {"fr": "installé", "en": "installed"},
    "not_installed": {"fr": "non installé", "en": "not installed"},
    "trained_models": {"fr": "Modèles entraînés", "en": "Trained models"},
    "trained_line": {"fr": "{name} v{version} [{task}] cible={target}",
                     "en": "{name} v{version} [{task}] target={target}"},
    "no_trained": {"fr": "Aucun pour l'instant. Utilisez `mide train`.",
                   "en": "None yet. Use `mide train`."},
    "anomaly_drop": {"fr": "chute", "en": "drop"},
    "anomaly_spike": {"fr": "pic", "en": "spike"},
    "anomaly_day": {"fr": "le {day}", "en": "on {day}"},
    "anomaly_period": {"fr": "du {start} au {end}", "en": "on {start} -> {end}"},
    "anomaly_line": {"fr": "{kind} {period} : {actual} au lieu de {expected} attendus ({change})",
                     "en": "{kind} {period}: {actual} vs {expected} expected ({change})"},
}


def ui_text(key: str, language: str, **values: object) -> str:
    """Dashboard label ``key`` in ``language`` (``fr`` when unknown), formatted with values."""
    texts = UI_TEXT[key]
    return texts.get(language, texts["fr"]).format(**values)


def anomaly_text(anomaly: insights.Anomaly, language: str) -> str:
    """Dashboard line of an anomaly; in English it equals ``anomaly.describe()``."""
    start, end = anomaly.start.date(), anomaly.end.date()
    period = (ui_text("anomaly_day", language, day=start) if anomaly.start == anomaly.end
              else ui_text("anomaly_period", language, start=start, end=end))
    kind_key = f"anomaly_{anomaly.kind}"
    kind = ui_text(kind_key, language) if kind_key in UI_TEXT else anomaly.kind
    return ui_text("anomaly_line", language, kind=kind, period=period,
                   actual=f"{anomaly.actual:,.0f}", expected=f"{anomaly.expected:,.0f}",
                   change=f"{anomaly.ratio - 1:+.0%}")


def page_labels(language: str) -> dict[str, str]:
    """Sidebar label of each page, keyed by its stable id from ``PAGE_KEYS``."""
    return {key: ui_text(f"page_{key}", language) for key in PAGE_KEYS}


def dashboard_language(config_dir: Path | None) -> str:
    """Language of the dashboard: ``language`` of the config, ``fr`` if unreadable."""
    from mide.cli import _cli_language

    return _cli_language(config_dir)


def config_dir_from_env() -> Path | None:
    """Config folder passed by `mide ui --config-dir` (None = repo default)."""
    value = os.environ.get(CONFIG_ENV)
    return Path(value) if value else None


@dataclass
class DashboardData:
    """Everything the pages need, loaded once from the authorized sources."""

    config: Config
    sources: list[str]
    tables: BusinessData
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def has_sales(self) -> bool:
        return self.tables.sales is not None

    @property
    def has_campaigns(self) -> bool:
        return self.tables.campaigns is not None


def load_dashboard_data(config_dir: Path | None = None) -> DashboardData:
    """Load config, authorized sources and the business tables (read-only)."""
    from mide.cli import _load_all_datasets  # local import: cli imports heavy modules

    cfg = load_config(config_dir)
    sources = list_sources(config_dir)
    frames = _load_all_datasets(sources) if sources else {}
    return DashboardData(cfg, sources, detect_tables(frames), frames)


def home_kpis(data: DashboardData) -> insights.InsightReport | None:
    """KPIs and anomalies for the home page, or None without usable sales."""
    if not data.has_sales:
        return None
    try:
        return insights.analyze(data.tables.sales)
    except ValueError:
        return None


def sales_view(df: pd.DataFrame, products: pd.DataFrame | None = None) -> dict:
    """Forecast, product ranking (with names if a catalog is given), trend and seasonality."""
    forecast = sales.forecast_sales(df)
    names = sales.product_names(products) if products is not None else None
    return {
        "forecast": forecast,
        "products": sales.product_ranking(df, n=5, names=names),
        "trend": sales.sales_trend(df),
        "seasonality": sales.detect_seasonality(df),
        "history": sales.daily_series(df),
    }


def customers_view(df: pd.DataFrame) -> dict:
    """RFM segments and churn risk for the customers page."""
    rfm = customers.rfm_segments(df)
    return {
        "segments": customers.segment_summary(rfm),
        "churn": customers.churn_risk(df),
    }


def marketing_view(df: pd.DataFrame) -> dict:
    """Channel performance and budget reallocation for the marketing page."""
    channels = marketing.channel_performance(df)
    return {
        "channels": channels,
        "campaigns": marketing.campaign_performance(df),
        "plan": marketing.suggest_reallocation(channels),
    }


def hardware_view(cfg: Config) -> dict:
    """Hardware report, installed LLM weights and trained models."""
    report: HardwareReport = profile_hardware()
    return {
        "hardware": report,
        "llm": list_models(cfg.models.profiles, cfg.app_dir / "models"),
        "trained": list_trained_models(cfg.app_dir / "models_trained"),
    }
