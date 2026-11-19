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
