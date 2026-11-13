# CLAUDE.md — MIDE Engine

> Ce fichier est la source de vérité du projet. Lis-le EN ENTIER au début de chaque session,
> puis lis `ROADMAP.md` et `PROGRESS.md` avant d'écrire la moindre ligne de code.

---

## 1. Vision

**MIDE Engine** (Market Intelligence Decision Engine) est un moteur d'IA **local, léger et adaptatif**
pour les entreprises (PME africaines en priorité). Une fois installé sur une machine :

1. il **détecte le matériel** (RAM, CPU, GPU, OS) et choisit automatiquement la configuration adaptée ;
2. il **se connecte aux sources de données que l'utilisateur autorise** (dossiers, CSV, Excel, PDF, bases SQL) ;
3. il **indexe** ces données (RAG) et **entraîne automatiquement** des modèles prédictifs sur les données tabulaires ;
4. il **répond aux questions** et **produit des recommandations business** (ventes, marketing, clients, décisions)
   en langage naturel, en français et en anglais ;
5. tout reste **100 % local** : aucune donnée ne quitte la machine.

Le « petit mais puissant » vient de la combinaison :
**petit LLM pré-entraîné quantifié + RAG + AutoML tabulaire + fine-tuning LoRA optionnel**.
On n'entraîne JAMAIS un LLM à partir de zéro.

---

## 2. Principes non négociables

1. **Consentement explicite** : le moteur ne lit QUE les sources listées dans `config/sources.yaml`
   ou ajoutées via la commande `mide sources add`. Aucun scan automatique du disque, du dossier
   utilisateur, des navigateurs, des emails ou de quoi que ce soit d'autre.
2. **Local-first** : aucun appel réseau en exécution, sauf le téléchargement initial des poids
   du modèle (avec confirmation). Pas de télémétrie.
3. **Lecture seule** sur les sources de données : on ne modifie, ne déplace, ne supprime jamais
   les fichiers ou tables de l'utilisateur.
4. **Dégradation gracieuse** : sur une petite machine (4 Go RAM, pas de GPU), tout doit fonctionner,
   avec un modèle plus petit. Le fine-tuning LoRA n'est activé que si le matériel le permet.
5. **Explicabilité** : chaque recommandation cite les données / métriques qui la justifient.
6. **Tests obligatoires** : aucune fonctionnalité sans tests. `pytest` doit passer avant tout commit.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Interfaces (CLI + Dashboard)              │
│               mide <cmd>          Streamlit (app/)            │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                  Orchestrateur / Agent décisionnel            │
│   route la question → RAG, Prédiction, ou les deux → LLM      │
└───────┬───────────────────┬───────────────────┬──────────────┘
        │                   │                   │
┌───────▼──────┐   ┌────────▼────────┐  ┌───────▼────────────┐
│  RAG / Index │   │ AutoML tabulaire│  │  LLM local          │
│  embeddings  │   │ LightGBM, sklearn│ │  llama.cpp (GGUF)   │
│  ChromaDB    │   │ Prophet/stats    │ │  + LoRA optionnel   │
└───────▲──────┘   └────────▲────────┘  └───────▲────────────┘
        │                   │                   │
┌───────┴───────────────────┴──────┐   ┌────────┴────────────┐
│  Connecteurs de données          │   │  Profiler matériel  │
│  dossiers, CSV, Excel, PDF, SQL  │   │  → choix du profil  │
└──────────────────────────────────┘   └─────────────────────┘
```

### Profils matériels (choisis par `mide/hardware/profiler.py`)

| Profil   | Condition                         | LLM                       | Embeddings          | LoRA |
|----------|-----------------------------------|---------------------------|---------------------|------|
| `tiny`   | RAM < 6 Go                        | ~0.5–1.5B, quantif. Q4    | petit modèle multilingue | non |
| `small`  | 6–12 Go RAM, pas de GPU           | ~1.5–3B, Q4               | modèle multilingue standard | non |
| `medium` | > 12 Go RAM ou GPU ≥ 6 Go VRAM    | ~3–4B, Q4/Q5              | modèle multilingue standard | oui si GPU |
| `large`  | GPU ≥ 12 Go VRAM                  | ~7–8B, Q4/Q5              | modèle multilingue large | oui |

Les noms exacts des modèles sont définis dans `config/models.yaml` (pas codés en dur),
pour pouvoir les mettre à jour sans toucher au code. Privilégier des modèles ouverts,
multilingues (FR/EN), à licence permissive (Qwen, Llama, Phi, Gemma — vérifier la licence).

---

## 4. Structure du dépôt

```
mide-engine/
├── CLAUDE.md               # ce fichier
├── ROADMAP.md              # tâches à cocher
├── PROGRESS.md             # journal des sessions
├── README.md               # doc utilisateur
├── pyproject.toml
├── config/
│   ├── default.yaml        # paramètres généraux
│   ├── models.yaml         # modèles par profil matériel
│   └── sources.yaml        # sources autorisées (vide par défaut)
├── mide/
│   ├── __init__.py
│   ├── cli.py              # point d'entrée Typer : `mide ...`
│   ├── config.py           # chargement/validation config (pydantic)
│   ├── hardware/
│   │   └── profiler.py
│   ├── connectors/
│   │   ├── base.py         # interface BaseConnector
│   │   ├── files.py        # dossiers, txt, md, docx
│   │   ├── tabular.py      # csv, xlsx
│   │   ├── pdf.py
│   │   └── sql.py          # SQLite, PostgreSQL, MySQL, SQL Server via SQLAlchemy
│   ├── ingestion/
│   │   ├── catalog.py      # inventaire des datasets (schéma, taille, type)
│   │   └── profiling.py    # profil des colonnes (types, nulls, dates, cibles possibles)
│   ├── rag/
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── store.py        # ChromaDB
│   │   └── retriever.py
│   ├── llm/
│   │   ├── runtime.py      # llama-cpp-python
│   │   ├── downloader.py   # téléchargement des poids avec confirmation
│   │   ├── prompts.py
│   │   └── lora.py         # fine-tuning optionnel (PEFT)
│   ├── automl/
│   │   ├── task_detector.py   # régression / classification / série temporelle
│   │   ├── trainer.py
│   │   ├── evaluator.py
│   │   └── registry.py        # sauvegarde/versionnement des modèles entraînés
│   ├── business/
│   │   ├── sales.py        # prévision des ventes, tendances, produits top/flop
│   │   ├── customers.py    # segmentation RFM, churn
│   │   ├── marketing.py    # performance canaux/campagnes, recommandations
│   │   └── insights.py     # détection d'anomalies, KPIs
│   ├── agent/
│   │   ├── router.py       # décide RAG vs prédiction vs les deux
│   │   └── decision.py     # transforme les résultats en recommandations
│   └── utils/
│       ├── logging.py
│       └── paths.py        # dossier de données de l'app (~/.mide)
├── app/
│   └── dashboard.py        # Streamlit
├── tests/
│   ├── fixtures/           # petits datasets synthétiques (ventes, clients, campagnes)
│   └── test_*.py
└── scripts/
    └── make_demo_data.py   # génère un jeu de données business fictif
```

Données de l'application (index, modèles entraînés, poids LLM) : `~/.mide/` — jamais dans le dépôt.

---

## 5. Stack technique

- **Python 3.11+**, gestion des dépendances avec `uv` (ou `pip` + `pyproject.toml`)
- CLI : `typer` + `rich`
- Config : `pydantic` + `pyyaml`
- Données : `pandas`, `pyarrow`, `openpyxl`, `SQLAlchemy`, `pypdf`, `python-docx`
- Matériel : `psutil`, détection GPU via `torch.cuda` (import optionnel) ou `nvidia-smi`
- LLM : `llama-cpp-python` (modèles GGUF)
- Embeddings : `sentence-transformers`
- Vector store : `chromadb` (mode persistant local)
- AutoML : `scikit-learn`, `lightgbm`, `statsmodels` (séries temporelles simples)
- LoRA (optionnel, extra `[finetune]`) : `torch`, `transformers`, `peft`
- Dashboard : `streamlit`
- Qualité : `pytest`, `ruff`, `mypy` (mode non strict)

Les dépendances lourdes (`torch`, `peft`) sont dans un extra optionnel :
`pip install mide-engine[finetune]`.

---

## 6. Règles de code

- Code, noms de variables et docstrings en **anglais** ; messages utilisateur de la CLI en
  **français** et **anglais** (paramètre `language` dans la config, défaut `fr`).
- Fonctions courtes, typées (`type hints` partout).
- Chaque module a son fichier de tests `tests/test_<module>.py`.
- Les tests ne doivent JAMAIS télécharger de vrai modèle : utiliser des mocks / faux modèles
  pour le LLM et les embeddings (fixtures dans `tests/conftest.py`).
- Pas de secrets dans le code. Les identifiants SQL viennent de variables d'environnement.
- `ruff check .` et `pytest` doivent passer avant chaque commit.

---

## 7. Déroulement de CHAQUE session (obligatoire)

1. Lire `CLAUDE.md`, `ROADMAP.md`, `PROGRESS.md`.
2. Vérifier l'état : `git pull`, `pytest -q`. Si des tests échouent, **les réparer d'abord**.
3. Prendre la **première tâche non cochée** de `ROADMAP.md` (respecter l'ordre).
   Une seule tâche par session, sauf si elle est terminée très vite.
4. Créer une branche `task/<ID>-<nom-court>` (ex. `task/W1-03-csv-connector`).
5. Implémenter + écrire les tests. Respecter les critères d'acceptation de la tâche.
6. Lancer `ruff check .` et `pytest`. Tout doit passer.
7. Cocher la tâche dans `ROADMAP.md`.
8. Ajouter une entrée dans `PROGRESS.md` (format défini dans ce fichier).
9. Commit, push, ouvrir une Pull Request vers `main` avec un résumé clair.
10. Si une tâche est bloquée (dépendance impossible, décision à prendre) : NE PAS improviser
    une grosse refonte. Écrire le blocage dans `PROGRESS.md` section « Questions pour Dieudonné »,
    et passer à la tâche suivante si elle est indépendante.

### Définition de « terminé »
- Les critères d'acceptation de la tâche sont remplis.
- Tests ajoutés et verts.
- Pas de régression sur les tests existants.
- `PROGRESS.md` et `ROADMAP.md` à jour.

---

## 8. Ce qu'il ne faut PAS faire

- Ne pas entraîner un LLM à partir de zéro.
- Ne pas lire de données hors des sources autorisées.
- Ne pas ajouter de service cloud, d'API payante ou de télémétrie.
- Ne pas changer l'architecture ou la stack sans noter la raison dans `PROGRESS.md`
  et la poser en question.
- Ne pas supprimer de tests pour les faire passer.
- Ne pas commiter de poids de modèles, de données réelles ou de fichiers de `~/.mide/`.
