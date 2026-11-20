# PROGRESS.md — Journal de développement

> L'agent ajoute UNE entrée à la fin de chaque session, la plus récente EN HAUT.
> Dieudonné lit ce fichier pour suivre l'avancement et répondre aux questions.

---

## ❓ Questions pour Dieudonné

_(L'agent écrit ici les blocages et décisions à prendre. Dieudonné répond directement sous chaque question.)_

- Roadmap complete (2026-11-15): which backlog item should come next (Google Sheets/Odoo/QuickBooks connectors, local FastAPI REST API, desktop app, Swahili, multi-user)? Until then, scheduled runs only do maintenance.
- W4-06: Docker daemon unavailable in the agent sandbox, so `docker build` was not verified. Could you run `docker build -t mide-engine . && docker run --rm mide-engine demo` and confirm?

---

## 📊 État global

| Semaine | Tâches terminées | Statut |
|---------|------------------|--------|
| S1 — Fondations       | 9 / 9 | ✅ terminé |
| S2 — LLM & RAG        | 7 / 7 | ✅ terminé |
| S3 — Intelligence     | 9 / 9 | ✅ terminé |
| S4 — Produit          | 8 / 8 | ✅ terminé |

---

## 📝 Journal des sessions

<!--
Format de chaque entrée :

### YYYY-MM-DD HH:MM — <ID tâche> <titre>
- **Fait :** ...
- **Fichiers principaux :** ...
- **Tests :** X passés / Y au total
- **PR :** #numéro / lien
- **Décisions techniques :** ... (et pourquoi)
- **Problèmes / dette technique :** ...
- **Prochaine tâche :** <ID>
-->

### 2026-11-20 — Maintenance: French multiplier in the attribution check (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Suite green at start (535 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`); PR #136 was open with green tests and was merged into main as asked. Picked a leftover English form in the French report: the marketing attribution check read "les canaux déclarent 1 443 825 de revenus, 1,96x le total des ventes 735 907 ; …". It now reads "les canaux déclarent 1 443 825 de revenus, soit 1,96 fois le total des ventes (735 907) ; …" in the weekly report (budget action), `mide ask` "Données utilisées" and the dashboard. English is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py` (`_FR_VALUE_PHRASES`), `tests/test_agent.py`, `tests/test_report.py`
- **Tests :** 536 passed, 0 skipped. 1 new: the French demo report has no "1,96x" multiplier and says "fois le total des ventes (", while the English one keeps "1.96x total sales" (fails without the fix). 1 new case in `test_fact_value_translates_english_phrases_to_french`. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-gcdwe9 -> main
- **Décisions techniques :** the translation happens only at display time, like the other phrases, so the English fact (LLM prompt, English output) is untouched. The regex now also matches the "x" and the ";" so the total can be put in parentheses.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (here 0.3 % of revenue; left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: spelled-out months in the French sales trend (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #135 was already merged; suite green at start (525 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #135: the French sales trend still showed ISO year-months ("sur un an +12 % (2024-01 -> 2024-12 vs 2023-01 -> 2023-12)"). It now reads "(janvier 2024 à décembre 2024 vs janvier 2023 à décembre 2023)" in the weekly report, `mide ask` "Données utilisées" and the dashboard. English is unchanged.
- **Fichiers principaux :** `mide/utils/french.py` (new `french_month()`, `french_year_months()`), `mide/agent/decision.py` (`fact_value` spells out year-months in French), `tests/test_french.py`, `tests/test_report.py`
- **Tests :** 535 passed, 0 skipped. 10 new: 8 `french_year_months` cases (range, lone month, full date kept, invalid month kept, digits glued kept, trailing dash kept, no month), `french_month` bad month, and the French demo report has no ISO year-month while the English one keeps them (fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-lkuj04 -> main
- **Décisions techniques :** same approach as #135: the facts keep ISO year-months (LLM prompt, English output) and they are rewritten at display time in `fact_value`, after `french_dates` so full dates are already spelled out. "à" between the two months avoids the de/d' elision problem ("d'octobre", "d'avril").
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: spelled-out dates in French fact values and dashboard anomalies (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #134 was already merged; suite green at start (518 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #134: French fact values still showed ISO dates ("baisse du 2023-06-14 au 2023-06-16", "735 907 du 2023-01-01 au 2024-12-31"), and so did the dashboard anomaly list ("chute le 2024-03-10"). They now read "baisse du 14 juin 2023 au 16 juin 2023", "du 1er janvier 2023 au 31 décembre 2024", "chute le 10 mars 2024". This covers the weekly report (KPIs, alerts, actions), `mide ask` "Données utilisées" and the dashboard. English is unchanged.
- **Fichiers principaux :** `mide/utils/french.py` (new `french_dates()`), `mide/agent/decision.py` (`fact_value` spells out dates in French), `mide/dashboard_data.py` (`anomaly_text`), `tests/test_french.py`, `tests/test_report.py`, `tests/test_agent.py`, `tests/test_dashboard.py`
- **Tests :** 525 passed, 0 skipped. 7 new: 6 `french_dates` cases (day, period with "1er", year-months kept, invalid date kept, digits glued to a date kept, no date) and the French demo report has no ISO date in Markdown/HTML while the English one keeps them (fails without the fix). Existing expectations updated to the spelled-out dates: `test_fact_value_translates_english_phrases_to_french`, `test_anomaly_text_french`, `test_anomaly_text_unknown_kind_kept`, `test_french_report_has_no_english_fact_values`. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-gh537w -> main
- **Décisions techniques :** the dates are rewritten at display time (last step of `fact_value` before number formatting), so `insights.Anomaly.describe()` keeps ISO dates and `report._ANOMALY_END` can still parse them to filter old anomalies. Only full dates (`YYYY-MM-DD`) are spelled out; year-month ranges like "(2024-01 -> 2024-12)" in the sales trend stay as they are.
- **Problèmes / dette technique :** the sales trend still shows "(2024-01 -> 2024-12)" in French. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: spelled-out dates in the French report (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #133 was already merged; suite green at start (513 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #133: the French weekly report showed ISO dates. It now reads "Généré le 20 novembre 2026", "dernière vente le 31 décembre 2024" and "(avant le 2 octobre 2024)", with "1er" for the first of the month, in both Markdown and HTML. The English report keeps ISO dates.
- **Fichiers principaux :** `mide/utils/french.py` (new `FRENCH_MONTHS`, `french_date()`), `mide/report.py`, `mide/dashboard_data.py` (chart locale reuses `FRENCH_MONTHS`), `tests/test_french.py`, `tests/test_report.py`
- **Tests :** 518 passed, 0 skipped. 5 new: `french_date` cases (1er, février, août) and the report header/stale alert in FR vs EN. 2 existing assertions updated to the French long date (`test_recent_anomaly_alerts_keeps_recent_and_counts_older`, `test_stale_data_alert`). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-lf5eit -> main
- **Décisions techniques :** the anomaly descriptions from `insights` keep their ISO dates, because `report._ANOMALY_END` parses them to filter old anomalies; only text that the report writes itself is spelled out. One month list in `mide/utils/french.py`, shared with the dashboard chart locale.
- **Problèmes / dette technique :** anomaly lines in the French report still show ISO dates (see above). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: proper plurals instead of "(s)" in report and forecast notes (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #132 was already merged; suite green at start (512 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). The French weekly report on the demo data read "4 anomalie(s) plus ancienne(s) (avant le 2024-10-02) non listée(s)". It now reads "4 anomalies plus anciennes … non listées" ("1 anomalie plus ancienne … non listée" for one). The sales forecast note "N anomalous day(s) excluded from the fit." now uses "day"/"days" too. These were the last "(s)" plurals in `mide/` and `app/`.
- **Fichiers principaux :** `mide/report.py`, `mide/business/sales.py`, `tests/test_report.py`, `tests/test_sales.py`
- **Tests :** 513 passed, 0 skipped. 1 new: the forecast note on the demo data has no "(s)" and the right singular/plural. 1 existing assertion updated (`test_recent_anomaly_alerts_keeps_recent_and_counts_older` now expects the French plural, plus a new singular case). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-y6wzgx -> main
- **Décisions techniques :** inline singular/plural choice (same style as the English branch already used); no plural helper, since only two strings needed it.
- **Problèmes / dette technique :** while checking by hand, `mide sources add` run from the repo directory writes into the repo's `config/sources.yaml` (expected: it is the project config), which then fails `test_packaged_defaults_match_repo_config`; reverted before commit. Dates in the French report stay ISO (`2024-10-02`). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: one wide bar per month in the monthly revenue chart (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #131 was already merged; suite green at start (510 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #130/#131: the "Chiffre d'affaires mensuel" bars were a few pixels wide because they sat on a continuous time axis. Monthly bar charts now have one band per month, labelled "janv. 2024" in French ("Jan 2024" in English), tooltip "janvier 2024". Checked in a real browser (Streamlit + Chromium) on the demo data: 24 wide bars with French month labels.
- **Fichiers principaux :** `mide/dashboard_data.py`, `tests/test_dashboard.py`
- **Tests :** 512 passed, 0 skipped. 2 new: monthly bar charts use an ordinal `yearmonth` x axis (FR/EN, axis and tooltip formats) while line charts and bar charts with several points per month keep the time axis; the demo monthly revenue chart uses month bands (fails without the fix). 1 existing assertion updated: `test_chart_french_locale_and_titles` now expects an ordinal x for the monthly bar case (the line case still expects temporal). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ypy2up -> main
- **Décisions techniques :** in `dd.chart()`, a bar chart over dates switches to `type="ordinal"` + `timeUnit="yearmonth"` only when no two dates share a month (`_one_point_per_month`), so other date bar charts would keep the old behaviour. Vega still formats the month labels with the French locale, so no new text table was needed.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French month and weekday names in the dashboard seasonality line (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #130 was already merged; suite green at start (501 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #130: the seasonality sentence on the French Sales page read "Mois le plus fort : **Dec**, … meilleur jour : **Sat**". It now reads "**décembre**", "**samedi**". English is unchanged.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 510 passed, 0 skipped. 9 new: `season_label` for months and weekdays (FR/EN), every name has a distinct French label, unknown names are kept; the Sales page shows the French names in French and the English names in English (the French case fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-r0hcyw -> main
- **Décisions techniques :** new `dashboard_data.season_label()` maps the `sales.MONTH_NAMES` / `WEEKDAY_NAMES` abbreviations to the French names already in `FRENCH_CHART_LOCALE` (one source for French month/day names). `sales.Seasonality` is unchanged, so its English keys used by the agent and the reports stay the same.
- **Problèmes / dette technique :** monthly revenue bars are still thin (temporal x axis). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French number and date format on dashboard chart axes (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #129 was already merged; suite green at start (498 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #129: the three dashboard charts (weekly revenue, monthly revenue, ROI by channel) showed English axes on the French dashboard ("12,000", "Jan", "Mar"). In French they now read "12 000", "janv.", "mars", "juillet", and tooltips show "1 234,5". English is unchanged. Checked in a real browser (Streamlit + Chromium) on the demo data: both pages render with French axes.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 501 passed, 0 skipped. 3 new: `dd.chart` line/bar in French (titles, temporal x, French number and month locale, data unchanged, input not modified); English has no locale, nominal x keeps the series order. 1 existing test helper updated: `test_dashboard_chart_labels_follow_language` now reads axis titles as well as field names, since the translated labels moved from field names to titles. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-34zqyj -> main
- **Décisions techniques :** `st.line_chart` / `st.bar_chart` cannot take a locale, so the charts are now Altair charts (`dd.chart()`, shown with `st.altair_chart`) with a Vega `config.locale` (`FRENCH_CHART_LOCALE`) in French. Altair already comes with Streamlit (the `ui` extra) and is imported inside the function, so the core package does not need it. Data fields are named `x` / `y` and the translated labels go in the axis/tooltip titles: Vega reads the quote in "Chiffre d'affaires" as access-path syntax and the chart failed to render ("Access path missing closing quote") when the label was the field name.
- **Problèmes / dette technique :** monthly revenue bars are thin (temporal x axis, same as before). The seasonality line still shows English month/day names ("Dec", "Sat"). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French number format in dashboard tables (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #128 was already merged; suite green at start (495 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by the previous sessions: the `st.dataframe` tables (top/flop products, RFM segments, churn scores, marketing channels) showed numbers in English format ("12000.0", "1.53") on the French dashboard. In French they now read "12 000", "1,53" (non-breaking spaces, 2 decimals for non-integer floats). English is unchanged.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 498 passed, 0 skipped. 3 new: `number_cell` (FR/EN, integers, NaN, text, bool); `table_view` formats French numbers while the underlying data stays numeric and English is the plain table; every dashboard table on the demo data has no English decimal point left in French (fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** task/maint-fr-table-numbers -> main
- **Décisions techniques :** new `dashboard_data.table_view()` wraps `display_table()` in a pandas `Styler` (French only). A Styler only changes the displayed text, so sorting a column in the dashboard still sorts by value. `display_table()` is unchanged (still returns a DataFrame), so its tests are unaffected. The `Styler` import is type-checking only, because it needs `jinja2` (installed with Streamlit, the `ui` extra).
- **Problèmes / dette technique :** chart axes still use Streamlit/Vega number format. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French RFM segment names in the LLM prompt (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #127 was already merged; suite green at start (493 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #127: the French decision prompt still listed "segment At risk", "segment Hibernating", … so a French answer could quote the segment names in English. In French the prompt now lists "segment À risque", "segment En sommeil", "segment À surveiller", "segment Nouveaux / prometteurs", "segment Fidèles" (same table as the dashboard and "Données utilisées"). The English prompt is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 495 passed, 0 skipped. 2 new: the French prompt on the demo data has no English segment name left, the English prompt is unchanged, and the finding keys stay English (fails without the fix); unknown language and non-segment keys stay as they are. `ruff check .` OK; `mypy mide` OK.
- **PR :** task/maint-fr-segment-prompt -> main
- **Décisions techniques :** only the segment name in the prompt **key** is translated (new `decision._prompt_key`, reusing `customers.segment_label`). `Finding.facts` keys stay English, so the dashboard, `fact_label` and the existing tests are unaffected. The fact values in the prompt stay English ("44 customers, 9.1% of revenue"), as before: the model handles them fine and translating them would change every prompt test.
- **Problèmes / dette technique :** chart axes and `st.dataframe` tables still use Streamlit's number format. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French RFM segment names in `mide ask` / `mide chat` (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #126 was already merged; suite green at start (490 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Running `scripts/demo.sh` showed English RFM segment names inside the French "Données utilisées" block: "segment Needs attention", "segment At risk", "segment Hibernating", "segment New / promising", "segment Loyal". They now read "segment À surveiller", "À risque", "En sommeil", "Nouveaux / prometteurs", "Fidèles" (same names as the dashboard). English output is unchanged.
- **Fichiers principaux :** `mide/business/customers.py`, `mide/agent/decision.py`, `mide/dashboard_data.py`, `tests/test_agent.py`, `tests/test_customers.py`
- **Tests :** 493 passed, 0 skipped. 3 new: `fact_label` translates segment keys (FR, fallback, EN, unknown segment); "Données utilisées" on the demo data has no English segment name left in French (fails without the fix); `SEGMENT_LABELS` covers every segment `rfm_segments` can produce. `ruff check .` OK; `mypy mide` OK.
- **PR :** task/maint-fr-segment-labels -> main
- **Décisions techniques :** the segment display names moved from `dashboard_data.VALUE_LABELS` to `business/customers.SEGMENT_LABELS` (+ `segment_label()`), so the dashboard and the agent share one table and `agent/decision.py` does not import the dashboard layer. The fact keys stay English ("segment At risk") for the LLM prompt; only the displayed label is translated.
- **Problèmes / dette technique :** the LLM prompt still receives English segment names (fine for the model, but a French answer may quote them in English). Chart axes and `st.dataframe` tables still use Streamlit's number format. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French number format and non-breaking spacing in the Streamlit dashboard (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #125 was already merged; suite green at start (481 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #125: the dashboard still showed English numbers and ordinary spaces in French ("Tendance : hausse", "1,200 au lieu de 4,000 attendus (-70%)", "ROI de radio -0.20 contre une médiane de 1.50", metrics "1,234,567", "+12.3%", "RAM 15.73 Go"). In French they now read "Tendance : hausse", "1 200 au lieu de 4 000 attendus (-70 %)", "-0,20", "1 234 567", "+12,3 %", "RAM 15,7 Go" (non-breaking spaces), like the CLI and reports. English output is unchanged, except RAM/disk/VRAM now always show one decimal and the LLM weights line uses the shared label separator.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 490 passed, 0 skipped. 9 new: every French `UI_TEXT` template renders without a plain space before `: ; ? !`; filled-in values are untouched; `dd.num` FR/EN/fallback (thousands, decimals, percent, negative); home + sales metrics rendered by Streamlit `AppTest` in FR/EN (the FR case fails without the fix). 2 existing tests updated: they pinned English numbers inside French anomaly and budget-move texts. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-qcgfov -> main
- **Décisions techniques :** new `dashboard_data.num(value, language, spec)` reuses `decision.french_numbers` (same rule as `cli._num`); any language other than `en` gets the French format, matching the French fallback of `ui_text`. `ui_text` applies `utils.french.french_spacing` to the French **template** before `.format()`, so values (paths, channel names) are never changed.
- **Problèmes / dette technique :** chart axes and `st.dataframe` tables still use Streamlit's own number format (not controllable without styling every table). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: non-breaking space before `:`, `;` and `?` in French CLI messages (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #124 was already merged; suite green at start (464 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt left by #124: French CLI messages ("Erreur : …", "Sources autorisées : …", "Tâche : …", "RAM : 15,7 Go", "(3) ; il en faut au moins 20", "depuis internet ?") used an ordinary space before the sign, so a terminal could wrap between the word and the sign. Every French CLI template, the friendly error messages (`utils/errors.py`), `mide privacy`, the remaining inline French CLI strings (unknown indexed source, empty question, refused report overwrite) and the rejected LoRA message now use a non-breaking space, like `mide ask`/`mide report` already did. English output is unchanged.
- **Fichiers principaux :** `mide/utils/french.py` (new), `mide/cli.py`, `mide/utils/errors.py`, `mide/utils/privacy.py`, `mide/llm/lora.py`, `tests/test_french.py` (new)
- **Tests :** 481 passed, 0 skipped. 17 new in `tests/test_french.py` (`french_spacing` cases, with `10:30`, URLs, `C:\\data` untouched; every French CLI template renders without a plain space before a sign; `_sources_msg` and `friendly_message` FR/EN; `sources list`, `privacy`, unknown `sources remove` and empty `ask` end to end in FR/EN). The CLI/error ones fail without the fix. About 40 existing tests updated: they pinned the ordinary space inside French CLI output (only the expected strings changed). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-uhoppq -> main
- **Décisions techniques :** new `utils.french.french_spacing(text)` replaces only an ordinary space already written before `:`, `;`, `?`, `!` (followed by a space, the end or a quote). It is applied to the **template** before `.format()`, so values (paths, SQL URLs, column names) are never touched. Kept in `mide/utils` rather than `agent/decision` so `utils/errors.py` does not import the agent layer. U+00A0, same as #121/#122.
- **Problèmes / dette technique :** the Streamlit dashboard texts (`dashboard_data.py`) still use ordinary spaces (browsers rarely wrap there; left as is). Typer's own help texts are English only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French number format in `mide scan`, `train`, `models`, `auto` and `doctor` (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #123 was already merged; suite green at start (461 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). PR #120 put French numbers in `mide ask` and the reports only; the rest of the CLI still printed English numbers in French: "17037 lignes", "VC mae : 313.4 (référence 430.1)", "date_day_of_year (31%)", "mae=313.4 bat_reference=oui", "conservé (2 -> 2.5)", "RAM : 15.7 Go", "(12.0 Go de VRAM)", "(1.93 Go) depuis internet ?". They now read "17 037 lignes", "313,4 (référence 430,1)", "(31 %)", "mae=313,4", "(2 -> 2,5)", "15,7 Go", "12,0 Go", "1,93 Go" (non-breaking spaces). English output is unchanged except the row count, which now has a thousands separator ("17,037 rows").
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`, `tests/test_profiler.py`, `tests/test_downloader.py`
- **Tests :** 464 passed, 0 skipped. 3 new (all fail without the fix): `scan` + `train` + `models trained` on a 1,200-row CSV in FR/EN (no English decimal or percent left in French); `doctor` with a mocked hardware report (RAM, VRAM, disk) in FR/EN; `_fmt_size` in FR/EN. 4 existing tests updated: they pinned English decimals inside French output (`mide auto` lines, `doctor` VRAM, `models pull` size). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-rf1c4o -> main
- **Décisions techniques :** new `cli._num(value, language, spec)` formats with the usual spec and then reuses `decision.french_numbers` in French, so the CLI and the reports share one rule. Metric names and model names are untouched. The `mide auto` line now prints "?" instead of crashing if a candidate score comes without a previous score (cannot happen today, but the old f-string would raise).
- **Problèmes / dette technique :** the French spaces before ':' in CLI messages are still ordinary spaces (only `ask`/`report` use non-breaking ones). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: `mide auto` no longer replaces a clean model with a leaky one (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #122 was already merged; suite green at start (458 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Picked the debt item "`mide auto` still promotes a leaky candidate (warning only)": when new data adds a column computed from the target, the retrained candidate scores better only because it cheats, and the unattended run replaced the clean model with it. Now a candidate with leakage suspects never replaces a model that had none: the previous model stays the latest one, the outcome is `kept_leak`, shown as "Model sales-amount: kept (… -> …) likely target leakage in the new model, previous model kept" (FR: "conservé … fuite de la cible probable dans le nouveau modèle, l'ancien est conservé"), followed by the existing leakage warning naming the suspect columns. If the registered model was already flagged, scores compare like with like and the usual better-only rule applies (with the warning).
- **Fichiers principaux :** `mide/automl/auto.py`, `mide/cli.py`, `tests/test_auto.py`, `tests/test_cli.py`, `README.md`
- **Tests :** 461 passed, 0 skipped. 3 new: leaky candidate kept out of a clean registry (one version left, fingerprint recorded, no retrain on the next run); leaky candidate promoted over an already-flagged worse model; `AutoReport.retrained` counts `kept_leak`; plus the FR/EN `mide auto` line for `kept_leak`. 1 existing test (`test_promoted_outcome_reports_target_leakage`) replaced: it pinned the old promotion of a leaky candidate. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-16gzkm -> main
- **Décisions techniques :** the check reuses `TrainedModel.leakage_suspects` and the `leakage_suspects` already stored in the registry metadata (models trained before that field existed count as clean). New status `kept_leak` instead of a flag so the CLI detail lookup stays one key per status. `mide train` is unchanged: a user training by hand still gets the model with a warning, since they chose the columns.
- **Problèmes / dette technique :** a leakage suspect that is a false positive (a genuinely very predictive column) now blocks automatic promotion until the user retrains by hand with `mide train`; the line says why. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French spacing before `:` and `;` in `mide ask`, `mide report` and the weekly report (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #121 was already merged; suite green at start (455 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Running the demo report showed French text with English punctuation spacing: "**chiffre d'affaires**: 735 907", "risque de départ: 4 clients", "(0,3 % du chiffre d'affaires; 4 clients sur 400)", "6 840 vers Email; meilleur canal: Email", while other lines already used French spacing ("données anciennes : …"). French output now always has a non-breaking space before `:` and `;` ("chiffre d'affaires : 735 907", "chiffre d'affaires ; 4 clients"), in the "Données utilisées" block of `mide ask`/`mide chat` (title included), and in the KPIs, forecasts, alerts and action evidence of the report (Markdown and HTML). English output is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py`, `mide/report.py`, `tests/test_agent.py`, `tests/test_report.py`
- **Tests :** 458 passed, 0 skipped. 3 new (all fail without the fix): `french_punctuation` cases (label colons, semicolons, sign at the end; `3:2`, `10:30`, `http://` and already-spaced text untouched) plus `fact_sep`/`list_sep`; `data_used("fr")` on the demo data has no `:`/`;` without a non-breaking space before it, and English has none; same for the French Markdown and HTML report. 6 existing tests updated: they pinned the old English spacing inside French output. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-qbf82a -> main
- **Décisions techniques :** new `decision.french_punctuation(value)` runs last in `fact_value` (after `french_numbers`); only a `:`/`;` followed by a space or the end of the text is touched, so ratios, times and URLs stay as they are. New `fact_sep(language)`/`list_sep(language)` are the single source of the label and list separators, used by `data_used` and every report builder. The stale-data alert keeps its wording but now uses non-breaking spaces too. Non-breaking space (U+00A0), not the narrow one, for the same terminal reason as in #121.
- **Problèmes / dette technique :** other French CLI messages ("Sources autorisées : …") use a normal space before `:`, which is correct but can wrap before the sign; left as is. Numbers and punctuation written by the LLM itself are not reformatted. `mide auto` still promotes a leaky candidate (warning only). The report still ranks churn first whatever its size (here 0.3 % of revenue; left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French number format in `mide ask`, `mide report` and the weekly report (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #120 was already merged; suite green at start (452 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Fixes the debt left by #120: in French, the numbers kept the English format ("74 vs 1,735 attendus (-96%)", "ROAS 42.54", "+20.7%"). They now read "74 vs 1 735 attendus (-96 %)", "ROAS 42,54", "+20,7 %" in the "Données utilisées" block of `mide ask`/`mide chat`, and in the KPIs, forecasts, alerts and action evidence of the report (Markdown and HTML). English output is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`, `tests/test_report.py`
- **Tests :** 455 passed, 0 skipped. 3 new (all fail without the fix): `french_numbers` cases (thousands, decimals, percent, `1,234.56`, dates, ids and comma-separated lists untouched); `data_used("fr")` on the demo data has no English-formatted number left while the English one still has them; the French Markdown and HTML report have none either. 2 existing tests updated: they pinned English numbers inside French output. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-lfz9lg -> main
- **Décisions techniques :** new `decision.french_numbers(value)` runs last in `fact_value` (after the phrase replacements, whose `\S+` captures must still see unbroken numbers). Thousands and the space before `%` use a non-breaking space (U+00A0) so a number is never split across lines; U+202F (narrow) was avoided because older Windows terminals render it poorly. Facts stay English internally (LLM prompt, `report._is_recent`, dashboard), as before.
- **Problèmes / dette technique :** a product name containing a decimal number (e.g. "Huile 1.5L") is shown as "1,5L" in French, which is correct French anyway. Numbers written by the LLM itself are not reformatted. Segment and product names stay as in the data. `mide auto` still promotes a leaky candidate (warning only). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: French fact values in `mide ask`, `mide report` and the weekly report (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #119 was already merged; suite green at start (449 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Fixes the debt carried since the fact labels were translated: in French, the values after the labels were still English ("4 customers at high risk (top: …), 2,344 past revenue at risk", "6,840 to Email, est. extra revenue up to …", "drop on 2023-06-14 -> 2023-06-16: 74 vs 1,735 expected", "up, YoY +20.7%"). They now read "4 clients à risque élevé (principaux : …), 2,344 de chiffre d'affaires passé à risque", "6,840 vers Email, revenu supplémentaire estimé jusqu'à …", "baisse du 2023-06-14 au 2023-06-16 : 74 vs 1,735 attendus", "hausse, sur un an +20.7%", in the "Données utilisées" block, the report KPIs/forecasts/alerts and the action evidence (Markdown and HTML). English output is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py`, `mide/report.py`, `tests/test_agent.py`, `tests/test_report.py`
- **Tests :** 452 passed, 0 skipped. 3 new (all fail without the fix): every fact phrase the builders write maps to its French wording and stays unchanged in English; `data_used("fr")` on the demo data has no English phrase left; the French Markdown and HTML report have none either. 3 existing tests updated: they pinned the old English values inside French output ("spike", "500 to Email", "4 customers", "up"). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-o2vate -> main
- **Décisions techniques :** new `decision.fact_value(value, language)` applies an ordered list of regex phrase replacements, at display time only. Facts stay English on purpose: the LLM prompt, `report._is_recent` (parses "on DATE -> DATE:") and the dashboard depend on them. Anomaly alerts are filtered first, then translated. Chose phrase translation over restructuring every fact into structured values: same result for the user, far smaller change, and each phrase is covered by a test.
- **Problèmes / dette technique :** numbers keep the English format (`1,735`, `42.54`), not the French one (`1 735`, `42,54`). A new English phrase added to a fact builder must also be added to `_FR_VALUE_PHRASES`, otherwise it shows in English (the demo-data tests catch the current ones). Segment names (Champions, At risk…) and product names stay as in the data. `mide auto` still promotes a leaky candidate (warning only). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: time-series models no longer learn from calendar noise (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #118 was already merged; suite green at start (447 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, `mide train --dataset campaigns --target conversions` (monthly series) listed `month_day_of_week (19%)` among its main features: every date is the 1st of the month, so the weekday is pure calendar noise (it changes year to year) that the model was fitting, and the explanation shown to the user was misleading. Now date features with no signal are dropped when the model is fitted: constant parts (e.g. `day` always 1, `year` within a single year) and, when distinct dates are a week or more apart, `day_of_week` and `day`. `year`, `month`, `day_of_year` and the ordinal day are kept. CV MAE on the demo campaigns goes from 252.7 to 218.2 (baseline 319.3); daily series (sales) keep the weekday.
- **Fichiers principaux :** `mide/automl/trainer.py`, `tests/test_trainer.py`
- **Tests :** 449 passed, 0 skipped. 2 new (both fail without the fix): monthly dates drop `day`/`day_of_week` and keep `year`/`month`/`day_of_year`/`ordinal`, daily dates keep `day_of_week`/`day` and drop a constant `year`, `transform` returns exactly the fitted columns; the demo campaigns series has no weekday or day feature. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ckr2iq -> main
- **Décisions techniques :** new `FeaturePrep._noise_parts` filters `self.columns` in `fit`; constants `FINE_DATE_PARTS` and `COARSE_GAP_DAYS = 6` (same threshold as the weekly cadence in `task_detector._infer_frequency`). `transform` already reindexes to `self.columns`, so models saved before this change still predict with their old feature layout (no migration needed).
- **Problèmes / dette technique :** a model trained before this change keeps its noisy features until it is retrained (`mide auto` only retrains on changed data). `mide auto` still promotes a leaky candidate (warning only). The values after the fact labels still come from the English business facts. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: target-leakage warning also shown by `mide auto`, `mide models trained` and the dashboard (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #117 was already merged; suite green at start (444 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Follow-up to the debt left by #117: the leakage warning only appeared once, in `mide train`. When `mide auto` retrained a model on new data that now contains a column computed from the target (e.g. `amount_ttc` = `amount` x 1.18), the leaky candidate beat the old model and was promoted with only "Modèle sales-amount : remplacé (...) le nouveau modèle est meilleur". Now `mide auto` prints the same FR/EN warning ("Attention : score presque parfait, fuite de la cible probable. Vérifiez que amount_ttc ne sont pas calculées à partir de 'amount' …") right under the promoted model's line; `mide models trained` repeats it (indented) under every flagged model; the dashboard "Matériel" page shows it as a yellow warning under the trained model.
- **Fichiers principaux :** `mide/automl/auto.py`, `mide/cli.py`, `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_auto.py`, `tests/test_cli.py`, `tests/test_dashboard.py`
- **Tests :** 447 passed, 0 skipped. 3 new (all fail without the fix): a retrain on data with a target-derived column is promoted and its outcome carries `target` and `leakage_suspects` (and the saved metadata too), nothing for an unchanged dataset; `mide auto` and `mide models trained` print the exact FR/EN warning only for the flagged model; `dashboard_data.leak_warning` returns the text for flagged metadata and `None` otherwise. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-40sqc0 -> main
- **Décisions techniques :** `ModelOutcome` gains `target` and `leakage_suspects` (defaults `""`/`[]`), filled only for a promoted model (a kept candidate is not saved, so nothing changes for the user). New `cli._leak_line(target, suspects, language)` is the single source of the wording, reused by `mide train`, `mide auto`, `mide models trained` and `dashboard_data.leak_warning`.
- **Problèmes / dette technique :** `mide auto` still promotes a leaky candidate (warning only, as in `mide train`); refusing it would be a product decision. The values after the fact labels still come from the English business facts. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: `mide train` warns about likely target leakage (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #116 was already merged; suite green at start (439 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, `mide train --dataset sales --target quantity` reached accuracy = f1 = 1 because `amount` = `quantity` x `unit_price`, and the CLI only said "The model beats the baseline", so a useless model looked excellent. Now training flags likely leaks: a classifier with CV accuracy >= 0.99, a regressor whose CV MAE is <= 5 % of the baseline's, or a numeric feature with |correlation| >= 0.99 with a continuous target. The CLI then prints "Attention : score presque parfait, fuite de la cible probable. Vérifiez que amount, unit_price ne sont pas calculées à partir de 'quantity' ni connues après lui ; sinon retirez-les des données avant d'entraîner." / "Warning: near-perfect score, likely target leakage. Check that … are not computed from 'quantity' or only known after it; …". The model is still saved (it is a warning, not a refusal) and the suspects are stored as `leakage_suspects` in the model metadata. Time series are never flagged (their only features are date parts).
- **Fichiers principaux :** `mide/automl/trainer.py`, `mide/automl/registry.py`, `mide/cli.py`, `tests/test_trainer.py`, `tests/test_cli.py`
- **Tests :** 444 passed, 0 skipped. 5 new (all fail without the fix): demo `quantity` flags `amount`, `unit_price`; exact regression leak flagged while a noisy target and a plausible classifier are not; rules of `leakage_suspects` (date parts mapped back to their column, 60 % importance cut-off, at most 3, time series ignored, correlated columns first); a 40-row exact linear leak is caught by correlation although the trees cannot fit it perfectly; `mide train` FR/EN warning plus metadata, and no warning on a plausible dataset. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-zg79wi -> main
- **Décisions techniques :** new `trainer.leakage_suspects(...)` (pure function, thresholds as module constants `LEAK_*`) and `TrainedModel.leakage_suspects` (default `[]`). Suspects = correlated numeric columns, then the most important source columns until 60 % of the importance (max 3). The MAE ratio is 5 %, not 1 %: on small exact data, trees cannot get below a few percent, hence the extra correlation check. No retraining is done, so the cost is negligible.
- **Problèmes / dette technique :** a warning only; the columns are not removed automatically (the user decides). A real but very strong signal (e.g. a deterministic business rule) will also be flagged; the wording says "probable". `mide auto` and the dashboard do not show the warning yet (it is in the metadata). The values after the fact labels still come from the English business facts. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-20 — Maintenance: overlapping sources no longer list or index a file twice (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #115 was already merged; suite green at start (435 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, after `mide sources add demo`, running `mide sources add demo/sales.csv` was accepted ("Source ajoutée"), so the file was authorized twice: `mide scan` showed `sales.csv` twice, and a first `mide index` stored its chunks twice (the RAG then returned duplicate passages). Now: `mide sources add` of a file or sub-folder inside an authorized folder adds nothing and says so ("Déjà autorisé par le dossier <folder> : <path> n'a pas été ajouté." / "Already authorized by the folder <folder>: <path> was not added.", exit 0). For existing `sources.yaml` files that already overlap (or a parent folder added after a file), the catalog lists each file once and the indexer indexes each file once. Tables with the same name in two different databases are still kept apart.
- **Fichiers principaux :** `mide/connectors/sources.py`, `mide/cli.py`, `mide/ingestion/catalog.py`, `mide/rag/indexer.py`, `tests/test_connectors_base.py`, `tests/test_ingestion.py`, `tests/test_store.py`
- **Tests :** 439 passed, 0 skipped. 4 new (all fail without the fix): `sources add` of a file and of a sub-folder of an authorized folder refused in FR/EN with `sources.yaml` unchanged, the folder itself and a sibling folder still accepted; `covering_folder` ignores SQL URLs and exact matches; catalog lists a file once with overlapping sources but keeps two `orders` tables from two databases; indexing folder + inner file gives the same items and chunk count as the folder alone. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-fiwj1a -> main
- **Décisions techniques :** new `sources.covering_folder(value, sources)` and `SourceCovered` exception (not a `ValueError`, so it is not mistaken for the password error); it is "nothing to do", not an error, hence exit 0. Catalog dedup key is the item path for files and `(source, table)` for SQL. Indexer `process` returns early for an item already seen in this run. The dashboard shows the exception text in the existing error box.
- **Problèmes / dette technique :** adding a parent folder does not remove the file sources it now covers (harmless thanks to the dedup; `mide sources remove` cleans them). While testing, `mide train --dataset sales --target quantity` got f1 = 1 because `amount` = `quantity` x `unit_price`: target leakage is still not detected. The values after the fact labels still come from the English business facts. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` refuses an ambiguous dataset name; one model name per dataset (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #114 was already merged; suite green at start (432 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data with a second authorized folder that also holds a `sales.csv`, `mide train --dataset sales --target amount` silently trained on whichever file came first, with nothing saying which. Also, the model was named after the exact text typed: `sales`, `sales.csv` and the full path gave three separate models (`sales-…`, `sales.csv-…`, `tmp_…_demo_sales.csv-…`, the last one putting the user's folder path in the model name). Now: an ambiguous short name is refused ("Erreur : Plusieurs jeux de données s'appellent 'sales' : <path1>, <path2>. Indiquez le chemin complet avec --dataset." / "Error: Several datasets are named 'sales': … Pass the full path with --dataset.", exit 1, nothing trained); a full path always wins; the model name always uses the short, path-free label (file stem, `file.xlsx::sheet` or table), so every spelling adds a version to the same model. The exact file is stored as `item` in the model metadata, and `mide auto` retrains only on that file: if it is gone, the model is "skipped" instead of being retrained on another file with the same name.
- **Fichiers principaux :** `mide/cli.py`, `mide/automl/auto.py`, `tests/test_cli.py`, `tests/test_auto.py`
- **Tests :** 435 passed, 0 skipped. 3 new (all fail without the fix): ambiguous name refused in FR/EN with both paths and no model saved, then full path accepted with metadata `dataset`/`item`; `sales`, `sales.csv` and full path give `sales-amount` v1/v2/v3; `retrain_if_changed` matches the recorded `item` only (skipped when absent, unchanged when present). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-wz3bgt -> main
- **Décisions techniques :** new `cli.dataset_label(item, source)` and `_dataset_connector`/`_read_item` helpers; `_load_dataset` now returns `(item, label, frame)` and only reads the chosen item. `auto._find_frame` takes the optional recorded `item`; models saved before this change (no `item`) keep the old label matching, so existing registries still work.
- **Problèmes / dette technique :** models trained before this change with a full path keep their long name (rename or retrain them by hand). The values after the fact labels still come from the English business facts. Target leakage is still not detected (e.g. `quantity` vs `amount`). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: a missing SQLite database is refused, never created (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #113 was already merged; suite green at start (427 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo setup, `mide sources add sqlite:///…/x.db` with a mistyped/non-existent file was accepted ("Source ajoutée"), and the next `mide scan` silently **created an empty `x.db` file** on disk (SQLite creates the file on connect), breaking the read-only rule (CLAUDE.md §2.3) and showing nothing. Now: `mide sources add` refuses it ("Erreur : le chemin n'existe pas : sqlite:///…" / "Error: path does not exist: …", exit 1, nothing created); a SQLite source deleted after being added is reported like a missing folder ("Attention : source introuvable, ignorée : sqlite:///…") and skipped by `mide scan`, `mide index`, `mide train`, `mide ask`/`report` data loading, without recreating the file. SQLite files are now opened with `mode=ro` at file level, on top of `PRAGMA query_only` and `ensure_read_only`.
- **Fichiers principaux :** `mide/connectors/sql.py`, `mide/connectors/sources.py`, `mide/ingestion/catalog.py`, `mide/rag/indexer.py`, `mide/cli.py`, `tests/test_sql.py`, `tests/test_connectors_base.py`, `tests/test_ingestion.py`
- **Tests :** 432 passed, 0 skipped. 5 new (all fail without the fix): `sqlite_file` URL parsing (file, memory, URI mode, other dialects, invalid URL); connector on a missing file raises `FileNotFoundError` and creates nothing; a write is refused at file level even with `query_only` turned off; `mide sources add` of a missing SQLite file refused in FR/EN without creating it; `mide scan` warns about and skips a deleted SQLite source without recreating it. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-s56yb1 -> main
- **Décisions techniques :** new `sql.sqlite_file(url)` (parses with SQLAlchemy `make_url`, returns `None` for `:memory:`, `uri=true` URLs and other dialects, so they keep the previous behavior). `SQLConnector.engine` uses a `creator` opening `file:…?mode=ro` with `sqlite3`. New `sources.source_missing(source)` (paths and SQLite files; server databases are never "missing") replaces the path-only checks in the CLI warning, catalog, indexer and dataset loaders.
- **Problèmes / dette technique :** a relative SQLite URL (`sqlite:///shop.db`) still depends on the current directory, as in SQLAlchemy. The values after the fact labels still come from the English business facts. Target leakage is still not detected (e.g. `quantity` vs `amount`). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: missing optional dependencies explained in the `language` setting; `mide ask` degrades without llama-cpp-python (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #112 was merged (suite green on its head: 422 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data with the default French config, a missing optional extra was explained in English: `mide index` and `mide chat` printed "Erreur : sentence-transformers is not installed. Install it with `pip install mide-engine[rag]`." and `mide auto` "Indexation : ignorée (sentence-transformers is not installed…)". Worse, with a downloaded model but no `llama-cpp-python`, `mide ask "Quel canal marketing a le meilleur ROI ?"` failed with "Erreur : Erreur inattendue : llama-cpp-python is not installed…" instead of showing the computed figures. Now: "sentence-transformers n'est pas installé. Installez-le avec `pip install mide-engine[rag]`." (EN unchanged) in `mide index`, `mide auto`, `mide chat`, `mide ask` and the dashboard "Poser une question" page; `mide ask` on a business question without llama-cpp-python shows "LLM local indisponible (llama-cpp-python n'est pas installé. …). Voici les chiffres calculés…" plus the figures, as it already did when the model file is missing; a documents-only question gives a clean localized error (exit 1).
- **Fichiers principaux :** `mide/utils/errors.py`, `mide/rag/embeddings.py`, `mide/llm/runtime.py`, `mide/cli.py`, `app/dashboard.py`, `tests/test_cli.py`, `tests/test_agent.py`, `tests/test_runtime.py`, `tests/test_embeddings.py`
- **Tests :** 427 passed, 0 skipped. 5 new (all fail without the fix): FR/EN messages of `mide index`, `mide auto` and `mide chat` without sentence-transformers; `mide ask` figures + FR/EN note without llama-cpp-python; documents-only `mide ask` error; `LLMDependencyError` / `EmbeddingDependencyError` attributes and `friendly_message` FR/EN. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-c08sj4 -> main
- **Décisions techniques :** new `MissingDependencyError(package, extra)` in `utils/errors.py` with a `missing_dependency` FR/EN message used by `friendly_message` (so the last-resort handler no longer says "unexpected error"). `EmbeddingDependencyError` and `LLMDependencyError` subclass both it and the existing `EmbeddingError` / `LLMError`, so every existing `except`/`pytest.raises` still works and `str(exc)` keeps the English text. `cli._error_text` localizes them; `ask_answer` treats `LLMError` like `DownloadError` (graceful degradation, CLAUDE.md §2.4).
- **Problèmes / dette technique :** "Model file not found" in `LlamaCppLLM` stays English (unreachable from the CLI, which checks the file first). The values after the fact labels still come from the English business facts. Target leakage is still not detected (e.g. `quantity` vs `amount`). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: report action evidence labels follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #111 was already merged; suite green at start (421 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, the French `mide report` still printed raw English fact keys in the "Actions prioritaires" evidence: "churn: …", "best channel: Email", "attribution check: …", "trend: up …" and "forecast 30d: …". They now use the same labels as the rest of the report: "risque de départ", "meilleur canal", "contrôle d'attribution", "tendance", "prévision à 30 jours" (Markdown and HTML). The English report is unchanged.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 422 passed, 0 skipped. 1 new: FR and EN evidence of the churn, budget (move + best channel + attribution check), best-channel-only and trend (+ 30d forecast) actions (fails without the fix). `test_budget_action_single_move_keeps_short_text` now expects the French label "meilleur canal" (it builds a French action). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-drrs8a -> main
- **Décisions techniques :** `_actions` reuses `fact_label` from `agent/decision.py`; the action evidence is built from the same fact keys, so no new label table.
- **Problèmes / dette technique :** the values after the labels still come from the English business facts (e.g. "4 customers at high risk", "6,840 to Email", "up, YoY +20.7%"); localizing them needs structured values from `decision.py`. Target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors, not reachable from the CLI). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. Note for future runs: `mide sources add` without `--config-dir` writes to the repo `config/sources.yaml`; pass a temp config dir when trying the demo.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide ask` evidence labels follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #110 was already merged; suite green at start (420 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, the French `mide ask` printed its "Données utilisées" block with English labels: "forecast 30d", "trend", "top products", "flop products", "segment …", "churn", "channel Email", "underperforming", "best channel", "move Radio", "attribution check", "anomaly 1". They now read "prévision à 30 jours", "tendance", "meilleurs produits", "produits les plus faibles", "segment …", "risque de départ", "canal Email", "canaux marketing sous-performants", "meilleur canal", "transfert depuis Radio", "contrôle d'attribution", "anomalie 1". The English output is unchanged.
- **Fichiers principaux :** `mide/agent/decision.py`, `mide/report.py`, `tests/test_agent.py`
- **Tests :** 421 passed, 0 skipped. 1 new: FR/EN labels in `Recommendation.data_used` (fixed and parameterized keys: forecast, channel, move, anomaly), unknown keys kept as is, unknown language falls back to French. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-axtg7a -> main
- **Décisions techniques :** `fact_label` moved from `report.py` to `agent/decision.py` (one label table, `report.py` imports it, its output is unchanged) and extended to every fact key the business modules produce. Fact keys stay English, so the LLM prompt, the dashboard and the report data are unchanged; only the displayed labels are translated.
- **Problèmes / dette technique :** the values after the labels still come from the English business facts (e.g. "84 customers, 60.3% of revenue", "6,840 to Email, est. extra revenue up to …"); localizing them needs structured values from `decision.py`. Target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: report KPI, forecast and alert labels follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #109 was already merged; suite green at start (419 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, the French `mide report` printed English labels: "**revenue**", "**orders**", "**average order value**", "**30d growth**", "**forecast 30d**", and the alerts "churn: …" and "marketing underperforming: Radio, SMS". They now read "chiffre d'affaires", "commandes", "panier moyen", "croissance sur 30 jours", "prévision à 30 jours", "risque de départ: …" and "canaux marketing sous-performants: Radio, SMS" (Markdown and HTML). The English report is unchanged.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 420 passed, 0 skipped. 1 new: FR and EN labels in the Markdown report, a FR label in the HTML report, unknown keys kept as is, unknown language falls back to French (fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-gtw4zp -> main
- **Décisions techniques :** new `report._LABELS` and `fact_label(key, language)`, applied at render time to the KPI/forecast keys and when building the two alerts. `Report.kpis`/`forecasts` keep the stable English fact keys, so the agent facts, the dashboard and `decision.py` are unchanged.
- **Problèmes / dette technique :** the values after the labels and the action evidence still come from the English business facts (e.g. "735,907 for 2023-01-01 -> 2024-12-31", "4 customers at high risk", "trend: up"); localizing them needs structured values from `decision.py`. Target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` refuses a date column as target (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #108 was already merged; suite green at start (417 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, `mide train --dataset sales --target date` trained and saved a useless 729-class classifier over dates ("Modèle enregistré : sales-date v1", accuracy 0.002). A date target is now refused before any training with "Erreur : La colonne cible 'date' contient des dates : choisissez une colonne à prédire (montant, quantité…) et passez la date avec --date-column" (EN: "Error: Target column 'date' contains dates: pick a column to predict (amount, quantity…) and pass the date with --date-column"); no model is saved.
- **Fichiers principaux :** `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_task_detector.py`, `tests/test_registry.py`
- **Tests :** 419 passed, 0 skipped. 2 new: `detect_task` raises `TargetError("target_is_date")` on a text date target and on a parsed `datetime64` one, and still classifies `city`; FR/EN `mide train --target date` message with no model saved (both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-hhkaas -> main
- **Décisions techniques :** the check reuses the column profiler (`kind == "date"`), the same rule as `mide scan` and `--date-column`, so numeric targets are never affected. New `TargetError` code `target_is_date`, localized through `SOURCES_MESSAGES["target_target_is_date"]`; still a `ValueError`. `mide auto` only trains on numeric target candidates, so it is unchanged.
- **Problèmes / dette technique :** a text column the date parser accepts (e.g. month names) is now also refused as a target. Target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` on an identifier target gives a clear error (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #107 was already merged; suite green at start (415 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, `mide train --dataset customers --target customer_id` (a text id, so a classification task where every value is unique) crashed with the raw sklearn message "Erreur : n_splits=2 cannot be greater than the number of members in each class." It is now refused before any training with "Erreur : Chaque valeur de la colonne cible 'customer_id' est unique (un identifiant ?) : choisissez une colonne dont les valeurs se répètent" (EN: "Error: Every value of target column 'customer_id' is unique (an identifier?): pick a column whose values repeat"); no model is saved.
- **Fichiers principaux :** `mide/automl/trainer.py`, `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_trainer.py`, `tests/test_registry.py`
- **Tests :** 417 passed, 0 skipped. 2 new: `train` raises `TargetError("unique_values")` on a 30-row unique text target and still trains when classes repeat; FR/EN `mide train --target customer_id` message with no model saved (both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ayp1ah -> main
- **Décisions techniques :** the check lives in the trainer (after row sampling, where the folds are built), not in `detect_task`, so task detection and its callers are unchanged. It reuses `TargetError` (new code `unique_values`, localized through `SOURCES_MESSAGES["target_unique_values"]`), still a `ValueError`. Only the case "no class has 2 rows" is refused; targets with some repeated classes keep training as before.
- **Problèmes / dette technique :** `--target date` is accepted as a classification over dates (useless model, no crash). Target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train --date-column` refuses a column that does not hold dates (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #106 was already merged; suite green at start (413 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the demo data, `mide train --dataset sales --target amount --date-column product_id` silently trained a regression (the override was ignored), and `--date-column unit_price` read the prices as nanosecond timestamps, collapsed the series into one period and failed with the misleading "Pas assez de lignes pour entraîner (1)". An explicit date column that is not a date column (ids, numbers, the target itself) is now refused with "Erreur : La colonne 'unit_price' ne contient pas de dates : choisissez une colonne de date pour --date-column" (EN: "Error: Column 'unit_price' does not contain dates: pick a date column for --date-column"), for every task type, before any training.
- **Fichiers principaux :** `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_task_detector.py`, `tests/test_registry.py`
- **Tests :** 415 passed, 0 skipped. 2 new: `detect_task` rejects `product_id`, `unit_price`, the target and a classification case with a coded `TargetError("not_a_date")` and still accepts `date`; FR/EN `mide train --date-column unit_price` message with no model saved (both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-zyujb7 -> main
- **Décisions techniques :** the check reuses the column profiler (`kind == "date"`), the same rule `mide scan` uses, so numbers are never dates. New `TargetError` code `not_a_date` (`column` = the date column), localized through `SOURCES_MESSAGES["target_not_a_date"]`; still a `ValueError`, so `mide auto` and other callers are unchanged (they only pass detected date columns).
- **Problèmes / dette technique :** target leakage is still not detected (e.g. `quantity` vs `amount`). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` no longer crashes on integer class targets (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #105 was already merged; suite green at start (410 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). Bug found while exercising the CLI on the demo data: `mide train --dataset sales --target quantity` (an integer target with few values, so a classification task) trained the model and then failed with the cryptic "Erreur : unknown is not supported". `evaluate()` cast labels to an `object` array, which sklearn rejects when the labels are integers (text labels worked). It now scores on class codes (indices into `model.classes`, -1 for unseen labels), so integer and text labels both work, AUC included.
- **Fichiers principaux :** `mide/automl/evaluator.py`, `tests/test_registry.py`
- **Tests :** 413 passed, 0 skipped. 3 new: `evaluate` on binary and multi-class integer labels (accuracy + AUC), `mide train` on `sales.quantity` end to end (all 3 fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-gjfg3f -> main
- **Décisions techniques :** fix in the evaluator, not the trainer: `TrainedModel.predict` still returns the original labels, so saved models and callers are unchanged. Metric values for text labels are identical to before.
- **Problèmes / dette technique :** on the demo data `quantity` reaches accuracy 1 because `amount = quantity × unit_price` leaks the target; MIDE does not detect target leakage yet (possible backlog item). A non-date `--date-column` (e.g. `product_id`) is silently ignored for classification/regression. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: missing-source warning of `mide scan` / `mide index` / `mide auto` follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #104 was already merged; suite green at start (408 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). When an authorized folder or file no longer exists, `mide scan`, `mide index` and `mide auto` printed the raw English log line "Source not found: <path>" even with `language: fr`. They now print "Attention : source introuvable, ignorée : <path>" in French and "Warning: source not found, skipped: <path>" in English (stderr); the other sources are still processed.
- **Fichiers principaux :** `mide/cli.py`, `mide/ingestion/catalog.py`, `mide/rag/indexer.py`, `tests/test_ingestion.py`, `tests/test_store.py`
- **Tests :** 410 passed, 0 skipped. 2 new: FR/EN missing-source warning for `mide scan` and `mide index` (both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ay32c1 -> main
- **Décisions techniques :** new CLI helper `_warn_missing_sources()` (message `source_missing` in `SOURCES_MESSAGES`), called before the catalog/index work; the library-level `logger.warning` in `catalog.py`/`indexer.py` became `logger.debug` so the English line is not printed twice. SQL URLs are not checked (their errors are already reported per source).
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: unusable target errors of `mide train` follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #103 was already merged; suite green at start (406 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). `mide train` on an empty target column or a target with a single value printed "Erreur : Target column 'y' has no values" / "… has fewer than 2 distinct values" in English even with `language: fr`. In French it now reads "Erreur : La colonne cible 'y' ne contient aucune valeur" / "… a moins de 2 valeurs distinctes"; English output is unchanged.
- **Fichiers principaux :** `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_task_detector.py`, `tests/test_registry.py`
- **Tests :** 408 passed, 0 skipped. 2 new: `detect_task` raises a coded `TargetError` (empty, single text value, single integer value), FR/EN `mide train` messages for both cases (fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-hwz14b -> main
- **Décisions techniques :** new `TargetError(ValueError)` with `code` (`no_values`, `single_value`) and `column`, like `TrainingError`; `_error_text` localizes it through `SOURCES_MESSAGES` (`target_*`). It stays a `ValueError` with the same English `str()`, so existing callers (`mide auto`, tests) are unchanged.
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors, not reachable from the CLI). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard chart labels follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #102 was already merged; suite green at start (400 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). The three dashboard charts (weekly revenue, monthly revenue, ROI per channel) showed raw English field names in their axes and tooltips (`date`, `amount`, `channel`, `roi`) even with `language: fr`. They now show "Date", "Chiffre d'affaires", "Canal", "ROI" in French and "Date", "Revenue", "Channel", "ROI" in English.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 406 passed, 0 skipped. 6 new: `chart_series` translates the series name and index name without touching values or the input, the three dashboard series have labels, FR/EN field names in the Vega-Lite spec of the sales and marketing charts. The 4 AppTest cases fail without the fix. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-oxnr7s -> main
- **Décisions techniques :** new `dashboard_data.chart_series()` reusing `COLUMN_LABELS` (with new `date` and `amount` entries), applied only at display time, so `sales.py`/`marketing.py` keep their stable English names.
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard segment names and risk levels follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #101 was already merged; suite green at start (395 passed, `python3.13 -m pytest` after `pip install -e ".[dev,ui]"`). On the dashboard customers page, RFM segment names ("Loyal", "Hibernating"…) and churn risk levels (`low/medium/high`) stayed English with `language: fr`. In French they now read "Fidèles", "En sommeil", "À risque", "Nouveaux / prometteurs", "À surveiller", "Champions" and "faible / moyen / élevé"; English output is unchanged.
- **Fichiers principaux :** `mide/dashboard_data.py`, `tests/test_dashboard.py`
- **Tests :** 400 passed, 0 skipped. 5 new: every segment produced by `customers._segment` and every risk level has FR and EN labels, `value_label` only translates listed values of listed columns, `display_table` translates segments in the index and risk levels in a column without touching numbers or the input, FR/EN values on the dashboard customers page. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-floyxy -> main
- **Décisions techniques :** new `dashboard_data.VALUE_LABELS` (column → value → language) and `value_label()`; `display_table` applies it to columns and to the index, at display time only, so `customers.py`, the agent facts and the report keep the stable English values.
- **Problèmes / dette technique :** chart series names stay English. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard table column names follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #100 was already merged; suite green at start (388 passed after `pip install -e ".[dev,ui]"`). The tables of the dashboard (top/flop products, RFM segments, churn scores, channel performance) showed raw English column names (`share_pct`, `avg_recency_days`, `cost_per_conversion`…) even with `language: fr`. They now show readable labels in French ("Part (%)", "Récence moy. (jours)", "Coût par conversion") or English ("Share (%)", "Avg recency (days)", "Cost per conversion"). The index names (product, segment, customer, channel) are translated too.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 395 passed, 0 skipped. 7 new: every column label has FR and EN, `display_table` translates columns and index and keeps unknown columns and the input unchanged, every column of the four dashboard tables has a label, FR/EN columns on the marketing page, FR/EN columns on the customers page (with riskiest customers first). The 4 AppTest cases fail without the fix. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-2uftvp -> main
- **Décisions techniques :** new `dashboard_data.COLUMN_LABELS`, `column_label()` and `display_table()`; the translation is applied only at display time, so the business modules, charts and the report keep their stable English column names. The churn table is now sorted explicitly by `risk` instead of "the last column" (same order today, but no longer depends on column order).
- **Problèmes / dette technique :** cell values stay English (RFM segment names such as "Champions", risk levels `low/medium/high`, chart series names). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard budget move reasons follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #99 was already merged; suite green at start (383 passed). On the dashboard marketing page, the reason of each suggested budget move was English even with `language: fr` ("radio ROI -0.20 vs median 1.50; whatsapp returns 4.00 revenue per unit spent"). In French it now reads "ROI de radio -0.20 contre une médiane de 1.50 ; whatsapp rapporte 4.00 de chiffre d'affaires par unité dépensée"; English output is unchanged.
- **Fichiers principaux :** `mide/business/marketing.py`, `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 388 passed, 0 skipped. 5 new: English text equals `BudgetMove.reason` on the demo data, French text, a move without figures keeps its reason, FR/EN reasons on the dashboard marketing page. 4 of them fail without the fix (the English AppTest case passes both ways). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-yz4d6s -> main
- **Décisions techniques :** `BudgetMove` gets three optional fields (`from_roi`, `median_roi`, `to_roas`, default `None`) filled by `suggest_reallocation`, so the dashboard rebuilds the sentence instead of parsing English. New `dashboard_data.move_reason(move, language)` with a `move_reason` key in `UI_TEXT`; it falls back to `move.reason` when the figures are missing. `BudgetMove.reason` stays English for the agent facts and the report.
- **Problèmes / dette technique :** table column names in the dashboard are still English. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard anomaly alerts follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #98 was already merged; suite green at start (373 passed, 4 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The anomaly warnings on the dashboard home page were English even with `language: fr` ("drop on 2024-03-10: 1,200 vs 4,000 expected (-70%)"). In French they now read "chute le 2024-03-10 : 1,200 au lieu de 4,000 attendus (-70%)" or "pic du … au … : …"; English output is unchanged.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 383 passed, 0 skipped (`pip install -e ".[ui]"` this session so the Streamlit `AppTest` tests ran). 6 new: English text equals `Anomaly.describe()` (one day and a run of days), French text, unknown kind kept as is, FR/EN anomaly warnings on the dashboard with the demo data. 5 of them fail without the fix (the English AppTest case passes both ways). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-6s23ry -> main
- **Décisions techniques :** new `dashboard_data.anomaly_text(anomaly, language)` with `anomaly_*` keys in `UI_TEXT`. `Anomaly.describe()` is unchanged on purpose: `mide/report.py` parses its English text to date the anomalies, and the agent facts use it.
- **Problèmes / dette technique :** budget move reasons and table column names in the dashboard are still English. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard UI follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #97 was already merged; suite green at start (366 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The Streamlit dashboard (page names, headers, KPI labels, buttons, messages) was English only. With `language: fr` it now shows "Accueil", "Ventes", "Clients", "Marketing", "Poser une question", "Sources de données", "Matériel & modèles" and French labels everywhere; English output is unchanged. Pages are selected by a stable id, not by their label.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_dashboard.py`
- **Tests :** 377 passed, 0 skipped (`streamlit` installed this session, so the Streamlit `AppTest` tests ran too). 9 new: every label has FR and EN with the same placeholders, French fallback, page labels FR/EN, language from config and from a broken config, French/English dashboard header, info message and sidebar. The FR dashboard test fails without the fix. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-9nfumz -> main
- **Décisions techniques :** labels live in `dashboard_data.UI_TEXT` (testable without Streamlit), read with `ui_text(key, language, **values)`. `dashboard_language` reuses the CLI's `_cli_language`, so a broken `sources.yaml` still uses `default.yaml`'s language. The loading spinner moved from `st.cache_data` to `st.spinner` so its text can be translated.
- **Problèmes / dette technique :** values computed by the business modules stay English in the dashboard (anomaly descriptions, budget move reasons, table column names). "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: Ctrl+C in `mide chat` exits cleanly (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #96 was already merged; suite green at start (363 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). Pressing Ctrl+C in `mide chat` (at the `>` prompt or while the answer is being generated) ended with a Python `KeyboardInterrupt` traceback. It now prints "Au revoir." (or "Goodbye." with `language: en`) and exits with code 0, like `exit`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_chat.py`
- **Tests :** 366 passed, 2 skipped (3 new: Ctrl+C at the prompt in FR/EN, Ctrl+C during generation; all fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-yjc8bx -> main
- **Décisions techniques :** the question loop moved to a helper `_chat_loop`; `chat_command` catches `KeyboardInterrupt` around it. Ctrl+C during generation ends the session instead of only cancelling the current answer, which is the simplest predictable behaviour.
- **Problèmes / dette technique :** the dashboard UI (page names, labels) is still English only. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: dashboard config error follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #95 was already merged; suite green at start (360 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The Streamlit dashboard showed "Configuration error: Invalid YAML in …" in English even with `language: fr`. It now shows "Erreur de configuration : YAML invalide dans …" in French (same localized details as the CLI); English output is unchanged.
- **Fichiers principaux :** `mide/dashboard_data.py`, `app/dashboard.py`, `mide/cli.py`, `tests/test_dashboard.py`
- **Tests :** 363 passed, 2 skipped (3 new: FR/EN dashboard message with a broken `sources.yaml`, French fallback without `default.yaml`; all fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-s6lk3f -> main
- **Décisions techniques :** new `dashboard_data.config_error_message` (testable without Streamlit) reuses the CLI's `_error_text` and `_default_yaml_language`, since the full config cannot be loaded when it is broken. Message key `dashboard_config_error` in `SOURCES_MESSAGES`.
- **Problèmes / dette technique :** the rest of the dashboard UI (page names, labels) is still English only. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: config error details follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #94 was already merged; suite green at start (357 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). Config errors printed a French prefix with an English body ("Erreur : Invalid sources file …", "Erreur : Invalid YAML in …"). With `language: fr` they now read "Erreur : Fichier de sources invalide …", "YAML invalide dans …", "Configuration invalide dans …" or "… doit contenir un dictionnaire (clé: valeur) au premier niveau."; English output is unchanged.
- **Fichiers principaux :** `mide/config.py`, `mide/connectors/sources.py`, `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 360 passed, 2 skipped (3 new parametrized cases: invalid YAML, non-mapping file and unknown key in `models.yaml`, FR and EN; `test_broken_sources_file_gives_clear_error` now expects the French text. All 4 fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-91munq -> main
- **Décisions techniques :** `ConfigError` gets `code`, `path` and `detail`, like `TrainingError`; `_error_text` localizes it through `SOURCES_MESSAGES` (`config_*`). `str(exc)` keeps the exact English text. The `detail` (YAML parser / pydantic text) stays as is, since it is technical and points at the line or key.
- **Problèmes / dette technique :** the Streamlit dashboard still shows "Configuration error: …" in English. "Unknown profile" and "A time series task needs a date column" stay English (internal errors the CLI cannot reach). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: a broken `sources.yaml` gives a clear error (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #93 was already merged; suite green at start (356 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). With a malformed `sources.yaml`, `mide scan`, `mide sources list/add/remove` fell through to the last-resort handler and printed the mixed "Error: Erreur inattendue : Invalid sources file …", always in French even with `language: en`. They now print "Erreur : Invalid sources file …" (or "Error: …" in English) and exit with code 1, without touching the file. The last-resort handler (`run_safely`) also uses the "Erreur :" prefix in French instead of always "Error:".
- **Fichiers principaux :** `mide/cli.py`, `mide/utils/errors.py`, `tests/test_cli.py`, `tests/test_robustness.py`
- **Tests :** 357 passed, 2 skipped (1 new: FR/EN errors of the four commands with a broken `sources.yaml`; `test_run_safely_reports_clean_error` extended to check the FR/EN prefix. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-fcq49t -> main
- **Décisions techniques :** new helper `_authorized_sources` catches `ConfigError` like the other commands do. When the full config cannot be loaded, `_cli_language` and `run()` now read `language` from `default.yaml` alone (`_default_yaml_language`), so a broken `sources.yaml` or `models.yaml` no longer forces French. The detail of `ConfigError` stays English, as for the other config errors.
- **Problèmes / dette technique :** config error details ("Invalid sources file", "Invalid YAML in …") are still English behind the localized prefix. "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide models trained` follows the `language` setting and handles a broken config (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #92 was already merged; suite green at start (353 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). `mide models trained` printed raw English values ("[time_series] target=… beats_baseline=True") even with `language: fr`, crashed with a traceback on an invalid config, and would crash on a model whose metric is missing. In French each line now reads "sales-amount v1 [série temporelle] cible=amount mae=… bat_reference=oui"; English output is unchanged. An invalid config prints "Erreur : …" and exits with code 1; a missing score prints "?".
- **Fichiers principaux :** `mide/cli.py`, `tests/test_registry.py`
- **Tests :** 356 passed, 2 skipped (3 new: FR/EN lines of `mide models trained`, invalid config, missing score; all three fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-tir5nq -> main
- **Décisions techniques :** the line format lives in `SOURCES_MESSAGES` (`trained_line`, `yes`, `no`) and reuses the existing `task_*` names. The English line keeps the exact old format (`time_series`, `True`/`False`) so scripts parsing it still work.
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide ui` errors follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #91 was already merged; suite green at start (349 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). `mide ui` printed "Streamlit is not installed: pip install 'mide-engine[ui]'" and "Dashboard not found: …" in English only, although `language` defaults to `fr`. In French they now read "Erreur : Streamlit n'est pas installé : pip install 'mide-engine[ui]'" and "Erreur : tableau de bord introuvable : …"; in English they get the same "Error: " prefix as the other CLI errors.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_dashboard.py`
- **Tests :** 353 passed, 2 skipped (4 new: FR/EN error without Streamlit and FR/EN error when the dashboard script is missing; all four fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-83pb0v -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`ui_no_streamlit`, `ui_no_dashboard`). The language comes from `_cli_language`, so a broken config still gives a (French) message instead of a crash. The script path moved to a small `_dashboard_script()` helper so tests can point it at a missing file.
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: training errors of `mide train` follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #90 was already merged; suite green at start (348 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The remaining trainer errors listed as debt were English-only behind the French prefix, e.g. "Erreur : Not enough rows to train (3); at least 20 are needed". In French they now read "Erreur : Pas assez de lignes pour entraîner (3) ; il en faut au moins 20", "Erreur : Aucune colonne utilisable comme variable explicative" and "Erreur : La validation croisée a échoué : jeu de données trop petit ou dégénéré"; English unchanged with `language: en`.
- **Fichiers principaux :** `mide/automl/trainer.py`, `mide/cli.py`, `tests/test_trainer.py`, `tests/test_registry.py`
- **Tests :** 349 passed, 2 skipped (1 new CLI test: FR/EN errors for a 3-row dataset and a dataset with no feature column, fails without the fix; `test_errors` of the trainer extended to check the error codes). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-g0p0ap -> main
- **Décisions techniques :** new `TrainingError(ValueError)` with a stable `code` (`not_enough_rows`, `no_features`, `cv_failed`) and `n_rows`, like `TaskInfo.reason_code`. Its `str()` stays the English text, so library callers, logs and existing `except ValueError` code are unchanged. The CLI maps the code to `SOURCES_MESSAGES` in `_echo_error`, so any command printing a `TrainingError` is localized.
- **Problèmes / dette technique :** "Unknown profile" and "A time series task needs a date column" stay English (internal errors, not reachable from normal CLI use). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: "column not found" errors of `mide train` follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #89 was already merged; suite green at start (347 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). A mistyped `--target` or `--date-column` printed "Erreur : Target column 'amout' not found in dataset. Available columns: …" in English (listed as debt). In French it now reads "Erreur : Colonne cible 'amout' introuvable dans le jeu de données. Colonnes disponibles : …" (and "Colonne de date 'jour' …" for `--date-column`); English unchanged with `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_registry.py`
- **Tests :** 348 passed, 2 skipped (1 new: FR/EN error for a wrong target and a wrong date column; the French assertion of `test_cli_train_and_list` updated. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-mtieov -> main
- **Décisions techniques :** `mide/automl/task_detector.py` is unchanged (its English `ValueError` stays for library callers and logs). The CLI checks the columns itself before training (helper `_check_columns`, new `column_not_found` / `column_kind_*` keys in `SOURCES_MESSAGES`), so the user sees one fully localized message.
- **Problèmes / dette technique :** the remaining trainer errors ("Not enough rows to train", "No usable feature columns found", "Cross-validation failed…") are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: "dataset not found" and "model not installed" errors follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #88 was already merged; suite green at start (345 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). Two CLI errors were English-only although `language` defaults to `fr` (exception texts were listed as debt): `mide train --dataset <unknown>` printed "Erreur : Dataset not found in authorized sources: … Available datasets: …", and a missing LLM printed "Model not installed: run `mide models pull` (…)" (seen in `mide ask` without figures, `mide chat`, and inside the "LLM local indisponible (…)" note). In French they now read "Jeu de données introuvable dans les sources autorisées : nope. Jeux de données disponibles : sales" and "Modèle non installé : lancez `mide models pull` (…)"; English unchanged with `language: en`. Also, `mide finetune` on a LoRA-capable machine without an installed LLM used to fall through to the last-resort handler ("Error: Unexpected error: …"); it now prints the clear localized error and exits with code 1.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_registry.py`, `tests/test_lora.py`
- **Tests :** 347 passed, 2 skipped (2 new: FR/EN "dataset not found" error of `mide train`; FR/EN `mide finetune` with no installed LLM. The French assertion of `test_cli_train_and_list` updated. All three fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-db8a9v -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`dataset_not_found`, `dataset_hint`, `llm_missing`) like the other CLI texts. `_load_dataset` gets a `language` argument (default `fr`); `_get_llm` uses `cfg.language`.
- **Problèmes / dette technique :** other exception texts are still English-only (e.g. "Available columns:" from the trainer when the target column is wrong). The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` task line follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #87 was already merged; suite green at start (343 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The `mide train` line "Tâche : time_series - numeric target with date column 'date'" mixed French and English (task-detector reasons were listed as debt). In French it now reads "Tâche : série temporelle - cible numérique avec la colonne de date 'date'" (also "régression", "classification", and the non-numeric / few-integers / continuous reasons). English output is unchanged when `language: en`.
- **Fichiers principaux :** `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_task_detector.py`, `tests/test_cli.py`, `tests/test_registry.py`
- **Tests :** 345 passed, 2 skipped (2 new: reason code per detection rule; the FR/EN task line for every rule plus the fallback. The FR assertion of `test_cli_train_output_follows_language` now checks the translated reason. All three fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-x4gfy2 -> main
- **Décisions techniques :** `TaskInfo` gets a new `reason_code` field (default `""`, so existing callers and saved models are unaffected) set by each detection rule; `TaskInfo.reason` stays English for logs and metadata. The CLI translates from the code (helper `_task_line`, new `task_*` / `reason_*` keys in `SOURCES_MESSAGES`). An unknown code keeps the English reason, an unknown task keeps its raw value.
- **Problèmes / dette technique :** exception texts are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide auto` summary follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #86 was already merged; suite green at start (342 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The `mide auto` summary ("Scan: …", "Index: …", "Model <name>: <status> …") was English-only although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt). In French it now prints "Analyse : n jeux de données/documents.", "Indexation : 3 nouveaux, 0 mis à jour, … retirés." / "Indexation : ignorée (…)." and "Modèle <name> : remplacé|conservé|inchangé|ignoré|erreur (old -> new) <detail>"; English unchanged when `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 343 passed, 2 skipped (1 new test covering every outcome status in FR and EN; it fails without the fix. The assertion of `test_auto_without_rag_extra_still_retrains` updated to French because it runs with the default language). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-0e9aq3 -> main
- **Décisions techniques :** `mide/automl/auto.py` is unchanged: it still returns the status codes and English details, and the CLI translates them (new `auto_*` keys in `SOURCES_MESSAGES`, helper `_auto_outcome_line`). The three known details (promoted, kept, skipped) are translated; an `error` detail is an exception text and is shown as it is. Unknown statuses fall back to the raw code.
- **Problèmes / dette technique :** the task-detector reasons and the exception texts are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: one corrupt workbook no longer hides the rest of its folder (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #85 was already merged; suite green at start (339 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). Fixed the bug logged last session: `TabularConnector.discover()` opened every `.xlsx` to list its sheets, so one corrupt workbook raised and the whole folder was lost. `mide scan` reported the folder as one error, and `mide index` / `mide auto` skipped every file in it, including CSVs and documents. Now an unreadable workbook stays a single item. Only its own read fails, and it is reported as `[erreur] <path>/bad.xlsx : …` (kind `excel`), while the other files of the folder are scanned and indexed normally.
- **Fichiers principaux :** `mide/connectors/tabular.py`, `mide/ingestion/catalog.py`, `tests/test_tabular.py`, `tests/test_ingestion.py`, `tests/test_store.py`
- **Tests :** 342 passed, 2 skipped (3 new regression tests: connector discovery, catalog and index with a corrupt workbook next to good files. All three fail without the fix. The assertion of `test_scan_cli_follows_language` now expects the error on `bad.xlsx` instead of the folder). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-tof4uh -> main
- **Décisions techniques :** the corrupt workbook is kept as a bare-path item rather than silently dropped, so the error stays visible in `scan` and in the `index` report, and existing per-item error handling (`scan`, `index`, `auto`, `ask` data loading) covers it with no change. The warning log only contains the file name and the exception type (no data). Catalog error entries now carry the real kind (`excel`/`csv`) instead of always `csv`.
- **Problèmes / dette technique :** the `auto` summary lines, the task-detector reasons and the exception texts are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide index` summary and `mide scan` catalog lines follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #84 was already merged; suite green at start (337 passed, 2 skipped for missing `streamlit`, run with `python3.13 -m pytest` after `pip install -e ".[dev]"`). The `mide index` summary ("Indexed: … new chunks") and its per-item error lines, and the `mide scan` catalog lines (size, date columns, target candidates, errors) were English-only although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt). In French they now print "Indexation : 3 nouveaux, 0 mis à jour, 0 inchangés, 0 retirés (n nouveaux extraits).", "[erreur] <item> : …", " - n lignes x m colonnes", "colonnes de date : …" and "cibles possibles : …"; English is unchanged when `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_store.py`, `tests/test_ingestion.py`
- **Tests :** 339 passed, 2 skipped (2 new tests: `index` and `scan` in FR and EN, including an error line; the assertions of `test_cli_index` and `test_scan_cli` updated to French because they run with the default language. They fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ymdiit -> main
- **Décisions techniques :** messages added to `SOURCES_MESSAGES` (`index_done`, `item_error`, `scan_size`, `scan_dates`, `scan_targets`). `scan` takes its language from `_cli_language()` (French fallback for a broken config), `index` from the loaded config. Dataset kinds (`[table]`, `[document]`…) and the error texts themselves are left as they are. Behaviour and exit codes are unchanged.
- **Problèmes / dette technique :** one unreadable file (e.g. a corrupt `.xlsx`) makes `mide scan` report the whole folder as an error instead of only that file (found while writing the test; not changed here). The `auto` summary lines, the task-detector reasons and the exception texts are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: the generic "Error: …" prefix follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #83 was already merged; suite green at start (336 passed, 2 skipped for missing `streamlit`) once the dev dependencies were installed (`pip install -e ".[dev]"`, then `python3.13 -m pytest`). The generic error prefix printed by every command on failure (`models list/pull`, `index`, `train`, `ask`, `auto`, `chat`, `finetune`, `privacy`) was always "Error: …" although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt). It is now "Erreur : …" in French and unchanged "Error: …" in English.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 337 passed, 2 skipped (1 new test: `train` on an unknown dataset in FR and EN, plus five commands with a broken config. It fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-0llnye -> main
- **Décisions techniques :** one helper `_echo_error(exc, language)` with the `error` message in `SOURCES_MESSAGES`. When the config itself cannot be loaded (or may not have been loaded yet, e.g. in `train`/`chat`/`ask`), the language comes from `_cli_language()`, which falls back to French for a broken config. Only the prefix is translated: the exception texts (downloader, connectors, trainer) keep their English wording. Exit codes are unchanged.
- **Problèmes / dette technique :** the `index`/`auto` progress lines, the `scan` catalog lines, the task-detector reasons and the exception texts behind the prefix are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide models list/pull` messages follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #82 was already merged; suite green at start (334 passed, 2 skipped for missing `streamlit`) once the dev dependencies were installed (note: in this sandbox `python` is 3.11 while `pip` installs for 3.13, so tests must be run with `python3.13 -m pytest`). `mide models list` and `mide models pull` were English-only although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt). They now print "[installé]" / "[non installé]", the confirmation prompt "Télécharger <url> (<n> Go) depuis internet ?", "Modèle prêt : …" and "Erreur : aucun modèle configuré pour le profil '…'. Profils configurés : …" in French; English unchanged when `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_downloader.py`
- **Tests :** 336 passed, 2 skipped (new parametrized test covering list, confirmation prompt, download result and unknown profile in FR and EN; the assertions of `test_cli_pull_requires_confirmation` and `test_cli_pull_unknown_profile_lists_configured_profiles` updated to French because they run with the default language. They fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-5bkffp -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`models_*`). `_fmt_size` takes the language to print "Go" or "GB". Errors raised by the downloader itself (`DownloadError`, e.g. declined download, bad checksum) keep their English text behind the generic "Error: …" prefix. Behaviour, consent prompt and exit codes are unchanged.
- **Problèmes / dette technique :** the `index`/`auto` progress lines, the `scan` catalog lines, the task-detector reasons, the downloader error texts and the generic "Error: …" prefix are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide doctor` report follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #81 was already merged; suite green at start (333 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed (`PyYAML`/`cryptography`/`cffi` reinstalled with `--ignore-installed`). The `mide doctor` hardware report was English-only although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt). It now prints "RAM : … Go", "Cœurs CPU : …", "OS : …", "GPU : <name> (<n> Go de VRAM)" / "GPU : aucun", "Espace disque libre : … Go" and "Profil : …" in French; English unchanged when `language: en`. `mide doctor` gained the same `--config-dir` option as the other commands.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_profiler.py`
- **Tests :** 334 passed, 2 skipped (1 new test covering every doctor line in FR and EN, with a GPU; the assertion of `test_doctor_shows_report` updated from "Profile: small" to "Profil : small" because it runs with the default language. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-0iddst -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`doctor_*`). The language is read with `_cli_language()` so a broken config falls back to French and never blocks `doctor` (which is the command used to diagnose a broken install). The leading "OK" line is unchanged in both languages. Behaviour and exit code are unchanged.
- **Problèmes / dette technique :** `models list/pull`, the `index`/`auto` progress lines, the task-detector reasons and the generic "Error: …" prefix are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` result output follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #80 was already merged; suite green at start (332 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed (`PyYAML`/`cryptography`/`cffi` reinstalled with `--ignore-installed` because of the Debian builds). The `mide train` result lines were English-only although `language` defaults to `fr` (CLAUDE.md section 6; listed as debt by the previous session). They now print "Tâche : …", "Modèle enregistré : <name> v<n>", "  VC <metric> : … (référence …)", "Le modèle bat la référence." / "Le modèle ne bat PAS la référence." and "Variables principales : …" in French; English unchanged when `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_registry.py`
- **Tests :** 333 passed, 2 skipped (1 new test covering every train line in FR and EN; the assertion of `test_cli_train_and_list` updated from English to French because it runs with the default language. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-hc8a78 -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`train_task`, `train_saved`, `train_cv`, `train_beats`, `train_not_beats`, `train_top`). The task reason produced by `automl/task_detector.py` (e.g. "numeric target with date column 'date'") is still English; translating it needs a change in the detector API, left for a later session. Behaviour and exit codes are unchanged.
- **Problèmes / dette technique :** `doctor`, `models list/pull`, the `index`/`auto` progress lines, the task-detector reasons and the generic "Error: …" prefix are still English-only. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide models trained`, `mide auto` and `mide report` messages follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #79 was already merged; suite green at start (331 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. The "No trained models. Use `mide train --dataset X --target Y`." hint (`mide models trained`, `mide auto`) and the `mide report` messages ("Format must be 'md' or 'html'.", "Report written: …") were English-only although `language` defaults to `fr` (CLAUDE.md section 6; follow-up of the previous session). They now print "Aucun modèle entraîné. Utilisez `mide train --dataset X --target Y`.", "Le format doit être 'md' ou 'html'." and "Rapport écrit : …" in French, English unchanged when `language: en`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 332 passed, 2 skipped (1 new test covering the three messages in FR and EN; the assertion of `test_auto_without_rag_extra_still_retrains` updated from English to French because it runs with the default language. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-9c9azf -> main
- **Décisions techniques :** the messages live in `SOURCES_MESSAGES` (`no_models_hint`, `report_format`, `report_written`). The report format check runs before the config is loaded, so it uses `_cli_language()` (French fallback if the config is broken). Behaviour and exit codes are unchanged.
- **Problèmes / dette technique :** `doctor`, `models list/pull`, `train`, the `index`/`auto` progress lines and the generic "Error: …" prefix are still English-only; left for later sessions. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide scan/index/auto` "no authorized sources" hint follows the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #78 was already merged; suite green at start (330 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. With no authorized source, `mide scan`, `mide index` and `mide auto` always printed the English "No authorized sources. Use `mide sources add`." although `language` defaults to `fr` (CLAUDE.md section 6; follow-up of the previous session). They now print "Aucune source autorisée. Utilisez `mide sources add`." in French, English unchanged when `language: en`. Also removed an unreachable duplicate `raise typer.Exit(1)` in `mide sources remove`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 331 passed, 2 skipped (1 new test covering the three commands in FR and EN; the assertion of `test_auto_no_sources` updated from English to French because it runs with the default language. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-iiv2u0 -> main
- **Décisions techniques :** the message lives in `SOURCES_MESSAGES` (`none_hint`). `scan` reuses `_cli_language()` (French fallback if the config is broken); `index` and `auto` use the config they already loaded. Behaviour and exit codes are unchanged.
- **Problèmes / dette technique :** other CLI messages (`doctor`, `models`, `report`, `index`/`auto` progress output) are still English-only; left for later sessions. The report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide sources add/list/remove` messages follow the `language` setting (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #77 was already merged; suite green at start (329 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. The consent commands (`mide sources add/list/remove`) only spoke English although `language` defaults to `fr` (CLAUDE.md section 6). They now answer in the configured language: "Source ajoutée : …", "Source retirée : …", "Aucune source autorisée.", "Erreur : source non listée : … Sources autorisées : …", "Erreur : le chemin n'existe pas : …" and the French "do not put a password in the URL" error (English unchanged when `language: en`).
- **Fichiers principaux :** `mide/cli.py`, `tests/test_connectors_base.py`
- **Tests :** 330 passed, 2 skipped (1 new test covering every sources message in FR and EN; 3 assertions of existing sources tests updated from English to French because those tests run with the default language. The new test fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-wcxh6t -> main
- **Décisions techniques :** the language is read with `load_config(..., create_app_dir=False)`; if the config cannot be read, messages fall back to French so source management is never blocked by a broken `default.yaml`. Behaviour and exit codes are unchanged. The shared "No authorized sources. Use `mide sources add`." hint of `scan`/`index`/`auto` and other commands (`doctor`, `models`, `report`) are still English-only; left for later sessions.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide report --output` never overwrites a file of an authorized source (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #76 was already merged; suite green at start (326 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed (`PyYAML`, `cryptography`/`cffi` reinstalled with pip because the Debian builds were broken in the sandbox). `mide report --output <file>` wrote over any path, including a file of an authorized source: `mide report -o demo/sales.csv` replaced the user's sales data with the report, which breaks principle 3 (sources are read-only). The command now stops before reading any data with "Erreur : <file> fait partie de la source autorisée <source>. MIDE ne modifie jamais vos données ; choisissez un autre fichier de sortie." (English: "Error: <file> belongs to the authorized source <source>. MIDE never modifies your data; choose another output file.") and exit code 1.
- **Fichiers principaux :** `mide/connectors/sources.py` (new `source_owning()`), `mide/cli.py`, `tests/test_report.py`
- **Tests :** 329 passed, 2 skipped (3 new: the CLI refuses to overwrite a file inside an authorized folder and an authorized file, in FR and EN, and leaves both files byte-for-byte unchanged; `source_owning()` unit test. The CLI tests fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-6tdo69 -> main
- **Décisions techniques :** only existing files are protected (paths resolved, so symlinks and `..` are caught). Writing a NEW report file inside a source folder is still allowed, since it changes none of the user's files; note that the next `mide index` would then index that report. SQL URLs are skipped (no local file).
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide ask` / `mide chat` reject a `--source` that is not indexed (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #75 was already merged; suite green at start (324 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. `--source` filters the index on the exact item path, so a typo or a short name (`--source meeting.txt` instead of the full path) matched nothing: the LLM got a prompt with no excerpt and answered anyway, with no warning. Now `mide ask` and `mide chat` stop before the LLM with "Source non indexée : <x>. Sources indexées : <a>, <b>" (English: "Source not indexed: <x>. Indexed sources: ...", or "Empty index. Run `mide index`." when nothing is indexed) and exit code 1. The `--source` help now says it expects the item's full path.
- **Fichiers principaux :** `mide/rag/store.py` (new `VectorStore.items()`), `mide/cli.py`, `tests/test_retriever.py`
- **Tests :** 326 passed, 2 skipped (2 new: `items()` on an empty and an indexed store; unknown source in `ask` (FR) and `chat` (EN) exits 1, lists the indexed items and never calls the LLM, while the full path still works. The CLI test fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-eazqw1 -> main
- **Décisions techniques :** only the local index metadata is read (items already indexed from authorized sources). Matching stays exact; no fuzzy matching, so `--source` can never widen to another file. The dashboard does not pass a source, so it is unchanged.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide models pull` lists the configured profiles when the profile is unknown (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #74 was already merged; suite green at start (323 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed (`cryptography`/`cffi` reinstalled with pip because the Debian build was broken in the sandbox). `mide models pull --profile <name>` with a profile that has no model in `config/models.yaml` (a typo, or a profile removed from the file) only said "no model configured for profile '<name>'". The error now adds "Configured profiles: tiny, small, ..." (or "none"), in the same way as the fixes in #73 and #74.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_downloader.py`
- **Tests :** 324 passed, 2 skipped (1 new: an unknown profile exits 1, lists the configured profiles and opens no network connection; it fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-e5mrrg -> main
- **Décisions techniques :** only `models.yaml` is read. Nothing is downloaded on this error path and the exit code is still 1.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide sources remove` lists the authorized sources when the source is not listed (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #73 was already merged; suite green at start (322 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. `mide sources remove <path>` with a path that is not listed (a typo, or a different spelling of the path) only said "Error: source not listed: <path>", so the user had to run `mide sources list` to find the exact stored value. The error now adds "Authorized sources: <a>, <b>" (or "No authorized sources." when the list is empty), in the same way as the `mide train` fix in #73.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_connectors_base.py`
- **Tests :** 323 passed, 2 skipped (1 new: removing an unknown source exits 1 and shows "No authorized sources." when empty, then the listed source once one is added, and the list is unchanged; it fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-9j5p8r -> main
- **Décisions techniques :** only `sources.yaml` is read (the list the user consented to), no data source is opened. Exit code is still 1.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide train` lists valid names when a dataset or column is mistyped (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #72 was already merged; suite green at start (321 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. A mistyped `--target`, `--date-column` or `--dataset` in `mide train` only said "not found", so the user had to run `mide scan` to look up the right name. The errors now list the valid names, e.g. "Target column 'nope' not found in dataset. Available columns: order_id, date, customer_id, ..." and "Dataset not found in authorized sources: nope. Available datasets: campaigns, customers, products, sales".
- **Fichiers principaux :** `mide/automl/task_detector.py`, `mide/cli.py`, `tests/test_task_detector.py`, `tests/test_registry.py`
- **Tests :** 322 passed, 2 skipped (1 new test: unknown target and date column errors list the columns; `test_cli_train_and_list` now checks both CLI messages. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-i5xori -> main
- **Décisions techniques :** only names from authorized sources are listed (datasets that were already discovered while searching), so nothing outside the consented sources is read. Exit code is still 1.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide ask` rejects a blank question clearly (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #71 was already merged; suite green at start (320 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. `mide ask ""` (or a question of spaces) was routed to the documents: with an empty index it said "Index vide. Lancez `mide index`.", and with an index it sent an empty query to the retriever and the LLM. A blank question now stops before any data is loaded with "Question vide. Exemple : mide ask \"Quels produits se vendent le mieux ?\"" (English: "Empty question. Example: ...") and exit code 1. The dashboard uses the same `ask_answer` and shows the same message.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_retriever.py`
- **Tests :** 321 passed, 2 skipped (1 new: on an indexed workspace, `mide ask "   "` exits 1 with "Question vide" in French and "Empty question" in English, and never calls the LLM; it fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-81djxj -> main
- **Décisions techniques :** the check lives in `ask_answer` (shared by CLI and dashboard) as a new `EmptyQuestionError`; `mide chat` already skipped blank lines.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide auto` still retrains without the `[rag]` extra (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #70 was already merged; suite green at start (319 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Without `sentence-transformers` (the optional `[rag]` extra, also skipped by `MIDE_DEMO_SKIP_RAG=1` in the demo), `mide auto` stopped with "Error: sentence-transformers is not installed" before the retraining step, so the scheduled auto-learning did nothing at all on such a machine. This broke the graceful-degradation rule (CLAUDE.md §2.4). Now indexing is skipped with the reason ("Index: skipped (sentence-transformers is not installed. Install it with `pip install mide-engine[rag]`).") and the models are still checked and retrained.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 320 passed, 2 skipped (1 new: with the embedder raising `EmbeddingError`, `mide auto` exits 0, says the index was skipped and still calls the retraining on the source's datasets; it fails without the fix). `ruff check .` OK; `mypy mide` OK. Checked by hand on the demo workspace: "Model sales-amount: unchanged".
- **PR :** claude/wizardly-shannon-3oryop -> main
- **Décisions techniques :** only `EmbeddingError` (embedder unavailable) is caught; any other indexing error still stops `mide auto` with exit code 1, as before. `mide index` itself still fails clearly without the extra, since indexing is its only job.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide ui` help shows the `[ui]` install extra (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #69 was already merged; suite green at start (318 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. `mide --help` and `mide ui --help` said "needs `pip install mide-engine`": Rich markup treated `[ui]` as a style tag and dropped it, so a user following the hint would install the package without Streamlit. The bracket is now escaped in the docstring, and the help shows `pip install mide-engine[ui]`.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_cli.py`
- **Tests :** 319 passed, 2 skipped (1 new: `mide ui --help` contains `mide-engine[ui]` and no stray backslash; it fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-07ob61 -> main
- **Décisions techniques :** escaped the one affected docstring instead of turning off Rich markup for the whole CLI, so the rest of the help keeps its formatting. Error messages with `[rag]`/`[llm]`/`[finetune]` go through `typer.echo` (no markup) and were already correct.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: `mide privacy` shows readable storage sizes (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #68 was already merged; suite green at start (316 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. After the demo, `mide privacy` listed stored data as raw byte counts ("models_trained (888655 B)"), and a downloaded LLM would show as a 10-digit number. Sizes now use binary units in the user's language: "867.8 KB" in English, "867.8 Ko" in French ("0 B" / "0 o" for empty folders).
- **Fichiers principaux :** `mide/utils/privacy.py`, `tests/test_privacy.py`
- **Tests :** 318 passed, 2 skipped (2 new: `format_size` units and rounding in FR/EN; `mide privacy` on a 888,655-byte folder shows "867.8 Ko" and not the raw count; the CLI test fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-s3yc47 -> main
- **Décisions techniques :** display-only change; `StoredLocation.size_bytes` stays in bytes. Binary units (1 KB = 1024 B) match what file managers on Windows show.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: a top product is never also listed as a flop (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #67 was already merged; suite green at start (314 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. `product_ranking` took the top `n` and the bottom `n` products independently, so with fewer than `2 * n` products the same product was in both lists: with 2 products, `mide ask` said "flop products: B (25%), A (75%)", calling the best seller (75% of revenue) a flop. The dashboard (n=5) had the same overlap with fewer than 10 products. The flop list now only holds products left after the top; when none are left, the agent drops the "flop products" figure (the dashboard shows an empty table).
- **Fichiers principaux :** `mide/business/sales.py`, `mide/agent/decision.py`, `tests/test_sales.py`, `tests/test_agent.py`
- **Tests :** 316 passed, 2 skipped (2 new: 3 products with n=2 gives flop = [C] and n=3 gives no flop; 2 products give no "flop products" figure; both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-9fgpg3 -> main
- **Décisions techniques :** the demo data (10 products) is unchanged: top 2 and flop 2 do not overlap there. Top products take priority over flop ones when the catalog is small.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: customer answer lists every RFM segment, including "At risk" (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #66 was already merged; suite green at start (313 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed that "Which customers are at risk of churn?" listed only the top 3 RFM segments by revenue (Champions, Needs attention, Loyal: 237 of 400 customers). The "At risk" segment (44 customers, 9.1% of revenue), the one the question is about, was hidden without a word, as were Hibernating and New / promising. RFM has at most six segments, so all of them are now listed. This shows up in `mide ask`, the agent figures and the LLM prompt.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 314 passed, 2 skipped (1 new: on the demo data the six segments are listed, "At risk" reads "44 customers, 9.1% of revenue", and the counts add up to 400; it fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-7ixxnf -> main
- **Décisions techniques :** text-only change; RFM scoring, segment labels and their order (by revenue) are unchanged. The report does not use the segment figures, so it is unchanged.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. Sandbox note: `pip` here belongs to Python 3.13 while `python` is 3.11; run the tests with `/usr/bin/python3 -m pytest`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: churn action names every at-risk customer it can (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #65 was already merged; suite green at start (312 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed the churn figure behind priority action 1 ("Relancer les clients à risque") as "4 customers at high risk (top: C0093, C0320, C0348, ...)": one of the four customers to contact was hidden behind "...", which saves no space. Now, when only one name would be hidden, all are named; when more are hidden, the text says how many ("top: L5, L4, L3, +3 more"). This shows up in `mide ask`, the agent figures, the LLM prompt and the report.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 313 passed, 2 skipped (1 new test, 1 updated from "..." to "+3 more"; both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-1eiguh -> main
- **Décisions techniques :** text-only change; `churn_risk` and the order of customers (most valuable first) are unchanged. The cap of 3 named customers stays, plus one when that names everyone.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. Sandbox note: the Debian `cryptography` package needs `pip install --ignore-installed cffi cryptography` before `pypdf` imports work.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: average order value cites revenue / orders (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #64 was already merged; suite green at start (310 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed the KPI "average order value: 43" with nothing behind it, so the reader could not tell what was divided by what. It now reads "43 (735,907 / 17,037 orders)". This shows up in `mide ask`, the agent figures, the LLM prompt and the report's "Indicateurs clés".
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 312 passed, 2 skipped (2 new: exact text on the demo data and on a small synthetic table; both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-t9r5e8 -> main
- **Décisions techniques :** text-only change; `compute_kpis` is unchanged. The order count is the same one the "orders" KPI shows (unique `order_id`, or rows if there is none).
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: weekly report budget action lists every suggested move (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #63 was already merged; suite green at start (309 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed that the report's alerts name two underperforming channels ("Radio, SMS"), but priority action 2 only said "Reallocate budget from Radio" and dropped the SMS move (6,396 to Email, est. up to 269,460) without a word. The action now lists every suggested move: "Reallocate budget from Radio, SMS", with each move cited as "Radio: ...; SMS: ...". With a single move the text is unchanged. Applies to `mide report` (Markdown/HTML) and `mide auto`.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 310 passed, 2 skipped (1 new: single move keeps the short text; the demo-data test now checks both moves and fails without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-hmetoj -> main
- **Décisions techniques :** text-only change; the reallocation plan, the moves and the order of the actions are unchanged.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size (left for Dieudonné). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: churn figure cites its share of revenue and of the customer base (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #62 was already merged; suite green at start (307 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed the weekly report's priority action 1 as "churn: 4 customers at high risk (top: ...), 2,344 past revenue at risk". It did not say that this is 0.3% of revenue and 4 of 400 customers, so the reader could not judge why it ranks above a budget move worth far more. The churn figure now ends with "(0.3% of revenue; 4 of 400 customers)". This shows up in `mide ask`, the agent figures, the LLM prompt and the report's alert and action 1.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 309 passed, 2 skipped (2 new: exact scale text on a synthetic table and on the demo data). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-5ya21d -> main
- **Décisions techniques :** text-only change; churn scoring and the order of the report actions are unchanged. The share uses the revenue of all scored customers, which is the same basis as the RFM segment shares.
- **Problèmes / dette technique :** the report still ranks churn first whatever its size. Ranking the actions by estimated value would be a behaviour change, so it is left for Dieudonné to decide. The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: weekly report stock action cites the 30d forecast (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #61 was already merged; suite green at start (305 passed, 2 skipped for missing `streamlit`). Running `scripts/demo.sh` showed that priority action 3, "Surveiller la tendance des ventes et ajuster les stocks", cited only the past trend ("up, ... last 3 months +70.7%"). The report's own 30d forecast is -9.3%. Stock is bought for the coming weeks, so the action read as "stock up" when the forecast points down (the demo peaks in December). The action now ends with "; forecast 30d: 45,871 for 2025-01-01 -> 2025-01-30 (-9.3% vs previous 30d)" when a forecast exists. Applies to `mide report` (Markdown/HTML) and `mide auto`.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 307 passed, 2 skipped (2 new: exact evidence text on the demo data; action with and without a forecast. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-osjjp7 -> main
- **Décisions techniques :** text-only change; the actions, their order and the forecast itself are unchanged. Only the 30d horizon is cited, since it matches a weekly report and keeps the line short.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The sandbox's `pip` installs into Python 3.13 while `python` is 3.11; tests and the demo were run with `python3.13`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: weekly report budget action carries the attribution check (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #60 was already merged; suite green at start (303 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed that the "attribution check" added last session appears in `mide ask` but not in the weekly report. Priority action 2, "Réallouer le budget depuis Radio — ... est. extra revenue up to 285,353 ...", rests on a ROAS the engine itself flags as double-counted, and the report said nothing about it. When the marketing finding has an attribution check, the budget action now ends with "; attribution check: channels report 1,443,825 revenue, 1.96x total sales 735,907; ...". The same applies to the "Renforcer le canal le plus rentable" action. Applies to `mide report` (Markdown/HTML) and `mide auto`.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 305 passed, 2 skipped (2 new: exact evidence text of the demo reallocation action; best-channel action with and without a check. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-en7iy5 -> main
- **Décisions techniques :** text-only change; the actions, their order and the estimates are unchanged. The full check text is reused rather than a shorter summary, so report and `mide ask` say the same thing.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The sandbox's `pip` installs into Python 3.13 while `python` is 3.11; tests and the demo were run with `python3.13` (`PYTHON=python3.13`).
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: marketing figures flag channel revenue above total sales (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #59 was already merged; suite green at start (301 passed, 2 skipped for missing `streamlit`). The debt noted in the last two entries is that the demo channels report 1,443,825 revenue against 735,907 total sales. This also happens with real data when several channels claim the same sale. It was left as a demo-generator problem, but the engine said nothing about it, so "ROI 41.54" read as an absolute return. The marketing finding now adds an `attribution check` figure when a sales table is available and the channels claim more than total sales: "channels report 1,443,825 revenue, 1.96x total sales 735,907; the same sale is likely counted by several channels, so compare ROI/ROAS between channels rather than as absolute returns". It shows up in `mide ask`, the agent figures and the LLM prompt.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 303 passed, 2 skipped (2 new: exact warning text on the demo data, which fails without the fix; no warning when channel revenue is within total sales or there is no sales table). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-wujpu2 -> main
- **Décisions techniques :** the demo generator is unchanged, so the existing figures and tests still hold. The check compares whole tables rather than overlapping dates, which is enough for the demo (both cover 2023–2024) and stays simple. It is a caveat, not a correction: ROI/ROAS and the reallocation estimates are unchanged.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The sandbox's `pip` installs into Python 3.13 while `python` is 3.11; tests were run with `python3.13`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: product figures cite the revenue behind their share (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #58 was already merged; suite green at start (299 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed "top products: P001 Rice 25kg (43.2%), P002 Cooking oil 5L (13.5%)". It did not say 43.2% of what, or give the amount behind it. Each product now cites its revenue and the basis of the share: "P001 Rice 25kg (317,856 = 43.2% of revenue), P002 Cooking oil 5L (99,528 = 13.5% of revenue)". Flop products read the same way. The change shows up in `mide ask`, the agent figures and the LLM prompt.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 301 passed, 2 skipped (2 new: exact revenue/share text for the demo top and flop products; a sales table with no product catalog cites ids with revenue. Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-6p6r2o -> main
- **Décisions techniques :** text-only change; `product_ranking` is unchanged (it already returns `revenue`). The existing `startswith("P001 Rice 25kg (")` checks still hold.
- **Problèmes / dette technique :** campaign-attributed revenue on the demo data is still about twice total sales (see the previous entry). The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: channel figures cite the spend and revenue behind ROI/ROAS (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #57 was already merged; suite green at start (297 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed "channel Email: ROI 41.54, ROAS 42.54" with no amounts behind it. "ROI 41.54" can be read as 41.54% when it means revenue is 42x the spend. Each channel figure now cites its totals: "spend 16,089, revenue 684,450: ROI 41.54, ROAS 42.54". A channel with zero spend now shows "ROI n/a, ROAS n/a" instead of "nan". The change shows up in `mide ask`, the agent figures and the LLM prompt.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 299 passed, 2 skipped (2 new: exact spend/revenue/ratio text for every demo channel; zero-spend channel shows "n/a". Both fail without the fix). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-4z8kp4 -> main
- **Décisions techniques :** text-only change; `channel_performance` is unchanged. The totals come before the ratios, so "ROAS <x>" stays at the end of the text (the reallocation test still reads it from there).
- **Problèmes / dette technique :** on the demo data, campaign-attributed revenue (1,443,825 over all channels) is about twice total sales (735,907), so campaign revenue is not consistent with `sales.csv`. That is a demo-generator choice; I left it alone because changing the generator changes figures many tests rely on. The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: sales trend cites the months it compares (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #56 was already merged; suite green at start (294 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed "trend: up, YoY +20.7%, last 3 months +70.7%" next to "forecast 30d: ... (-9.3% vs previous 30d)". Neither growth figure said which months it compared, so the +70.7% (a strong Q4 against Q3) looked like it contradicted the forecast. The fact now reads "up, YoY +20.7% (2024-01 -> 2024-12 vs 2023-01 -> 2023-12), last 3 months +70.7% (2024-10 -> 2024-12 vs 2024-07 -> 2024-09)". Only complete months are counted: a partial last month is still left out. The change shows up in `mide ask`, the agent figures and the weekly report priority action "Surveiller la tendance des ventes".
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 297 passed, 2 skipped (3 new: exact month windows on the demo data, which fails without the fix; a partial December is left out of the windows; no window text when there are not enough months). In `test_sales_trend_cites_yoy_basis`, the check `yoy.endswith("%")` became `"%" in yoy` because the months now follow the figure. Its intent is kept. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-qo5amt -> main
- **Décisions techniques :** text-only change; `sales_trend` is unchanged (the months come from `Trend.monthly`). The text has no ", " inside the brackets, so the fact still splits into direction / YoY / recent parts.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: priority actions skip anomalies outside the 90-day window (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #55 was already merged; suite green at start (292 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Fixed the debt noted last session: the priority action "Analyser la cause de l'anomalie de ventes la plus récente" cited the latest anomaly even when the "Alertes" section had left it out as too old (demo data: 2024-09-03, 119 days before the last sale). The action is now proposed only for an anomaly that ends within `RECENT_ANOMALY_DAYS` (90) of the last sale, the same window as the alerts. On the demo data the third action is now "Surveiller la tendance des ventes et ajuster les stocks" (trend: up, YoY +20.7%, last 3 months +70.7%). Applies to `mide report` (Markdown/HTML) and `mide auto`; `mide ask` is unchanged.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 294 passed, 2 skipped (2 new: `_actions` window with a multi-day run, no filter without a sales date; no anomaly action on the demo data in FR/EN). `test_anomaly_action_cites_most_recent_anomaly` now uses demo sales cut at 2024-10-01, so the latest anomaly is recent; its intent is kept. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-1rj2mp -> main
- **Décisions techniques :** the window check is shared with the alerts (`_is_recent`), so the action and the alerts can never disagree. Anomalies whose date cannot be read are still kept.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: weekly report alerts list only recent anomalies (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #54 was already merged; suite green at start (290 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Fixed the debt noted in the last sessions: the "Alertes" section listed every anomaly the agent kept, back to 2023. Now it lists only anomalies that end within 90 days of the last sale, and adds one line counting the older ones. On the demo data (last sale 2024-12-31), all 4 anomalies are older, so the section reads "4 anomalie(s) plus ancienne(s) (avant le 2024-10-02) non listée(s)" (EN: "4 older anomalies (before 2024-10-02) not listed") instead of four 2023–2024 events. The change applies to `mide report` (Markdown and HTML) and `mide auto`. `mide ask` and the agent figures are unchanged.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 292 passed, 2 skipped (2 new: exact FR/EN wording, the cutoff uses the last day of a multi-day run, no filter without a sales date, unparseable text kept; old demo anomalies are not listed). `test_anomaly_action_cites_most_recent_alert` was renamed and now checks the action against the insights figures, because the alerts no longer list every anomaly. Its intent (the action cites the most recent anomaly) is kept. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-mtipjq -> main
- **Décisions techniques :** the 90-day window is measured from the last sale day, not the report date. The stale-data alert already covers the report date, and measuring from it would hide every anomaly in stale data. The window is a module constant (`RECENT_ANOMALY_DAYS = 90`), not a config key. The anomaly date is read from its description ("... on A -> B: ..."); text that does not match is kept.
- **Problèmes / dette technique :** the priority action "Analyser la cause de l'anomalie de ventes la plus récente" still cites the latest anomaly even when it is older than 90 days (on the demo data, 2024-09-03). I left it alone because changing the action ranking changes report behaviour. The six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-19 — Maintenance: weekly report warns when the data is stale (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #53 was already merged; suite green at start (288 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Fixed the debt noted in the last sessions: nothing warned that the data was old. On the demo data the report dated 2026-11-19 describes sales that end on 2024-12-31. When the last sale is more than 30 days before the report date, the "Alertes" section now starts with "données anciennes : dernière vente le 2024-12-31, 688 jours avant ce rapport ; les chiffres décrivent cette période, pas aujourd'hui" (EN: "stale data: last sale on 2024-12-31, 688 days before this report; figures describe that period, not today"). Shows up in `mide report` (Markdown and HTML) and in `mide auto`.
- **Fichiers principaux :** `mide/report.py`, `tests/test_report.py`
- **Tests :** 290 passed, 2 skipped (2 new: exact FR/EN alert text, 30-day threshold and missing sales table; alert comes first on the demo data and is absent when the data is fresh). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-qhkwpq -> main
- **Décisions techniques :** threshold is a module constant (`STALE_AFTER_DAYS = 30`), not a config key, to avoid a config change without validation. Unparseable dates are ignored. The alert is only added to the report, not to `mide ask` answers.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The weekly report "Alertes" still lists every historical anomaly (the last 5), not only recent ones.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: revenue and 30d growth cite the dates they cover (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #52 was already merged; suite green at start (286 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed (pip copies of `PyYAML`, `cryptography`, `cffi` over the Debian ones). Running `scripts/demo.sh` showed the KPIs "revenue: 735,907" and "30d growth: +10.4%" in a report dated 2026-11-18. Neither said which dates it covered: the total is all history and the growth is the last 30 days of data (to 2024-12-31), which a reader could take as the last 30 days before today. They now read "735,907 for 2023-01-01 -> 2024-12-31" and "+10.4% (30 days to 2024-12-31 vs previous 30)". This also shows how old the data is (part of the "data is stale" debt noted earlier). The change shows up in `mide ask`, the agent figures and the weekly report "Indicateurs clés" section.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 288 passed, 2 skipped (2 new: revenue/growth cite the exact data dates, which fails without the fix; growth stays "n/a" with no full previous period). `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-v01j1y -> main
- **Décisions techniques :** text-only change; `compute_kpis` is unchanged (it already stores `start`/`end`).
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The weekly report "Alertes" still lists every historical anomaly, not only recent ones. There is still no explicit warning when the last data day is far before the report date.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: forecast figures cite the period they cover (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #51 was already merged; suite green at start (285 passed, 2 skipped for missing `streamlit`) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed "forecast 30d: 45,871 (-9.3% vs previous 30d)" in a report dated 2026-11-18: the forecast starts the day after the last sales record (here 2025-01-01), not today, and nothing said which days it covered. A reader could take it as the next 30 days from today. The fact now reads "45,871 for 2025-01-01 -> 2025-01-30 (-9.3% vs previous 30d)". The change shows up in `mide ask`, the agent figures and the weekly report "Prévisions" section.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 286 passed, 2 skipped (1 new: exact start/end dates for the 30/60/90-day horizons; fails without the fix). Also green with `-W error`. `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ajmuyq -> main
- **Décisions techniques :** text-only change; `forecast_sales` is unchanged (it already forecasts from the last data day, which is right for a model trained on that history).
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The weekly report "Alertes" still lists every historical anomaly, not only recent ones. Nothing flags that the data is stale yet (in the demo, the last sale is almost 2 years before the report date).
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: churn figure names the most valuable at-risk customers (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #50 was already merged; suite green at start (283 passed, 2 skipped for missing `streamlit`, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed that the answer to "Which customers are at risk of churn?" and the report action "Relancer les clients à risque de départ" only gave a count ("4 customers at high risk"), never saying whom to contact. The churn figure now names up to 3 high-risk customers, most valuable first: "4 customers at high risk (top: C0093, C0320, C0348, ...), 2,344 past revenue at risk". It flows into `mide ask`, the agent figures and the weekly report.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 285 passed, 2 skipped (2 new: names in value order with "..." when more exist, no "..." otherwise; the first fails without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-4qe6ap -> main
- **Décisions techniques :** text-only change; `churn_risk` is unchanged (it already sorts high-risk customers by past revenue). Ids only: the customers table has no name column in the demo data.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The weekly report "Alertes" still lists every historical anomaly, not only recent ones.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: budget reallocation estimate flagged as a linear upper bound (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #49 was already merged; suite green at start (284 passed, also with `-W error`; `ruff` and `mypy` OK) once the sandbox dependencies were installed. Running `scripts/demo.sh` showed the marketing figure "move Radio: 6,840 to Email, est. extra revenue 285,353": moving 6.8k of budget would add revenue equal to ~39% of total sales. The estimate is linear at Email's average ROAS (42.54), which `suggest_reallocation` documents as optimistic, but nothing told the user. The figure now reads "est. extra revenue up to 285,353 (linear, at Email ROAS 42.54; returns diminish)"; it flows into `mide ask`, the agent figures and the weekly report action. The dashboard says "linear upper bound" too.
- **Fichiers principaux :** `mide/agent/decision.py`, `app/dashboard.py`, `tests/test_agent.py`
- **Tests :** 285 passed (1 new: the move figure says "up to", cites the ROAS it uses and the diminishing returns; fails without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ga9fqi -> main
- **Décisions techniques :** text-only change; the estimate calculation is unchanged (a saturation model would change behaviour and needs Dieudonné's decision).
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The weekly report "Alertes" lists every anomaly in the history (back to 2023), not only recent ones; left as is, as it would change report behaviour.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: anomaly figures show a signed deviation (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #48 was already merged; suite green at start (283 passed, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed the anomaly alert "spike on 2024-03-08: 3,962 vs 1,265 expected (313%)": the percentage was actual/expected, so it read as a +313% spike when sales were in fact +213% above expected, and drops read "(4%)" for a -96% fall. `Anomaly.describe()` now prints the signed deviation ("(+213%)", "(-96%)"), which flows into `mide ask`, the agent figures, the weekly report alerts/actions and the dashboard.
- **Fichiers principaux :** `mide/business/insights.py`, `tests/test_insights.py`
- **Tests :** 284 passed (1 new: exact spike/drop wording, fails without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-ad4noj -> main
- **Décisions techniques :** text-only change; `Anomaly.ratio` (actual/expected) and detection are unchanged.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. `scripts/demo.sh` uses `python3` by default; in this sandbox it must be run with `PYTHON=python3.13`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: trend figure cites its YoY basis (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #47 was already merged; suite green at start (278 passed, 2 skipped for missing `streamlit`, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed the sales fact "trend: up, last 3 months +70.7%": the direction "up" is actually computed from year-over-year growth (+20.7%), which was never shown, so a reader could not see what "up" was based on (principle 5, explainability). The fact now reads "up, YoY +20.7%, last 3 months +70.7%" (YoY only when 24 months of data exist). The insights "orders" figure now uses a thousands separator ("17,037") like the other amounts.
- **Fichiers principaux :** `mide/agent/decision.py`, `tests/test_agent.py`
- **Tests :** 281 passed, 2 skipped (3 new: YoY cited, short history without YoY, orders formatting; two of them fail without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-4mxxwj -> main
- **Décisions techniques :** text-only change to the finding; `sales_trend` logic unchanged. The -9.3% 30-day forecast next to +70.7% recent growth is not a bug: the demo data peaks in Oct–Dec and the forecast covers January.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The sandbox's `pip` installs into Python 3.13 while `python` is 3.11; tests were run with `python3.13`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: cite product names in sales figures (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Merged PR #46 first (suite green: 275 passed, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed that top/flop products were cited by id only ("P001 (43.2%)"), which a business user cannot read. When an authorized product catalog (columns `product_id` + `name`) is present, `detect_tables` now picks it up as `BusinessData.products`, and the sales figures read "P001 Rice 25kg (43.2%)". Without a catalog, output is unchanged (ids only). The dashboard Sales page shows a `name` column in the top/flop tables too.
- **Fichiers principaux :** `mide/business/sales.py` (`product_names`, `product_ranking(names=...)`), `mide/agent/decision.py`, `mide/dashboard_data.py`, `app/dashboard.py`, `tests/test_sales.py`, `tests/test_agent.py`, `tests/test_dashboard.py`
- **Tests :** 280 passed (5 new: catalog name mapping, ranking with names, catalog detection, finding cites names, fallback to ids without catalog; dashboard test now also authorizes the products file); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-2ekjz2 -> main
- **Décisions techniques :** the catalog is used only if the user authorized it as a source (no extra reads). Module builders now receive the whole `BusinessData`, so a module can use secondary tables.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: priority-action questions and latest-anomaly action (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. PR #45 was already merged; suite green at start (268 passed, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed two bugs: (1) demo question 5 "What are my 3 priority actions this week?" was routed to RAG only and failed ("Index vide"); the router now sends action/priority/recommendation questions (FR/EN, word-start match so "transactions" does not match) to all four business modules, like `mide report`. (2) The report action "Investigate the cause of the latest sales anomaly" cited the *oldest* anomaly (2023-06-14) because anomalies are chronological and it used `anomaly 1`; it now cites the last one (2024-09-03). The agent also keeps the 5 most recent anomalies instead of the 5 oldest.
- **Fichiers principaux :** `mide/agent/router.py`, `mide/agent/decision.py`, `mide/report.py`, `tests/test_agent.py`, `tests/test_report.py`
- **Tests :** 275 passed (7 new: 4 action-routing cases, "transactions" negative case, most-recent anomalies kept, report cites latest anomaly; the new ones fail without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK. Demo step 6 now answers all 5 questions.
- **PR :** #46 (merged)
- **Décisions techniques :** action questions skip RAG unless document keywords are present (same rule as other business questions).
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-18 — Maintenance: `mide ask` answers business questions without an LLM (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Suite green at start (265 passed, also with `-W error`; `ruff` and `mypy` OK). Running `scripts/demo.sh` showed that all business questions in step 6 fail when no LLM weights are installed ("Model not installed"), although the agent computes the figures deterministically. Applying principle 4 (graceful degradation): when business findings exist but the LLM is not installed, `ask_answer` now returns a bilingual note ("Local LLM unavailable (...). Here are the computed figures...") plus the usual "Data used" figures, with exit code 0. Questions that need documents only still fail with the same clear error as before.
- **Fichiers principaux :** `mide/cli.py`, `tests/test_agent.py`
- **Tests :** 268 passed (3 new: FR CLI fallback, EN `ask_answer` fallback, documents-only question still raises; the first two fail without the fix); also green with `-W error`; `ruff check .` OK; `mypy mide` OK.
- **PR :** claude/wizardly-shannon-m1xbqi -> main
- **Décisions techniques :** fallback lives in `ask_answer`, so the CLI and the dashboard (which reuse it) both benefit. `mide chat` is unchanged: it always needs the LLM for conversation.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged. The router sends "What are my 3 priority actions this week?" to RAG only; it could also route to `insights` (left as is, would change routing behaviour).
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-17 — Maintenance: fix mypy type errors (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Suite was green at start (264 passed, also with `-W error`; `ruff` OK), but `mypy mide` (part of the quality stack in CLAUDE.md §5) reported 21 errors in 5 files. Fixed with annotations only, no behaviour change: LightGBM params dict typed `dict[str, Any]` (`automl/trainer.py`), file fingerprint dict typed (`rag/indexer.py`), Chroma embeddings passed as the list type Chroma declares (`rag/store.py`), `list_models` accepts any `Mapping` (`llm/downloader.py`, profile keys are `Literal`s), and connector variables in `cli.py` typed `SQLConnector | TabularConnector`.
- **Fichiers principaux :** `mide/automl/trainer.py`, `mide/rag/indexer.py`, `mide/rag/store.py`, `mide/llm/downloader.py`, `mide/cli.py`, `tests/test_typecheck.py`
- **Tests :** 265 passed (new `test_typecheck.py` runs mypy on `mide/` and fails on the old code; skipped if mypy is not installed); also green with `-W error`; `ruff check .` OK; `mypy mide`: no issues.
- **PR :** claude/wizardly-shannon-pzqsgw -> main
- **Décisions techniques :** mypy is run through a pytest test, so `pytest` (required before every commit) also guards typing.
- **Problèmes / dette technique :** the six stale PRs (#15, #17, #20, #21, #24, #26) are still open and should be closed, not merged.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-16 — Maintenance: close SQL connections (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Suite was green at start (262 passed), but `pytest -W error` exposed 4 failures from `ResourceWarning: unclosed database`: `SQLConnector` never disposed its SQLAlchemy engine, so pooled connections leaked after `mide scan`, `mide index`, `mide train`, `mide report`/`auto`. Added `SQLConnector.close()` (idempotent) and context-manager support; `ingestion/catalog.py`, `rag/indexer.py` and `cli.py` (`_load_dataset`, `_load_all_datasets`) now close it. Tests also fixed: SQL tests use a closing fixture, and `test_ingestion` used `with sqlite3.connect(...)` (commits but does not close) — now wrapped in `contextlib.closing`.
- **Fichiers principaux :** `mide/connectors/sql.py`, `mide/ingestion/catalog.py`, `mide/rag/indexer.py`, `mide/cli.py`, `tests/test_sql.py`, `tests/test_ingestion.py`
- **Tests :** 264 passed (2 new: connector close + catalog closes connections, both fail without the fix); also 264 passed with `-W error`; `ruff check .` OK.
- **PR :** claude/wizardly-shannon-g81s8b -> main
- **Décisions techniques :** did not add `filterwarnings = error` to the pytest config, since third-party warnings in other environments could break the suite.
- **Problèmes / dette technique :** six stale PRs from early sessions are still open (#15, #17, #20, #21, #24, #26); their tasks already landed on `main` through later PRs. They should be closed, not merged (merging would conflict/regress). Sandbox note: `pip` installs to Python 3.13 while `python` is 3.11 — run tests with `python3.13 -m pytest`.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-16 — Maintenance: remove pandas 4 deprecation warnings (no roadmap task left)
- **Fait :** Every ROADMAP task is checked and the backlog question is still open, so no new task was started. Test suite was green at session start (261 passed). Fixed the tech debt noted in W4-06: `scripts/make_demo_data.py` used `DatetimeIndex.dayofyear` / `dayofweek`, deprecated in pandas 3 and removed in pandas 4; replaced with `day_of_year` / `day_of_week` (available since pandas 1.1, output unchanged). New test fails if demo generation raises any `DeprecationWarning`/`FutureWarning`.
- **Fichiers principaux :** `scripts/make_demo_data.py`, `tests/test_demo_data.py`
- **Tests :** 262 passed, 0 warnings (previously 8); `ruff check .` OK.
- **PR :** claude/wizardly-shannon-opmu51 -> main
- **Décisions techniques :** none (same values, new attribute names).
- **Problèmes / dette technique :** sandbox setup still needs `pip install --ignore-installed PyYAML cffi cryptography` before `pip install -e ".[dev,ui]"` (environment only, not the project).
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-15 — Maintenance: fix failing memory test (no roadmap task left)
- **Fait :** Every ROADMAP task is checked, and the backlog needs validation first, so no new task was started. Per §7 step 2 the broken test was fixed: `test_chunked_metadata_uses_less_memory_than_full_read` failed with pandas 3.x (Arrow-backed strings make a full read of the fixture smaller than one 50k-row chunk). `TabularConnector.metadata()` now counts CSV rows by reading only the first column in chunks, and infers dtypes from a 10k-row sample (peak memory about halved). Excel is unchanged.
- **Fichiers principaux :** `mide/connectors/tabular.py`, `tests/test_robustness.py`
- **Tests :** 261 passed (new: header-only CSV metadata); `ruff check .` OK. `tests/test_files.py` is collectable again after reinstalling `cffi`/`cryptography` in the sandbox.
- **PR :** task/maintenance-csv-metadata-memory -> main
- **Décisions techniques :** dtypes now come from the first 10k rows instead of the first 50k-row chunk; types inferred only further down the file may differ.
- **Problèmes / dette technique :** none new.
- **Prochaine tâche :** none. Waiting for Dieudonné to pick a backlog item (see questions).

### 2026-11-14 — W4-08 Final demo
- **Fait :** `scripts/demo.sh` runs data generation, consent, scan, index, train, 5 business questions and the weekly report in an isolated workspace (own `MIDE_HOME` and config copy). Index and `ask` steps are optional and never stop the demo (no model/rag extra on small setups).
- **Fichiers principaux :** `scripts/demo.sh`, `tests/test_demo_script.py`, `README.md`
- **Tests :** 258 passed, 2 skipped
- **PR :** task/W4-08-final-demo -> main
- **Décisions techniques :** `ask` is skipped (with a message) when the LLM is not pulled, since tests/demo must never download weights without confirmation.
- **Problèmes / dette technique :** `ask` answers in the demo need `mide models pull` first. Roadmap complete.
- **Prochaine tâche :** none (backlog needs validation)

### 2026-11-14 — W4-07 Documentation
- **Fait :** Full bilingual `README.md` (EN + FR): installation (scripts, pip, Docker), demo quick start, adding sources, command table, configuration, architecture, limits, privacy FAQ. Demo steps were run end to end (sources add, scan, train `sales`/`amount`, report); `ask`/`chat` need the LLM weights (`mide models pull`), documented.
- **Fichiers principaux :** `README.md`, `tests/test_readme.py`
- **Tests :** 249 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK.
- **PR :** voir la PR vers `main` (branche `task/W4-07-documentation`)
- **Décisions techniques :** `test_readme.py` checks every CLI command appears in the README so docs cannot drift.
- **Problèmes / dette technique :** the French section references the English command table instead of duplicating it.
- **Prochaine tâche :** W4-08 — Démo finale

### 2026-11-14 — W4-06 Packaging
- **Fait :** `Dockerfile` (+ `.dockerignore`, `scripts/docker-entrypoint.sh`; `docker run ... mide-engine demo` generates the demo data, authorizes it, scans and reports), `scripts/install.sh` (Linux/macOS) and `scripts/install.ps1` (Windows) creating a venv in `~/.mide/venv`. `pip install` of the wheel now works outside a checkout: default YAML files are shipped in `mide/_defaults/` and seeded into `<MIDE_HOME>/config` on first use (the repo `config/` is still used in a source checkout).
- **Fichiers principaux :** `Dockerfile`, `scripts/install.*`, `mide/config.py`, `mide/connectors/sources.py`, `mide/_defaults/`, `tests/test_packaging.py`
- **Tests :** 246 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK. Wheel installed in a clean venv and demo data scanned with `mide sources add` / `mide scan`.
- **PR :** voir la PR vers `main` (branche `task/W4-06-packaging`)
- **Décisions techniques :** duplicated the three config files in `mide/_defaults/` (a test enforces they stay identical to `config/`) rather than moving `config/`, to keep the documented layout.
- **Problèmes / dette technique :** `docker build` could NOT be run here (no Docker daemon in the sandbox) — the acceptance criterion "docker build OK" is unverified; please run `docker build -t mide-engine .` locally. Demo script emits pandas 4 deprecation warnings (`dayofyear`, `dayofweek`).
- **Prochaine tâche :** W4-07 — Documentation

### 2026-11-14 — W4-05 Security and privacy
- **Fait :** Audit of network use, source consent, SQL read-only mode and logging. New `mide privacy` command (`mide/utils/privacy.py`): lists authorized sources (database credentials masked), local storage folders with sizes, network and read-only policy (FR/EN). Log lines in `cli.py` and the indexer now carry the exception type only, never its message (which can contain row data). Test that blocks all socket access during `mide ask`.
- **Fichiers principaux :** `mide/utils/privacy.py`, `mide/cli.py`, `mide/rag/indexer.py`, `tests/test_privacy.py`
- **Tests :** 239 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK.
- **PR :** voir la PR vers `main` (branche `task/W4-05-security-privacy`)
- **Décisions techniques :** the network test patches `socket` (connect, create_connection, getaddrinfo); SQL read-only was already enforced (W2/W3, `tests/test_sql.py`).
- **Problèmes / dette technique :** `report.errors[item] = str(exc)` in the indexer is shown to the user, not logged; kept as is.
- **Prochaine tâche :** W4-06 — Packaging

### 2026-11-14 — W4-04 Performance and robustness
- **Fait :** `TabularConnector.read_chunks()` (chunked CSV reading); `metadata()` now counts rows in chunks instead of loading the whole file (the catalog previously read each file twice in full). `mide/utils/errors.py`: bilingual FR/EN friendly messages (missing file, permission, encoding, empty/malformed file, out of memory, network) and `run_safely`; the console script is now `mide.cli:run`, which prints a clear error instead of a traceback. `mide/utils/perf.py`: `measure()` (time + peak memory).
- **Fichiers principaux :** `mide/connectors/tabular.py`, `mide/utils/errors.py`, `mide/utils/perf.py`, `mide/cli.py`, `tests/test_robustness.py`
- **Tests :** 234 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK. Demo dataset catalog peak allocation is asserted far below the 4 GB budget; chunked metadata uses less memory than a full read.
- **PR :** voir la PR vers `main` (branche `task/W4-04-performance-robustness`)
- **Décisions techniques :** memory measured with `tracemalloc` (Python allocations) to stay portable; Excel cannot be streamed by pandas, so it is read once then sliced.
- **Problèmes / dette technique :** other modules (trainer, indexer) still load full DataFrames; only the tabular connector/catalog path is chunked. `tests/test_files.py` still uncollectable here (env `cryptography` issue).
- **Prochaine tâche :** W4-05 — Sécurité et confidentialité

### 2026-11-14 — W4-03 Optional LoRA fine-tuning
- **Fait :** `mide/llm/lora.py`: availability check (GPU + medium/large profile + `[finetune]` extra, FR/EN message "fine-tuning unavailable, RAG is used"), Q/A dataset generation from authorized documents with the local LLM, deterministic train/held-out split, injectable trainer/scorer, before/after evaluation (adapter activated only if the held-out score improves), PEFT trainer (lazy imports). New command `mide finetune`.
- **Fichiers principaux :** `mide/llm/lora.py`, `mide/cli.py`, `tests/test_lora.py`
- **Tests :** 228 passés ; `ruff check .` OK. Unavailable path, activation, rejection and not-enough-data are covered with fakes (no torch, no model).
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-zc2npq`, empilée sur W4-02)
- **Décisions techniques :** trainer and scorer are injected so the pipeline is testable without GPU; the adapter is only recorded in `~/.mide/lora/active_adapter.json` when it wins.
- **Problèmes / dette technique :** the real PEFT trainer is untested (needs GPU, `# pragma: no cover`). The CLI scorer is a placeholder returning 0.0, so `mide finetune` never activates an adapter yet: a real scorer (answer overlap on held-out questions with the adapter loaded in llama.cpp) is still to write. The runtime does not load the active adapter yet.
- **Prochaine tâche :** W4-04 — Performance et robustesse

### 2026-11-14 — W4-02 Weekly report
- **Fait :** `mide/report.py` (`build_report`, `render_markdown`, `render_html`) and `mide report [--format md|html] [--output FILE]`. Sections: key indicators, forecasts, alerts (anomalies, churn, underperforming channels), 3 priority actions each with its source figures. FR/EN following `language`.
- **Fichiers principaux :** `mide/report.py`, `mide/cli.py`, `tests/test_report.py`
- **Tests :** 211 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-ttl1l9`, empilée sur W4-01)
- **Décisions techniques :** the report is fully deterministic (reuses the decision-agent findings, no LLM call) so it works on `tiny` machines and needs no model download; HTML output is escaped.
- **Problèmes / dette technique :** action ranking is rule-based (churn > marketing > anomaly > trend). Not yet exposed in the dashboard.
- **Prochaine tâche :** W4-03 — Fine-tuning LoRA optionnel

### 2026-11-14 — W4-01 Streamlit dashboard
- **Fait :** `app/dashboard.py` with 7 pages (Home KPIs/anomalies, Sales, Customers, Marketing, Ask a question, Data sources add/remove, Hardware & models) and `mide ui` (launches Streamlit with usage stats disabled, `--config-dir` forwarded via `MIDE_CONFIG_DIR`). Data logic lives in `mide/dashboard_data.py` (no Streamlit import, unit-tested). The body of `mide ask` was extracted into `cli.ask_answer()` so CLI and dashboard share it.
- **Fichiers principaux :** `app/dashboard.py`, `mide/dashboard_data.py`, `mide/cli.py`, `pyproject.toml` (new extra `[ui]`), `tests/test_dashboard.py`
- **Tests :** 206 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK. Pages are exercised with `streamlit.testing.AppTest` on the demo data and on an empty config.
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-wjbujy`, empilée sur W3-09)
- **Décisions techniques :** Streamlit is an optional extra (`pip install mide-engine[ui]`) to keep the base install light; the dashboard only reads authorized sources and caches the load (refresh button / source edits invalidate it).
- **Problèmes / dette technique :** `app/` is not part of the installed Python package, so `mide ui` works from a repo checkout only (packaging is W4-06). In this sandbox pytest needs `/usr/bin/python3 -m pip install -e ".[dev,ui]"` first.
- **Prochaine tâche :** W4-02 — Rapport hebdomadaire

### 2026-11-14 — W3-09 Scheduled auto-learning
- **Fait :** `automl/auto.py` (`retrain_if_changed`, `fingerprint`, `AutoReport`) and `mide auto`: scan -> incremental indexing -> retrain registered models only when their dataset content changed -> promote the new version only if it beats the previous one on its primary metric, otherwise keep the old one -> report. `mide train` now stores `dataset` and `data_hash` in the model metadata.
- **Fichiers principaux :** `mide/automl/auto.py`, `mide/cli.py`, `tests/test_auto.py`, `tests/test_cli.py`
- **Tests :** 199 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-pnu5qf`, empilée sur W3-08)
- **Décisions techniques :** only models already trained via `mide train` are retrained (no automatic target guessing); data fingerprint = pandas row hash, stored in `~/.mide/auto_state.json` so a rejected candidate is not retrained on every run; one failing model is reported and does not stop the run.
- **Problèmes / dette technique :** scheduling itself is left to cron/Task Scheduler calling `mide auto`. Metric comparison is on the training CV score of the primary metric (not a held-out set). Use `/usr/bin/python3` for pytest in this sandbox.
- **Prochaine tâche :** W4-01 — Dashboard Streamlit

### 2026-11-14 — W3-08 Decision agent
- **Fait :** `agent/router.py` (`route_question`: FR/EN keyword routing to RAG, business modules, or both), `agent/decision.py` (`detect_tables`, `run_modules` -> `Finding`s with figures, `build_decision_prompt`, `recommend`; `Recommendation.data_used()` always appends the source figures, independent of LLM output). `mide ask` now uses the agent; pure document questions behave as before.
- **Fichiers principaux :** `mide/agent/router.py`, `mide/agent/decision.py`, `mide/cli.py`, `tests/test_agent.py`
- **Tests :** 194 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-5yr9v3`, empilée sur W3-07)
- **Décisions techniques :** keyword router (no LLM call, deterministic, works on `tiny`); business-only questions skip the index so they work without `mide index`; if no usable business table is found, falls back to RAG. Sales/campaign tables are detected by column names.
- **Problèmes / dette technique :** keyword lists are coarse (no semantic routing). `mide chat` still RAG-only. Sandbox needed `python -m pip install -e ".[dev]"` (PATH `pytest` used another Python).
- **Prochaine tâche :** W3-09 — Auto-apprentissage planifié

### 2026-11-14 — W3-07 Insights & anomalies
- **Fait :** `business/insights.py`: `compute_kpis` (revenue, orders, average order value, customers, last-30d vs previous-30d growth, best day), `detect_anomalies` (drops/spikes on the daily series, consecutive days merged into one `Anomaly` with actual/expected/ratio/score), `analyze` (KPIs + anomalies).
- **Fichiers principaux :** `mide/business/insights.py`, `tests/test_insights.py`
- **Tests :** 182 passés (hors `tests/test_files.py`, voir W3-06) ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-b4e2ck`, empilée sur W3-06)
- **Décisions techniques :** expected value = weekday factor x centered 29-day rolling median (absorbs trend and season); robust MAD z-score (threshold 4) plus a minimum 40% deviation to avoid flagging noise. Finds all 3 planted demo anomalies with at most 2 extra detections.
- **Problèmes / dette technique :** `tests/test_files.py` still not collectable in this sandbox (environment issue). Not wired into the CLI yet (W3-08).
- **Prochaine tâche :** W3-08 — Agent décisionnel

### 2026-11-14 — W3-06 Marketing module
- **Fait :** `business/marketing.py`: `channel_performance` and `campaign_performance` (spend, revenue, ROI, ROAS, cost per conversion, conversion rate, CTR), `underperforming_channels`, `suggest_reallocation` (`ReallocationPlan` with `BudgetMove`s: part of weak channels' budget moved to the best-ROAS channel, with reason and estimated extra revenue).
- **Fichiers principaux :** `mide/business/marketing.py`, `tests/test_marketing.py`
- **Tests :** 174 passés (hors `tests/test_files.py`, voir ci-dessous) ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-a1wkmu`, empilée sur W3-05)
- **Décisions techniques :** underperformance is measured against the median channel ROI (a spend-weighted baseline wrongly flagged Facebook/Google Ads because Email/WhatsApp dominate). Extra-revenue estimate is linear (average ROAS of the receiving channel), hence optimistic; at most 50% of a weak channel's budget moves.
- **Problèmes / dette technique :** `tests/test_files.py` could not be collected in this sandbox (system `cryptography` lacks `_cffi_backend`; environment issue, not code). Not wired into the CLI yet (W3-08).
- **Prochaine tâche :** W3-07 — Insights & anomalies

### 2026-11-14 — W3-05 Customers module
- **Fait :** `business/customers.py`: `customer_table` (recency, frequency, monetary, typical purchase gap per customer), `rfm_segments` (1-5 rank-quantile scores + named segments: Champions, Loyal, New / promising, At risk, Hibernating, Needs attention), `segment_summary` (customers, revenue, revenue share per segment), `churn_risk` (risk in [0,1] from silence relative to each customer's own purchase rhythm; `ChurnReport` with high-risk customers and revenue at risk).
- **Fichiers principaux :** `mide/business/customers.py`, `tests/test_customers.py`
- **Tests :** 174 passés / 174 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-nu241q`)
- **Décisions techniques :** rank-based quantiles (robust to ties/skew) instead of `qcut`; churn is a transparent heuristic (risk = 1 - 0.5^(recency/(3 x typical gap))), not a trained model, so it works on any dataset and stays explainable. Single-order customers use the population median gap.
- **Problèmes / dette technique :** heuristic not validated against real churn labels; not yet wired into the CLI (planned with the agent, W3-08). Pre-existing pandas deprecation warnings in `scripts/make_demo_data.py`.
- **Prochaine tâche :** W3-06 — Module marketing

### 2026-11-13 — W3-04 Sales module
- **Fait :** `business/sales.py`: `forecast_sales` (30/60/90-day forecast: linear trend + weekday + yearly Fourier terms by least squares, anomalous days >3 sigma excluded from the fit, growth vs previous period), `product_ranking` (top/flop with revenue share), `sales_trend` (monthly totals, last-3-months and YoY growth, direction), `detect_seasonality` (monthly/weekday indices after detrending, peak/trough, yearly seasonality flag).
- **Fichiers principaux :** `mide/business/sales.py`, `tests/test_sales.py`
- **Tests :** 168 passés / 168 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-nu3qlz`, empilée sur W3-03 / PR #25)
- **Décisions techniques :** numpy least squares instead of statsmodels/Prophet (no new dependency, fast on `tiny`). Column names default to `date`/`amount`/`product_id`, overridable. Partial last month ignored in trend.
- **Problèmes / dette technique :** no prediction intervals; one yearly harmonic only; not yet wired into the CLI (planned with the agent, W3-08).
- **Prochaine tâche :** W3-05 — Module clients

### 2026-11-13 — W3-03 Evaluation + model registry
- **Fait :** `automl/evaluator.py`: `evaluate(model, df)` (regression/time series: MAE, MAPE, RMSE, R2; classification: accuracy, macro-F1, AUC binary/OvR) and `feature_importance`. `automl/registry.py`: versioned save/load/list in `~/.mide/models_trained/<name>/vN/` (joblib model + `metadata.json` with task, target, CV metrics, baseline, top features). CLI: `mide train --dataset X --target Y` (authorized sources only) and `mide models trained`.
- **Fichiers principaux :** `mide/automl/evaluator.py`, `mide/automl/registry.py`, `mide/cli.py`, `tests/test_registry.py`
- **Tests :** 161 passés / 161 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-j3c5qa`, empilée sur W3-02)
- **Décisions techniques :** joblib (bundled with scikit-learn) for persistence; model name = `<dataset>-<target>` slugified, version auto-incremented. Importance reuses LightGBM split importance from training.
- **Problèmes / dette technique :** joblib files are only safe to load from the local registry (never from untrusted sources). `evaluate` on training data is optimistic; CV metrics are the honest ones. No `mide predict` command yet.
- **Prochaine tâche :** W3-04 — Module ventes

### 2026-11-13 — W3-02 AutoML trainer
- **Fait :** `automl/trainer.py`: `train(df, target, profile, seed, task, date_column)` returns a `TrainedModel` (predict, CV metrics, baseline metrics, `beats_baseline`, feature importance). Automatic preparation: identifier-like text columns dropped, categoricals encoded (unseen -> -1), date features (year/month/weekday/day-of-year/day/ordinal), NaN left to LightGBM. Time series are aggregated per period and validated with `TimeSeriesSplit`; other tasks use (Stratified)KFold. Baselines: mean (regression), majority class, last value (time series). Limits per hardware profile (trees, leaves, row cap, folds, threads).
- **Fichiers principaux :** `mide/automl/trainer.py`, `tests/test_trainer.py`, `pyproject.toml` (+ scikit-learn, lightgbm)
- **Tests :** 154 passés / 154 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-0a1csg`, empilée sur W3-01 / PR #22)
- **Décisions techniques :** `deterministic=True`, single seed -> reproducible metrics. `task` override added to `train` (answers W3-01 debt: plain regression on dated rows). Classification primary metric is accuracy (macro-F1 also reported). Models are fitted in CV then refit on all data.
- **Problèmes / dette technique :** no hyperparameter search; no time budget enforcement beyond tree/row caps; time-series model has no lag features (trees cannot extrapolate trends). Tests run with `python -m pytest` in a venv.
- **Prochaine tâche :** W3-03 — Évaluation + registre de modèles

### 2026-11-13 — W3-01 Task type detection
- **Fait :** `automl/task_detector.py`: `detect_task(df, target, date_column=None)` returns a `TaskInfo` (task, reason, date column, frequency, number of classes). Non-numeric/boolean targets and integer targets with <= 10 values -> classification; continuous numeric target with a date column (>= 10 distinct dates) -> time series (frequency D/W/MS); otherwise regression. Clear errors for unknown target/date column or constant target.
- **Fichiers principaux :** `mide/automl/task_detector.py`, `tests/test_task_detector.py`
- **Tests :** 145 passés / 145 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-emrktx`, empilée sur W2-07 / PR #19)
- **Décisions techniques :** thresholds are module constants. Date columns come from the existing profiler; an explicit `date_column` overrides. Time series is chosen whenever a date column exists, so a caller wanting plain regression on dated rows must pass the task explicitly later (trainer, W3-02).
- **Problèmes / dette technique :** no `task` override parameter yet; a numeric column with few integer values (e.g. quantity 1-5) is treated as classification. Tests had to run in a venv (system python lacks deps). Work done on the session branch because pushes are restricted to it.
- **Prochaine tâche :** W3-02 — Entraîneur AutoML

### 2026-11-13 — W2-07 Conversation mode
- **Fait :** `llm/chat.py` (`ChatHistory`: keeps the last N turns within a character budget, cuts an oversized single turn instead of dropping it). `build_rag_prompt` accepts a rendered history (FR/EN "previous conversation" section). `mide chat [--source] [--top-k]`: interactive loop, fresh retrieval at each turn, sources listed after each answer, `exit`/`/clear` commands, EOF-safe.
- **Fichiers principaux :** `mide/llm/chat.py`, `mide/llm/prompts.py`, `mide/cli.py`, `tests/test_chat.py`
- **Tests :** 136 passés / 136 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-6vo1y7`, empilée sur W2-06 / PR #18)
- **Décisions techniques :** defaults of 3 turns / 1500 chars keep the prompt within the `tiny` profile 2048-token context. Retrieval uses only the current question (no query rewriting with history) to stay simple and predictable; follow-up questions that rely on pronouns may retrieve poorly.
- **Problèmes / dette technique :** no query rewriting for follow-ups; no streaming output yet (`LLM.stream` exists). Work done on the session branch because pushes are restricted to it.
- **Prochaine tâche :** W3-01 — Détection du type de tâche

### 2026-11-13 — W2-06 Retriever + answers with sources
- **Fait :** `rag/retriever.py` (`Retriever`: top-k, optional per-item filter, numbered `Passage` with human-readable citation: file, table, page, lines). `llm/prompts.py` (FR/EN RAG prompt with numbered excerpts, sources footer). `mide ask "question" [--source] [--top-k]`: retrieves, prompts the local LLM, prints the answer then the cited sources. Clear errors for an empty index or a missing model.
- **Fichiers principaux :** `mide/rag/retriever.py`, `mide/llm/prompts.py`, `mide/cli.py`, `tests/test_retriever.py`
- **Tests :** 130 passés / 130 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/clever-bell-5ei4dj`)
- **Décisions techniques :** the sources footer is built from retrieved passages (not parsed from the LLM output), so sources are always listed even if the small model forgets the `[n]` markers. `--source` filters on the indexed item key (path or SQL URL).
- **Problèmes / dette technique :** e5 `query:` prefix still not applied. Branch stacked on W2-05 (PR #16); work done on the session branch rather than `task/W2-06-*` because pushes are restricted to it.
- **Prochaine tâche :** W2-07 — Mode conversation

### 2026-11-13 — W2-05 Vector index + incremental indexing
- **Fait :** `rag/store.py` (`VectorStore`: persistent Chroma collection in `~/.mide/index/`, cosine, telemetry disabled, add/delete_item/query with optional item filter). `rag/indexer.py` (`index_sources`: documents chunked, tables/SQL tables summarized, only new or modified items re-embedded; vanished items and revoked sources pruned; per-item errors reported, not raised). `mide index` command.
- **Fichiers principaux :** `mide/rag/store.py`, `mide/rag/indexer.py`, `mide/cli.py`, `tests/test_store.py`, `pyproject.toml`
- **Tests :** 126 passés / 126 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `task/W2-05-vector-index`)
- **Décisions techniques :** change detection = sha256, recomputed only when mtime/size changed (a touched file with identical content is not reindexed). `chromadb` added to core dependencies (listed in the CLAUDE.md stack). Indexing logic put in a new `indexer.py` to keep `store.py` a pure storage layer. Pruning removes chunks of revoked sources (consent principle).
- **Problèmes / dette technique :** SQL table fingerprint = schema + row count + hash of the first 1000 rows, so changes deeper in a large table with equal row count are not detected. PDF page numbers not yet passed to the index (DocumentConnector returns joined text). Branch stacked on W2-04 (PR #14). Sandbox had no deps installed: used a venv.
- **Prochaine tâche :** W2-06 — Retriever + réponses avec sources

### 2026-11-13 — W2-04 Chunking
- **Fait :** `rag/chunking.py`: `chunk_text` (size + overlap, cuts on whitespace, metadata source/chunk_index/line_start/line_end/page), `chunk_pages` (page numbers), `summarize_table` (schema chunk + statistics chunk built from `profile_dataframe`). `chunk_size` / `chunk_overlap` added to `config/default.yaml` and `GeneralConfig`.
- **Fichiers principaux :** `mide/rag/chunking.py`, `tests/test_chunking.py`, `mide/config.py`, `config/default.yaml`
- **Tests :** 117 passés / 117 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-c2d17s`)
- **Décisions techniques :** character-based sizes (no tokenizer dependency); table summaries are capped at 30 columns to stay small on tiny machines.
- **Problèmes / dette technique :** `DocumentConnector.read` returns joined PDF text, so page numbers are only available via `chunk_pages` (to be wired in W2-05). Branch stacked on W2-03. Environment note: system `cryptography` was broken for Python 3.11 in the sandbox; reinstalled locally, no repo change.
- **Prochaine tâche :** W2-05 — Index vectoriel + indexation incrémentale

### 2026-11-13 — W2-03 Embeddings
- **Fait :** `rag/embeddings.py`: `Embedder` protocol, `SentenceTransformerEmbedder` (lazy import, injectable loader, batched, normalised vectors), `FakeEmbedder` (deterministic hashed bag-of-words, unit norm), `embedding_model_for_profile` (reads `models.yaml`), `load_embedder` with batch size per profile (tiny 8 → large 64). `fake_embedder` fixture in `tests/conftest.py`.
- **Fichiers principaux :** `mide/rag/embeddings.py`, `tests/test_embeddings.py`, `pyproject.toml`
- **Tests :** 108 passés / 108 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-pcvwrb`)
- **Décisions techniques :** `sentence-transformers` added as optional extra `[rag]` (pulls torch, heavy) and imported lazily so base install and tests stay light; model names stay in `config/models.yaml`.
- **Problèmes / dette technique :** the real model path is only tested via a stub loader. Branch stacked on W2-02 (PR #11). e5 models expect `query:`/`passage:` prefixes; to handle in W2-05/W2-06.
- **Prochaine tâche :** W2-04 — Chunking

### 2026-11-13 — W2-02 Local LLM runtime
- **Fait :** `llm/runtime.py`: `LLM` protocol (`generate`, `stream`), `LlamaCppLLM` wrapper (lazy `llama_cpp` import, injectable loader), `params_for_hardware` (context per profile, threads = cores-1, GPU offload only if a GPU exists), `FakeLLM`, `load_llm`. `fake_llm` fixture in `tests/conftest.py`.
- **Fichiers principaux :** `mide/llm/runtime.py`, `tests/test_runtime.py`, `pyproject.toml`
- **Tests :** 97 passés / 97 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-kem5g6`)
- **Décisions techniques :** `llama-cpp-python` added as optional extra `[llm]` (compiles from source, heavy) and imported lazily so the base install and tests stay light; a clear error points to the extra. Stack unchanged otherwise.
- **Problèmes / dette technique :** real llama.cpp path is only tested through a mocked loader. Branch stacked on W2-01 (PR #10).
- **Prochaine tâche :** W2-03 — Embeddings

### 2026-11-13 — W2-01 Model download and management
- **Fait :** `llm/downloader.py` (`download_model`, `list_models`): stdlib `urllib` download from Hugging Face into `~/.mide/models/`, mandatory confirmation callback called before any byte is written, progress callback, `.part` file then atomic move, size check (Content-Length / expected) and optional SHA-256, cleanup on failure, path-traversal guard. CLI: `mide models list`, `mide models pull [--profile] [--yes]`.
- **Fichiers principaux :** `mide/llm/downloader.py`, `mide/cli.py`, `tests/test_downloader.py`
- **Tests :** 89 passés / 89 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-unu180`)
- **Décisions techniques :** no new dependency (urllib instead of huggingface_hub/requests); all downloads mocked via an injectable opener. Without `--yes`, `pull` asks interactively.
- **Problèmes / dette technique :** `models.yaml` has no hash/size per model, so integrity relies on Content-Length unless hashes are added later. Branch stacked on W1-09 (PR #9). Tests run with `python3.13`.
- **Prochaine tâche :** W2-02 — Runtime LLM local

### 2026-11-13 — W1-09 Demo dataset
- **Fait :** `scripts/make_demo_data.py` (`generate_demo_data(out_dir, seed)`): fictional SME with 2 years of sales (~14k orders), products, customers, monthly campaigns for 6 channels, 3 markdown documents (annual report, 2 meeting notes), and `anomalies.json`. Trend (+25%/yr), yearly seasonality (Dec peak, Aug dip), weekly pattern, 3 deliberate anomalies (2 drops, 1 spike), SMS as under-performing channel, P009 as flop product. Session-scoped `demo_data` fixture in `tests/conftest.py`.
- **Fichiers principaux :** `scripts/make_demo_data.py`, `tests/test_demo_data.py`, `tests/conftest.py`
- **Tests :** 81 passés / 81 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `task/W1-09-demo-data`)
- **Décisions techniques :** fully seeded numpy generator, byte-identical output per seed. Test module loads the script by path since `scripts/` is not a package.
- **Problèmes / dette technique :** branch stacked on W1-08 (PR #8). W1-08 tests still use an in-test table; could be switched to the demo data. Tests run with `python3.13` in this sandbox.
- **Prochaine tâche :** W2-01 — Téléchargement et gestion des modèles

### 2026-11-13 — W1-08 Catalog and data profiling
- **Fait :** `ingestion/profiling.py` (column kind numeric/date/boolean/categorical/text, % missing, date detection incl. string dates, target candidates by FR/EN name keywords, ID columns excluded); `ingestion/catalog.py` (`build_catalog`: inventory of CSV/Excel sheets, SQL tables, documents across authorized sources only; unreadable items reported as errors, not fatal); `mide scan` command.
- **Fichiers principaux :** `mide/ingestion/profiling.py`, `mide/ingestion/catalog.py`, `mide/cli.py`, `tests/test_ingestion.py`
- **Tests :** 73 passés / 73 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `task/W1-08-catalog-profiling`)
- **Décisions techniques :** profiling uses a sample of at most 5000 rows to bound memory; row counts come from connector metadata. Target candidates are name-based heuristics (keywords), refined later by the task detector (W3-01).
- **Problèmes / dette technique :** the demo dataset (W1-09) does not exist yet, so tests use a synthetic in-test sales table; they should be switched to the demo data once W1-09 lands. Branch is stacked on W1-07 (PR #7). Tests run with `python3.13` in this sandbox.
- **Prochaine tâche :** W1-09 — Jeu de données de démonstration

### 2026-11-13 — W1-07 SQL connector
- **Fait :** `connectors/sql.py` (`SQLConnector`): SQLAlchemy engine for SQLite/PostgreSQL/MySQL/SQL Server URLs, table discovery, schema + row count metadata, sample, chunked reads. Read-only enforced twice: statement validation (single SELECT/WITH only, comments/literals stripped) and SQLite `PRAGMA query_only`. Credentials via `${VAR}` placeholders in the URL, expanded only at connection time (the URL stored in `sources.yaml` holds no secret). URL must be an authorized source.
- **Fichiers principaux :** `mide/connectors/sql.py`, `tests/test_sql.py`, `pyproject.toml` (added `SQLAlchemy`)
- **Tests :** 66 passés / 66 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-9f8ve5`)
- **Décisions techniques :** keyword-based write blocking is conservative (e.g. a column named `copy` would be refused); the real guarantee for server databases is to use a read-only DB account. DB drivers (psycopg, pymysql, pyodbc) are not bundled to keep install light; users install the one they need.
- **Problèmes / dette technique :** this branch is stacked on W1-06 (PR #6, not merged yet). Only SQLite is exercised in tests. In this sandbox `python` is 3.11 while deps are installed for `python3.13`.
- **Prochaine tâche :** W1-08 — Catalogue et profilage des données

### 2026-11-13 — W1-06 Document connectors (folders, TXT/MD, DOCX, PDF)
- **Fait :** `connectors/files.py` (`DocumentConnector`): recursive walk of an authorized folder, extension filter, configurable max file size, TXT/MD (UTF-8 or Latin-1), DOCX (`python-docx`), PDF (`pypdf`); `read_all()` skips corrupted files with a log warning. `.txt` removed from the tabular connector (resolves W1-05 debt).
- **Fichiers principaux :** `mide/connectors/files.py`, `mide/connectors/tabular.py`, `tests/test_files.py`, `pyproject.toml` (added `pypdf`, `python-docx`)
- **Tests :** 51 passés / 51 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `task/W1-06-documents-connector`)
- **Décisions techniques :** authorization is re-checked on every read; oversized files are skipped with a warning rather than failing the scan.
- **Problèmes / dette technique :** the sandbox's system `cryptography` package was broken (missing `_cffi_backend`); fixed locally with `pip install --ignore-installed cryptography cffi`, not a repo issue. Max size is a constructor parameter; wiring it to `config.general.max_file_size_mb` is left for the ingestion step (W1-08).
- **Prochaine tâche :** W1-07 — SQL connector

### 2026-11-13 — W1-05 Tabular connector (CSV / Excel)
- **Fait :** `connectors/tabular.py` (`TabularConnector`): CSV separator detection (`,` `;` tab `|`), encoding detection (UTF-8/BOM, else Latin-1), XLSX with every sheet exposed as `path::sheet`; authorization re-checked on every read.
- **Fichiers principaux :** `mide/connectors/tabular.py`, `tests/test_tabular.py`, `pyproject.toml` (added `pandas`, `openpyxl`)
- **Tests :** 44 passés / 44 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-3xbahq`)
- **Décisions techniques :** no `chardet` dependency (keeps install light): UTF-8 strict check with Latin-1 fallback is enough for FR/EN data. Files are never written to.
- **Problèmes / dette technique :** `.txt` files are treated as CSV by this connector; W1-06 may need to carve them out for documents. Run tests with `python -m pytest`.
- **Prochaine tâche :** W1-06 — Document connectors

### 2026-11-13 — W1-04 Connector interface + sources management
- **Fait :** `connectors/base.py` (`BaseConnector` with `discover/read/metadata`, `is_authorized`/`ensure_authorized`, `SourceNotAuthorizedError`); `connectors/sources.py` (add/list/remove persisted in `sources.yaml`); CLI `mide sources add|list|remove` (`--config-dir` option for tests).
- **Fichiers principaux :** `mide/connectors/base.py`, `mide/connectors/sources.py`, `mide/cli.py`, `tests/test_connectors_base.py`
- **Tests :** 35 passés / 35 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-44v6yu`)
- **Décisions techniques :** paths are resolved (symlinks, `..`) before the authorization check, so escapes are refused; a folder source authorizes its contents only (not sibling folders with the same prefix); SQL URLs must match exactly; URLs containing an inline password are rejected (credentials must come from env vars, per CLAUDE.md).
- **Problèmes / dette technique :** `sources.yaml` rewrite drops user comments except the header. The routine's branch is `claude/...` instead of `task/W1-04-...` (imposed by the environment).
- **Prochaine tâche :** W1-05 — Tabular connector (CSV / Excel)

### 2026-11-13 — W1-03 Hardware profiler
- **Fait :** `mide/hardware/profiler.py` (RAM, CPU cores, OS, GPU via `nvidia-smi`, free disk, `choose_profile` per CLAUDE.md §3); `mide doctor` now prints "OK" plus the hardware report and chosen profile.
- **Fichiers principaux :** `mide/hardware/profiler.py`, `mide/cli.py`, `tests/test_profiler.py`
- **Tests :** 27 passés / 27 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/tender-pascal-1cbbpy`)
- **Décisions techniques :** GPU detection uses `nvidia-smi` only (no torch import, keeps base install light); psutil/GPU mocked in tests. Boundary: RAM exactly 12 GB = `small`, > 12 = `medium`.
- **Problèmes / dette technique :** only NVIDIA GPUs detected (no AMD/Apple Metal). The environment's `pytest` on PATH uses a different Python; run `/usr/bin/python3 -m pytest`.
- **Prochaine tâche :** W1-04 — Connector interface + sources management

### 2026-11-13 — W1-02 Configuration
- **Fait :** `mide/config.py` (pydantic, `load_config()`, `ConfigError` avec message clair), `mide/utils/paths.py` (`~/.mide` créé automatiquement, surchargeable via `MIDE_HOME`), `language: fr|en`, `config/models.yaml` rempli (4 profils), `sources.yaml` avec `sources: []`.
- **Fichiers principaux :** `mide/config.py`, `mide/utils/paths.py`, `tests/test_config.py`, `config/*.yaml`
- **Tests :** 10 passés / 10 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/relaxed-tesla-7a4m6z`)
- **Décisions techniques :** schémas stricts (clés inconnues refusées) pour détecter les fautes de frappe ; fichiers absents = valeurs par défaut ; noms de modèles Qwen2.5 GGUF dans `models.yaml` (à valider côté licence/taille).
- **Problèmes / dette technique :** le dossier de config est celui du dépôt (`config/`) ; `mide sources add` (W1-04) devra écrire dedans. Environnement : `pytest` global utilise un autre Python, lancer `/usr/bin/python3 -m pytest`.
- **Prochaine tâche :** W1-03 — Profiler matériel

### 2026-11-13 — W1-01 Squelette du projet
- **Fait :** `pyproject.toml`, arborescence de CLAUDE.md §4, config par défaut, CLI Typer (`mide --version`, `mide doctor` → « OK »), ruff/pytest/mypy, `conftest.py`.
- **Fichiers principaux :** `pyproject.toml`, `mide/cli.py`, `tests/test_cli.py`, `config/*.yaml`
- **Tests :** 2 passés / 2 au total ; `ruff check .` OK
- **PR :** voir la PR vers `main` (branche `claude/relaxed-tesla-8wpugt`)
- **Décisions techniques :** dépendances de base légères uniquement (typer, rich, pydantic, pyyaml, psutil) ; les dépendances lourdes (llama-cpp, chromadb, lightgbm…) seront ajoutées par les tâches qui en ont besoin. Branche imposée par l'environnement au lieu de `task/W1-01-...`.
- **Problèmes / dette technique :** `app/`, `scripts/` et sous-paquets sont des placeholders vides.
- **Prochaine tâche :** W1-02 — Configuration

### 2026-11-14 — Initialisation
- **Fait :** création de `CLAUDE.md`, `ROADMAP.md`, `PROGRESS.md`.
- **Prochaine tâche :** W1-01 — Squelette du projet
