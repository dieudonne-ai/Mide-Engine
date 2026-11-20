"""Data layer of the Streamlit dashboard (no Streamlit import: fully testable)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

import pandas as pd

from mide.agent.decision import BusinessData, detect_tables, french_numbers
from mide.automl.registry import list_models as list_trained_models
from mide.business import customers, insights, marketing, sales
from mide.config import Config, load_config
from mide.connectors.sources import list_sources
from mide.hardware.profiler import HardwareReport, profile_hardware
from mide.llm.downloader import list_models
from mide.utils.french import french_spacing

if TYPE_CHECKING:  # Styler needs jinja2, altair comes with Streamlit (dashboard-only)
    import altair as alt
    from pandas.io.formats.style import Styler

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
    "move_reason": {
        "fr": "ROI de {src} {roi} contre une médiane de {median} ; {dst} rapporte {roas} "
              "de chiffre d'affaires par unité dépensée",
        "en": "{src} ROI {roi} vs median {median}; {dst} returns {roas} revenue per unit spent",
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


COLUMN_LABELS: dict[str, dict[str, str]] = {
    "product_id": {"fr": "Produit", "en": "Product"},
    "date": {"fr": "Date", "en": "Date"},
    "amount": {"fr": "Chiffre d'affaires", "en": "Revenue"},
    "name": {"fr": "Nom", "en": "Name"},
    "revenue": {"fr": "Chiffre d'affaires", "en": "Revenue"},
    "share_pct": {"fr": "Part (%)", "en": "Share (%)"},
    "segment": {"fr": "Segment", "en": "Segment"},
    "customers": {"fr": "Clients", "en": "Customers"},
    "avg_recency_days": {"fr": "Récence moy. (jours)", "en": "Avg recency (days)"},
    "avg_frequency": {"fr": "Fréquence moy.", "en": "Avg frequency"},
    "revenue_share_pct": {"fr": "Part du CA (%)", "en": "Revenue share (%)"},
    "customer": {"fr": "Client", "en": "Customer"},
    "last_purchase": {"fr": "Dernier achat", "en": "Last purchase"},
    "first_purchase": {"fr": "Premier achat", "en": "First purchase"},
    "frequency": {"fr": "Fréquence", "en": "Frequency"},
    "monetary": {"fr": "Montant total", "en": "Monetary"},
    "recency_days": {"fr": "Récence (jours)", "en": "Recency (days)"},
    "typical_gap_days": {"fr": "Écart habituel (jours)", "en": "Typical gap (days)"},
    "expected_gap_days": {"fr": "Écart attendu (jours)", "en": "Expected gap (days)"},
    "risk": {"fr": "Risque", "en": "Risk"},
    "risk_level": {"fr": "Niveau de risque", "en": "Risk level"},
    "channel": {"fr": "Canal", "en": "Channel"},
    "campaigns": {"fr": "Campagnes", "en": "Campaigns"},
    "spend": {"fr": "Dépenses", "en": "Spend"},
    "impressions": {"fr": "Impressions", "en": "Impressions"},
    "clicks": {"fr": "Clics", "en": "Clicks"},
    "conversions": {"fr": "Conversions", "en": "Conversions"},
    "roi": {"fr": "ROI", "en": "ROI"},
    "roas": {"fr": "ROAS", "en": "ROAS"},
    "cost_per_conversion": {"fr": "Coût par conversion", "en": "Cost per conversion"},
    "conversion_rate": {"fr": "Taux de conversion", "en": "Conversion rate"},
    "ctr": {"fr": "Taux de clic", "en": "CTR"},
}


# Display names of cell values, per column: RFM segments and churn risk levels.
VALUE_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "segment": customers.SEGMENT_LABELS,
    "risk_level": {
        "low": {"fr": "faible", "en": "low"},
        "medium": {"fr": "moyen", "en": "medium"},
        "high": {"fr": "élevé", "en": "high"},
    },
}


def value_label(column: object, value: object, language: str) -> object:
    """Display name of a cell ``value`` of ``column``; unknown values are kept as is."""
    labels = VALUE_LABELS.get(column) if isinstance(column, str) else None
    texts = labels.get(value) if labels is not None and isinstance(value, str) else None
    if texts is None:
        return value
    return texts.get(language, texts["fr"])


def column_label(column: object, language: str) -> object:
    """Display name of a table column in ``language``; unknown columns are kept as is."""
    texts = COLUMN_LABELS.get(column) if isinstance(column, str) else None
    if texts is None:
        return column
    return texts.get(language, texts["fr"])


def display_table(df: pd.DataFrame, language: str) -> pd.DataFrame:
    """Copy of ``df`` with column names, index name and known labels translated for display.

    Numbers are unchanged; only labels listed in ``VALUE_LABELS`` (segments, risk levels)
    are translated, in the columns and in the index.
    """
    out = df.copy()
    for column in out.columns:
        if column in VALUE_LABELS:
            out[column] = out[column].map(lambda v, c=column: value_label(c, v, language))
    if df.index.name in VALUE_LABELS:
        out.index = out.index.map(lambda v: value_label(df.index.name, v, language))
    out = out.rename(columns=lambda c: column_label(c, language))
    out.index = out.index.rename(column_label(df.index.name, language))
    return out


def number_cell(value: object, language: str) -> str:
    """One table cell as text: thousands separator, 2 decimals for floats, French format."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or pd.isna(value):
        return str(value)
    spec = ",.2f" if isinstance(value, float) and not float(value).is_integer() else ",.0f"
    return num(float(value), language, spec)


def table_view(df: pd.DataFrame, language: str) -> pd.DataFrame | Styler:
    """``display_table`` ready for ``st.dataframe``: in French, numbers read '1 735,50'.

    The cell values stay numeric (a Styler only changes their text), so sorting a
    column in the dashboard still sorts by value. English keeps Streamlit's format."""
    out = display_table(df, language)
    if language == "en":
        return out
    numeric = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])
               and not pd.api.types.is_bool_dtype(out[c])]
    return out.style.format(lambda v: number_cell(v, language), subset=numeric)


def chart_series(series: pd.Series, language: str) -> pd.Series:
    """Copy of ``series`` whose name and index name (chart axis labels) are translated.

    Values and index labels are unchanged.
    """
    out = series.rename(column_label(series.name, language))
    out.index = out.index.rename(column_label(series.index.name, language))
    return out


# Vega (d3-format / d3-time-format) locale for French charts: "12 000", "1,5", "janv. 2024".
FRENCH_CHART_LOCALE: dict[str, dict[str, object]] = {
    "number": {
        "decimal": ",",
        "thousands": "\u00a0",
        "grouping": [3],
        "currency": ["", "\u00a0€"],
        "percent": "\u00a0%",
        "minus": "-",
    },
    "time": {
        "dateTime": "%A %e %B %Y à %X",
        "date": "%d/%m/%Y",
        "time": "%H:%M:%S",
        "periods": ["AM", "PM"],
        "days": ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"],
        "shortDays": ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."],
        "months": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                   "août", "septembre", "octobre", "novembre", "décembre"],
        "shortMonths": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
                        "août", "sept.", "oct.", "nov.", "déc."],
    },
}


def season_label(name: str, language: str) -> str:
    """French full name of a ``sales`` month/weekday abbreviation ("Dec" -> "décembre").

    English (and any unknown name) is returned unchanged.
    """
    if language == "en":
        return name
    time = FRENCH_CHART_LOCALE["time"]
    if name in sales.MONTH_NAMES:
        months = cast(list[str], time["months"])
        return months[sales.MONTH_NAMES.index(name)]
    if name in sales.WEEKDAY_NAMES:
        days = cast(list[str], time["days"])  # Vega order starts on Sunday
        return days[(sales.WEEKDAY_NAMES.index(name) + 1) % 7]
    return name


def _one_point_per_month(dates: pd.Series) -> bool:
    """True if no two ``dates`` fall in the same calendar month."""
    months = dates.dt.to_period("M")
    return bool(months.is_unique)


def chart(series: pd.Series, language: str, kind: str = "line") -> alt.Chart:
    """Altair line or bar chart of ``series`` for ``st.altair_chart``.

    Axis titles come from ``chart_series``. Any language other than ``en`` gets the
    French Vega locale, so axes and tooltips read "12 000", "1,5" and "janv." instead
    of "12,000", "1.5" and "Jan". A bar chart of monthly dates gets one band per
    month ("janv. 2024") instead of thin bars on a time axis. Needs altair (installed
    with Streamlit).
    """
    import altair as alt

    labelled = chart_series(series, language)
    x_title, y_title = str(labelled.index.name), str(labelled.name)
    # Neutral field names: Vega reads quotes and dots in a field name ("Chiffre
    # d'affaires") as access-path syntax and fails; the labels go in the titles.
    df = pd.DataFrame({"x": labelled.index, "y": labelled.to_numpy()})
    temporal = pd.api.types.is_datetime64_any_dtype(df["x"])
    base = alt.Chart(df)
    marked = base.mark_bar() if kind == "bar" else base.mark_line()
    if kind == "bar" and temporal and _one_point_per_month(df["x"]):
        # One band per month: on a temporal axis each bar is only a few pixels wide.
        x = alt.X(field="x", type="ordinal", timeUnit="yearmonth", title=x_title,
                  axis=alt.Axis(format="%b %Y", labelAngle=0))
        x_tip = alt.Tooltip(field="x", type="ordinal", timeUnit="yearmonth",
                            title=x_title, format="%B %Y")
    else:
        x_type: Literal["temporal", "nominal"] = "temporal" if temporal else "nominal"
        x = alt.X(field="x", type=x_type, sort=None, title=x_title)
        x_tip = alt.Tooltip(field="x", type=x_type, title=x_title,
                            format="%d %b %Y" if temporal else "")
    out = marked.encode(
        x=x,
        y=alt.Y(field="y", type="quantitative", title=y_title),
        tooltip=[x_tip,
                 alt.Tooltip(field="y", type="quantitative", title=y_title,
                             format=",.2~f")],
    )
    if language == "en":
        return out
    return out.configure(locale=FRENCH_CHART_LOCALE)


def ui_text(key: str, language: str, **values: object) -> str:
    """Dashboard label ``key`` in ``language`` (``fr`` when unknown), formatted with values.

    French templates get a non-breaking space before ':', ';', '?' and '!' (the values
    filled in are left as they are)."""
    texts = UI_TEXT[key]
    template = texts.get(language)
    if template is None or language == "fr":
        template = french_spacing(texts["fr"])
    return template.format(**values)


def num(value: float, language: str, spec: str = "") -> str:
    """Format ``value`` with ``spec``; French number format unless ``language`` is en.

    '1,735' -> '1 735', '42.54' -> '42,54', '-70%' -> '-70 %' (non-breaking spaces)."""
    text = format(value, spec)
    return text if language == "en" else french_numbers(text)


def anomaly_text(anomaly: insights.Anomaly, language: str) -> str:
    """Dashboard line of an anomaly; in English it equals ``anomaly.describe()``."""
    start, end = anomaly.start.date(), anomaly.end.date()
    period = (ui_text("anomaly_day", language, day=start) if anomaly.start == anomaly.end
              else ui_text("anomaly_period", language, start=start, end=end))
    kind_key = f"anomaly_{anomaly.kind}"
    kind = ui_text(kind_key, language) if kind_key in UI_TEXT else anomaly.kind
    return ui_text("anomaly_line", language, kind=kind, period=period,
                   actual=num(anomaly.actual, language, ",.0f"),
                   expected=num(anomaly.expected, language, ",.0f"),
                   change=num(anomaly.ratio - 1, language, "+.0%"))


def move_reason(move: marketing.BudgetMove, language: str) -> str:
    """Reason of a budget move; in English it equals ``move.reason``."""
    if move.from_roi is None or move.median_roi is None or move.to_roas is None:
        return move.reason
    return ui_text("move_reason", language, src=move.from_channel, dst=move.to_channel,
                   roi=num(move.from_roi, language, ".2f"),
                   median=num(move.median_roi, language, ".2f"),
                   roas=num(move.to_roas, language, ".2f"))


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


def leak_warning(meta: dict, language: str) -> str | None:
    """Target-leakage warning of a trained model's metadata, or ``None`` when not flagged."""
    suspects = meta.get("leakage_suspects") or []
    if not suspects:
        return None
    from mide.cli import _leak_line  # local import: cli imports heavy modules

    return _leak_line(str(meta.get("target")), list(suspects), language)


def hardware_view(cfg: Config) -> dict:
    """Hardware report, installed LLM weights and trained models."""
    report: HardwareReport = profile_hardware()
    return {
        "hardware": report,
        "llm": list_models(cfg.models.profiles, cfg.app_dir / "models"),
        "trained": list_trained_models(cfg.app_dir / "models_trained"),
    }
