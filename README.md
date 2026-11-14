# MIDE Engine

**Market Intelligence Decision Engine** — a local, lightweight, adaptive AI engine for businesses
(African SMEs first). / Un moteur d'IA **local, léger et adaptatif** pour les entreprises.

[English](#english) · [Français](#français)

---

## English

### What it does
1. Detects your hardware (RAM, CPU, GPU) and picks a matching profile (`tiny`, `small`, `medium`, `large`).
2. Reads **only** the data sources you explicitly authorize (folders, CSV, Excel, PDF, SQL databases).
3. Indexes documents (RAG) and trains predictive models on tabular data automatically.
4. Answers questions and produces business recommendations (sales, customers, marketing) in French or English.
5. Everything stays on your machine: no telemetry, no cloud.

### Installation
Requires Python 3.11+.

```bash
# Linux / macOS
./scripts/install.sh            # default extra: ui. Example: ./scripts/install.sh ui,llm,rag
# Windows (PowerShell)
./scripts/install.ps1
# or manually
pip install -e ".[ui]"          # extras: llm, rag, ui, finetune, dev
mide --version
mide doctor                     # checks the install and shows the hardware report
```

Docker: `docker build -t mide-engine .` then `docker run --rm mide-engine demo`.

One-shot demo (isolated workspace, no intervention): `./scripts/demo.sh` (set `MIDE_DEMO_SKIP_RAG=1` to skip indexing; `ask` steps are skipped until a model is pulled).

### Quick start (5 minutes, demo data)
```bash
python scripts/make_demo_data.py demo_data     # fictional SME dataset (sales, customers, campaigns, notes)
mide sources add demo_data                      # explicit consent: authorize this folder
mide scan                                       # catalog of datasets found
mide index                                      # index documents (needs the `rag` extra)
mide train --dataset sales --target amount     # train a model (see `mide scan` for columns)
mide report                                     # weekly report: KPIs, forecasts, alerts, 3 priority actions (no LLM needed)
mide models pull                                # optional: download the LLM (asks confirmation), needed for `ask`/`chat`
mide ask "Which products sell best?"            # answer with cited data
mide ui                                         # Streamlit dashboard on http://localhost:8501
```

### Adding your own sources
```bash
mide sources add /path/to/folder_or_file        # CSV, XLSX, PDF, TXT, MD, DOCX
mide sources add "sqlite:///path/to/db.sqlite"  # SQL URL (read-only); credentials come from environment variables
mide sources list
mide sources remove /path/to/folder_or_file     # revoke access
```
Authorized sources are stored in `config/sources.yaml`. Nothing outside this list is ever read.

### Commands
| Command | Purpose |
|---|---|
| `mide doctor` | Check installation, show hardware profile |
| `mide sources add/list/remove` | Manage authorized sources |
| `mide scan` | Catalog of datasets |
| `mide index` | Incremental indexing of documents |
| `mide train --dataset D --target T` | Train and register a model |
| `mide models list/trained/pull` | List profiles/trained models; download LLM weights (asks confirmation) |
| `mide ask "question"` | Answer from documents, business modules, or both |
| `mide chat` | Interactive conversation |
| `mide report [--format md\|html] [-o file]` | Weekly report |
| `mide auto` | Scan, index, retrain changed models (kept only if better), report |
| `mide ui [--port N]` | Streamlit dashboard |
| `mide finetune` | Optional LoRA fine-tuning (GPU only) |
| `mide privacy` | Show what is read, what is stored, and the network policy |

Configuration: `config/default.yaml` (language `fr|en`, chunking), `config/models.yaml` (models per
profile; update models without touching code). App data lives in `~/.mide/` (override with `MIDE_HOME`).

### Architecture
```
CLI + Dashboard -> Agent (router: RAG / prediction / both) -> LLM
RAG (embeddings + ChromaDB) · AutoML (scikit-learn, LightGBM, statsmodels) · LLM (llama.cpp, GGUF, optional LoRA)
Connectors (folders, CSV, Excel, PDF, SQL)  ·  Hardware profiler
```
Small pre-trained quantized LLM + RAG + tabular AutoML. We never train an LLM from scratch.

### Limits
- Small local models are less fluent than large cloud models; a `tiny` profile (< 6 GB RAM) uses a ~1B model.
- AutoML targets simple tabular tasks (regression, classification, time series); results depend on data quality.
- LoRA fine-tuning needs a GPU; otherwise RAG is used instead.
- Scanned PDFs without a text layer are not OCR-ed.
- Without LLM weights, answers fall back to structured, data-backed text.

### Privacy FAQ
- **Does data leave my machine?** No. The only network call is the optional, confirmed download of model weights (`mide models pull`).
- **Does MIDE scan my disk?** No. Only sources you add with `mide sources add`.
- **Can it modify my files or databases?** No. Sources are read-only.
- **Telemetry?** None. Run `mide privacy` at any time to see what is read and stored.
- **How do I delete everything?** Remove `~/.mide/` and revoke sources with `mide sources remove`.

---

## Français

### Ce que fait MIDE
1. Détecte votre matériel (RAM, CPU, GPU) et choisit un profil (`tiny`, `small`, `medium`, `large`).
2. Ne lit **que** les sources que vous autorisez explicitement (dossiers, CSV, Excel, PDF, bases SQL).
3. Indexe les documents (RAG) et entraîne automatiquement des modèles prédictifs sur les données tabulaires.
4. Répond aux questions et produit des recommandations business (ventes, clients, marketing) en français ou en anglais.
5. Tout reste sur votre machine : pas de télémétrie, pas de cloud.

### Installation
Python 3.11+ requis. Mêmes commandes que ci-dessus :

```bash
./scripts/install.sh          # Linux / macOS  (Windows : ./scripts/install.ps1)
pip install -e ".[ui]"        # ou manuellement ; extras : llm, rag, ui, finetune, dev
mide doctor                   # vérifie l'installation et affiche le matériel
```
Docker : `docker build -t mide-engine .` puis `docker run --rm mide-engine demo`.

### Démarrage rapide (données de démo)
```bash
python scripts/make_demo_data.py demo_data
mide sources add demo_data       # consentement explicite
mide scan
mide index
mide train --dataset sales --target amount
mide report
mide models pull                 # optionnel : télécharge le LLM (confirmation), requis pour ask/chat
mide ask "Quels produits se vendent le mieux ?"
mide ui
```
La langue des messages se règle dans `config/default.yaml` (`language: fr` ou `en`).

### Ajouter vos sources
`mide sources add <dossier|fichier|URL SQL>`, `mide sources list`, `mide sources remove <source>`.
Les identifiants SQL viennent de variables d'environnement. Seules les sources listées dans
`config/sources.yaml` sont lues, toujours en **lecture seule**.

### Commandes
Voir le tableau anglais ci-dessus ; `mide --help` et `mide <commande> --help` donnent le détail.

### Limites
- Les petits modèles locaux sont moins fluides que les grands modèles cloud.
- L'AutoML vise des tâches tabulaires simples ; la qualité dépend des données.
- Le fine-tuning LoRA exige un GPU ; sinon le RAG est utilisé.
- Les PDF scannés sans couche texte ne sont pas reconnus (pas d'OCR).

### FAQ confidentialité
- **Mes données quittent-elles ma machine ?** Non. Seul le téléchargement (confirmé) des poids du modèle utilise le réseau.
- **MIDE scanne-t-il mon disque ?** Non, uniquement les sources ajoutées avec `mide sources add`.
- **Peut-il modifier mes fichiers ?** Non, tout est en lecture seule.
- **Télémétrie ?** Aucune. `mide privacy` montre ce qui est lu et stocké.
- **Tout supprimer ?** Supprimez `~/.mide/` et révoquez les sources avec `mide sources remove`.

## License
See `LICENSE`.
