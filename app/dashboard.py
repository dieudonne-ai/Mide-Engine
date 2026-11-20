"""MIDE Engine dashboard (Streamlit). Launch with `mide ui`."""

from __future__ import annotations

import streamlit as st

from mide import __version__
from mide import dashboard_data as dd
from mide.agent.decision import fact_sep
from mide.config import ConfigError
from mide.connectors.sources import add_source, remove_source


@st.cache_data(show_spinner=False)
def _load(config_dir: str | None, _version: int):
    from pathlib import Path

    return dd.load_dashboard_data(Path(config_dir) if config_dir else None)


def _need(data_ok: bool, what: str, lang: str) -> bool:
    if not data_ok:
        st.info(dd.ui_text("no_data", lang, what=dd.ui_text(f"what_{what}", lang),
                           page=dd.ui_text("page_sources", lang)))
    return data_ok


def page_home(data: dd.DashboardData, lang: str) -> None:
    st.header(dd.ui_text("page_home", lang))
    report = dd.home_kpis(data)
    if not _need(report is not None, "sales", lang):
        return
    k = report.kpis
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(dd.ui_text("revenue", lang), dd.num(k.total_revenue, lang, ",.0f"))
    c2.metric(dd.ui_text("orders", lang), dd.num(k.orders, lang, ","))
    c3.metric(dd.ui_text("avg_order", lang), dd.num(k.avg_order_value, lang, ",.0f"))
    growth = None if k.growth_30d is None else dd.num(k.growth_30d, lang, "+.1%")
    c4.metric(dd.ui_text("last_30d", lang), dd.num(k.last_30d_revenue, lang, ",.0f"), growth)
    st.subheader(dd.ui_text("anomalies", lang))
    if report.anomalies:
        for a in report.anomalies:
            st.warning(dd.anomaly_text(a, lang))
    else:
        st.success(dd.ui_text("no_anomaly", lang))


def page_sales(data: dd.DashboardData, lang: str) -> None:
    st.header(dd.ui_text("page_sales", lang))
    if not _need(data.has_sales, "sales", lang):
        return
    view = dd.sales_view(data.tables.sales, data.tables.products)
    fc = view["forecast"]
    cols = st.columns(len(fc.totals))
    for col, (h, total) in zip(cols, fc.totals.items()):
        growth = fc.growth_pct.get(h)
        col.metric(dd.ui_text("forecast", lang, h=h), dd.num(total, lang, ",.0f"),
                   None if growth is None else dd.num(growth / 100, lang, "+.1%"))
    st.altair_chart(dd.chart(view["history"].resample("W").sum(), lang))
    st.subheader(dd.ui_text("monthly_revenue", lang))
    st.altair_chart(dd.chart(view["trend"].monthly, lang, "bar"))
    direction = dd.ui_text(f"trend_{view['trend'].direction}", lang)
    st.caption(dd.ui_text("trend", lang, value=direction))
    s = view["seasonality"]
    st.write(dd.ui_text("seasonality", lang, peak=s.peak_month, trough=s.trough_month,
                        weekday=s.peak_weekday))
    left, right = st.columns(2)
    left.subheader(dd.ui_text("top_products", lang))
    left.dataframe(dd.table_view(view["products"]["top"], lang))
    right.subheader(dd.ui_text("flop_products", lang))
    right.dataframe(dd.table_view(view["products"]["flop"], lang))


def page_customers(data: dd.DashboardData, lang: str) -> None:
    st.header(dd.ui_text("page_customers", lang))
    if not _need(data.has_sales, "customers", lang):
        return
    view = dd.customers_view(data.tables.sales)
    st.subheader(dd.ui_text("rfm_segments", lang))
    st.dataframe(dd.table_view(view["segments"], lang))
    churn = view["churn"]
    st.metric(dd.ui_text("revenue_at_risk", lang), dd.num(churn.revenue_at_risk, lang, ",.0f"))
    st.write(dd.ui_text("high_risk", lang, n=len(churn.high_risk)))
    top = churn.scores.sort_values("risk", ascending=False).head(20)
    st.dataframe(dd.table_view(top, lang))


def page_marketing(data: dd.DashboardData, lang: str) -> None:
    st.header(dd.ui_text("page_marketing", lang))
    if not _need(data.has_campaigns, "marketing", lang):
        return
    view = dd.marketing_view(data.tables.campaigns)
    st.dataframe(dd.table_view(view["channels"], lang))
    st.altair_chart(dd.chart(view["channels"]["roi"], lang, "bar"))
    plan = view["plan"]
    st.subheader(dd.ui_text("reallocation", lang))
    if not plan.moves:
        st.success(dd.ui_text("no_reallocation", lang))
    for m in plan.moves:
        st.write(dd.ui_text("move", lang, src=m.from_channel, dst=m.to_channel,
                            amount=dd.num(m.amount, lang, ",.0f"), reason=dd.move_reason(m, lang),
                            extra=dd.num(m.estimated_extra_revenue, lang, ",.0f")))


def page_ask(data: dd.DashboardData, config_dir, lang: str) -> None:
    st.header(dd.ui_text("page_ask", lang))
    question = st.text_input(dd.ui_text("your_question", lang))
    if not question:
        return
    from mide.cli import _error_text, ask_answer

    try:
        with st.spinner(dd.ui_text("thinking", lang)):
            answer, used, sources = ask_answer(question, config_dir)
    except Exception as exc:  # noqa: BLE001 - show any engine error to the user
        st.error(_error_text(exc, lang))
        return
    st.write(answer)
    if used:
        st.caption(used)
    if sources:
        st.caption(sources)


def page_sources(data: dd.DashboardData, config_dir, lang: str) -> None:
    st.header(dd.ui_text("page_sources", lang))
    st.caption(dd.ui_text("sources_caption", lang))
    for src in data.sources:
        c1, c2 = st.columns([5, 1])
        c1.code(src)
        if c2.button(dd.ui_text("remove", lang), key=f"rm-{src}"):
            remove_source(src, config_dir)
            st.session_state["version"] = st.session_state.get("version", 0) + 1
            st.rerun()
    new = st.text_input(dd.ui_text("add_prompt", lang))
    if st.button(dd.ui_text("add", lang)) and new:
        try:
            add_source(new, config_dir)
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))
        else:
            st.session_state["version"] = st.session_state.get("version", 0) + 1
            st.rerun()
    st.subheader(dd.ui_text("datasets", lang))
    for name, df in data.frames.items():
        st.write(dd.ui_text("dataset_line", lang, name=name, rows=dd.num(len(df), lang, ","),
                            cols=len(df.columns)))


def page_hardware(data: dd.DashboardData, lang: str) -> None:
    st.header(dd.ui_text("page_hardware", lang))
    view = dd.hardware_view(data.config)
    hw = view["hardware"]
    gpu = (dd.ui_text("gpu_vram", lang, name=hw.gpu.name, vram=dd.num(hw.gpu.vram_gb, lang, ".1f")) if hw.gpu
           else dd.ui_text("gpu_none", lang))
    st.write(dd.ui_text("hardware_line", lang, ram=dd.num(hw.ram_gb, lang, ".1f"), cores=hw.cpu_cores,
                        os=hw.os_name, gpu=gpu, disk=dd.num(hw.disk_free_gb, lang, ".1f")))
    st.metric(dd.ui_text("profile", lang), hw.profile)
    st.subheader(dd.ui_text("llm_weights", lang))
    for m in view["llm"]:
        state = dd.ui_text("installed" if m.installed else "not_installed", lang)
        st.write(f"{m.profile}{fact_sep(lang)}{m.repo}/{m.file} - {state}")
    st.subheader(dd.ui_text("trained_models", lang))
    for r in view["trained"]:
        st.write(dd.ui_text("trained_line", lang, name=r.name, version=r.version,
                            task=r.metadata["task"], target=r.metadata["target"]))
        leak = dd.leak_warning(r.metadata, lang)
        if leak:
            st.warning(leak)
    if not view["trained"]:
        st.caption(dd.ui_text("no_trained", lang))


def main() -> None:
    st.set_page_config(page_title="MIDE Engine", layout="wide")
    config_dir = dd.config_dir_from_env()
    lang = dd.dashboard_language(config_dir)
    labels = dd.page_labels(lang)
    st.sidebar.title(f"MIDE {__version__}")
    page = st.sidebar.radio(dd.ui_text("sidebar_page", lang), dd.PAGE_KEYS,
                            format_func=labels.__getitem__)
    if st.sidebar.button(dd.ui_text("refresh", lang)):
        st.session_state["version"] = st.session_state.get("version", 0) + 1
    try:
        with st.spinner(dd.ui_text("loading", lang)):
            data = _load(str(config_dir) if config_dir else None,
                         st.session_state.get("version", 0))
    except ConfigError as exc:
        st.error(dd.config_error_message(exc, config_dir))
        return
    if page == "home":
        page_home(data, lang)
    elif page == "sales":
        page_sales(data, lang)
    elif page == "customers":
        page_customers(data, lang)
    elif page == "marketing":
        page_marketing(data, lang)
    elif page == "ask":
        page_ask(data, config_dir, lang)
    elif page == "sources":
        page_sources(data, config_dir, lang)
    else:
        page_hardware(data, lang)


main()
