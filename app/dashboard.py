"""MIDE Engine dashboard (Streamlit). Launch with `mide ui`."""

from __future__ import annotations

import streamlit as st

from mide import __version__
from mide import dashboard_data as dd
from mide.config import ConfigError
from mide.connectors.sources import add_source, remove_source

PAGES = ["Home", "Sales", "Customers", "Marketing", "Ask a question", "Data sources",
         "Hardware & models"]


@st.cache_data(show_spinner="Loading data...")
def _load(config_dir: str | None, _version: int):
    from pathlib import Path

    return dd.load_dashboard_data(Path(config_dir) if config_dir else None)


def _need(data_ok: bool, what: str) -> bool:
    if not data_ok:
        st.info(f"No {what} data found. Add a source in the *Data sources* page.")
    return data_ok


def page_home(data: dd.DashboardData) -> None:
    st.header("Home")
    report = dd.home_kpis(data)
    if not _need(report is not None, "sales"):
        return
    k = report.kpis
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"{k.total_revenue:,.0f}")
    c2.metric("Orders", f"{k.orders:,}")
    c3.metric("Average order", f"{k.avg_order_value:,.0f}")
    growth = None if k.growth_30d is None else f"{k.growth_30d:+.1%}"
    c4.metric("Last 30 days", f"{k.last_30d_revenue:,.0f}", growth)
    st.subheader("Anomalies")
    if report.anomalies:
        for a in report.anomalies:
            st.warning(a.describe())
    else:
        st.success("No abnormal day detected.")


def page_sales(data: dd.DashboardData) -> None:
    st.header("Sales")
    if not _need(data.has_sales, "sales"):
        return
    view = dd.sales_view(data.tables.sales)
    fc = view["forecast"]
    cols = st.columns(len(fc.totals))
    for col, (h, total) in zip(cols, fc.totals.items()):
        growth = fc.growth_pct.get(h)
        col.metric(f"Forecast {h} d", f"{total:,.0f}",
                   None if growth is None else f"{growth:+.1f}%")
    st.line_chart(view["history"].resample("W").sum())
    st.subheader("Monthly revenue")
    st.bar_chart(view["trend"].monthly)
    st.caption(f"Trend: {view['trend'].direction}")
    s = view["seasonality"]
    st.write(f"Peak month: **{s.peak_month}**, trough: **{s.trough_month}**, "
             f"best weekday: **{s.peak_weekday}**")
    left, right = st.columns(2)
    left.subheader("Top products")
    left.dataframe(view["products"]["top"])
    right.subheader("Flop products")
    right.dataframe(view["products"]["flop"])


def page_customers(data: dd.DashboardData) -> None:
    st.header("Customers")
    if not _need(data.has_sales, "customer"):
        return
    view = dd.customers_view(data.tables.sales)
    st.subheader("RFM segments")
    st.dataframe(view["segments"])
    churn = view["churn"]
    st.metric("Revenue at risk", f"{churn.revenue_at_risk:,.0f}")
    st.write(f"{len(churn.high_risk)} high-risk customers")
    st.dataframe(churn.scores.sort_values(churn.scores.columns[-1], ascending=False).head(20))


def page_marketing(data: dd.DashboardData) -> None:
    st.header("Marketing")
    if not _need(data.has_campaigns, "marketing"):
        return
    view = dd.marketing_view(data.tables.campaigns)
    st.dataframe(view["channels"])
    st.bar_chart(view["channels"]["roi"])
    plan = view["plan"]
    st.subheader("Suggested budget reallocation")
    if not plan.moves:
        st.success("No reallocation needed.")
    for m in plan.moves:
        st.write(f"- {m.from_channel} → {m.to_channel}: **{m.amount:,.0f}** ({m.reason}; "
                 f"≈ +{m.estimated_extra_revenue:,.0f} revenue)")


def page_ask(data: dd.DashboardData, config_dir) -> None:
    st.header("Ask a question")
    question = st.text_input("Your question")
    if not question:
        return
    from mide.cli import ask_answer

    try:
        with st.spinner("Thinking..."):
            answer, used, sources = ask_answer(question, config_dir)
    except Exception as exc:  # noqa: BLE001 - show any engine error to the user
        st.error(str(exc))
        return
    st.write(answer)
    if used:
        st.caption(used)
    if sources:
        st.caption(sources)


def page_sources(data: dd.DashboardData, config_dir) -> None:
    st.header("Data sources")
    st.caption("MIDE only reads the sources listed here (read-only).")
    for src in data.sources:
        c1, c2 = st.columns([5, 1])
        c1.code(src)
        if c2.button("Remove", key=f"rm-{src}"):
            remove_source(src, config_dir)
            st.session_state["version"] = st.session_state.get("version", 0) + 1
            st.rerun()
    new = st.text_input("Add a folder, file or SQL URL")
    if st.button("Add") and new:
        try:
            add_source(new, config_dir)
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
        else:
            st.session_state["version"] = st.session_state.get("version", 0) + 1
            st.rerun()
    st.subheader("Datasets")
    for name, df in data.frames.items():
        st.write(f"**{name}** - {len(df)} rows x {len(df.columns)} columns")


def page_hardware(data: dd.DashboardData) -> None:
    st.header("Hardware & models")
    view = dd.hardware_view(data.config)
    hw = view["hardware"]
    gpu = f"{hw.gpu.name} ({hw.gpu.vram_gb} GB)" if hw.gpu else "none"
    st.write(f"RAM {hw.ram_gb} GB - {hw.cpu_cores} cores - {hw.os_name} - GPU: {gpu} - "
             f"disk free {hw.disk_free_gb} GB")
    st.metric("Profile", hw.profile)
    st.subheader("LLM weights")
    for m in view["llm"]:
        st.write(f"{m.profile}: {m.repo}/{m.file} - "
                 f"{'installed' if m.installed else 'not installed'}")
    st.subheader("Trained models")
    for r in view["trained"]:
        st.write(f"{r.name} v{r.version} [{r.metadata['task']}] target={r.metadata['target']}")
    if not view["trained"]:
        st.caption("None yet. Use `mide train`.")


def main() -> None:
    st.set_page_config(page_title="MIDE Engine", layout="wide")
    config_dir = dd.config_dir_from_env()
    st.sidebar.title(f"MIDE {__version__}")
    page = st.sidebar.radio("Page", PAGES)
    if st.sidebar.button("Refresh data"):
        st.session_state["version"] = st.session_state.get("version", 0) + 1
    try:
        data = _load(str(config_dir) if config_dir else None, st.session_state.get("version", 0))
    except ConfigError as exc:
        st.error(f"Configuration error: {exc}")
        return
    if page == "Home":
        page_home(data)
    elif page == "Sales":
        page_sales(data)
    elif page == "Customers":
        page_customers(data)
    elif page == "Marketing":
        page_marketing(data)
    elif page == "Ask a question":
        page_ask(data, config_dir)
    elif page == "Data sources":
        page_sources(data, config_dir)
    else:
        page_hardware(data)


main()
