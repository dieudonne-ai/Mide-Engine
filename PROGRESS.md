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
| S1 — Fondations       | 7 / 9 | 🚧 en cours |
| S2 — LLM & RAG        | 0 / 7 | ⏳ pas commencé |
| S3 — Intelligence     | 0 / 9 | ⏳ pas commencé |
| S4 — Produit          | 0 / 8 | ⏳ pas commencé |

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
