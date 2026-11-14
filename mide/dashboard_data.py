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


def sales_view(df: pd.DataFrame) -> dict:
    """Forecast, product ranking, trend and seasonality for the sales page."""
    forecast = sales.forecast_sales(df)
    return {
        "forecast": forecast,
        "products": sales.product_ranking(df, n=5),
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
