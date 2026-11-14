# PROGRESS.md — Journal de développement

> L'agent ajoute UNE entrée à la fin de chaque session, la plus récente EN HAUT.
> Dieudonné lit ce fichier pour suivre l'avancement et répondre aux questions.

---

## ❓ Questions pour Dieudonné

_(L'agent écrit ici les blocages et décisions à prendre. Dieudonné répond directement sous chaque question.)_

- Aucune pour l'instant.

---

## 📊 État global

| Semaine | Tâches terminées | Statut |
|---------|------------------|--------|
| S1 — Fondations       | 9 / 9 | ✅ terminé |
| S2 — LLM & RAG        | 7 / 7 | ✅ terminé |
| S3 — Intelligence     | 9 / 9 | ✅ terminé |
| S4 — Produit          | 5 / 8 | 🔄 en cours |

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
