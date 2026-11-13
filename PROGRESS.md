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
| S1 — Fondations       | 2 / 9 | 🚧 en cours |
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
