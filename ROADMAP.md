# ROADMAP.md — MIDE Engine (4 semaines)

> Règle : prendre la PREMIÈRE tâche non cochée, dans l'ordre. Une tâche = une PR.
> Cocher `[x]` uniquement quand tous les critères d'acceptation sont remplis et que `pytest` passe.

---

## Semaine 1 — Fondations, matériel et connecteurs

- [x] **W1-01 — Squelette du projet**
  - `pyproject.toml`, arborescence de `CLAUDE.md` §4, `ruff`, `pytest`, `conftest.py`.
  - CLI Typer minimale : `mide --version`, `mide doctor` (affiche « OK »).
  - ✅ Critères : `pip install -e .` fonctionne, `mide --version` répond, `pytest` passe.

- [x] **W1-02 — Configuration**
  - `config.py` avec pydantic : charge `config/default.yaml`, `models.yaml`, `sources.yaml`.
  - Dossier de l'app `~/.mide/` créé automatiquement (`utils/paths.py`).
  - Paramètre `language: fr|en`.
  - ✅ Critères : config invalide → erreur claire ; tests sur chargement et valeurs par défaut.

- [x] **W1-03 — Profiler matériel**
  - `hardware/profiler.py` : RAM, cœurs CPU, OS, GPU (nom + VRAM si dispo), espace disque libre.
  - Choix du profil `tiny|small|medium|large` selon le tableau de `CLAUDE.md` §3.
  - `mide doctor` affiche le rapport matériel et le profil choisi.
  - ✅ Critères : tests avec valeurs simulées (mock `psutil`) pour chaque profil.

- [x] **W1-04 — Interface connecteur + gestion des sources**
  - `connectors/base.py` : `BaseConnector` (`discover()`, `read()`, `metadata()`).
  - `mide sources add <chemin|url_sql>`, `mide sources list`, `mide sources remove`.
  - Les sources sont enregistrées dans `sources.yaml`. Rien n'est lu sans y figurer.
  - ✅ Critères : test vérifiant qu'un fichier hors source autorisée est refusé.

- [x] **W1-05 — Connecteur tabulaire (CSV / Excel)**
  - Lecture CSV (détection séparateur/encodage) et XLSX (toutes les feuilles).
  - ✅ Critères : tests sur fixtures CSV `,` et `;`, UTF-8 et Latin-1, Excel multi-feuilles.

- [x] **W1-06 — Connecteurs documents (dossiers, TXT/MD, DOCX, PDF)**
  - Parcours récursif d'un dossier autorisé, filtrage par extension, taille max configurable.
  - ✅ Critères : tests sur petits fichiers de fixtures ; fichiers corrompus ignorés avec un log.

- [x] **W1-07 — Connecteur SQL**
  - SQLAlchemy : SQLite (tests), PostgreSQL, MySQL, SQL Server (via URL).
  - Lecture seule : découverte des tables, schéma, échantillon, lecture par chunks.
  - Identifiants via variables d'environnement.
  - ✅ Critères : tests sur une base SQLite de fixtures ; toute requête d'écriture est bloquée.

- [x] **W1-08 — Catalogue et profilage des données**
  - `ingestion/catalog.py` : inventaire de tous les datasets (source, type, lignes, colonnes).
  - `ingestion/profiling.py` : types de colonnes, % de valeurs manquantes, colonnes date,
    colonnes numériques candidates comme cible (ventes, montant, quantité…).
  - Commande `mide scan` qui affiche le catalogue.
  - ✅ Critères : tests sur le jeu de démo ; détection correcte des colonnes date et montant.

- [x] **W1-09 — Jeu de données de démonstration**
  - `scripts/make_demo_data.py` : génère une PME fictive (ventes 2 ans, produits, clients,
    campagnes marketing par canal, quelques documents texte : rapports, notes de réunion).
  - Saisonnalité et tendances réalistes, quelques anomalies volontaires.
  - ✅ Critères : script déterministe (seed), utilisé par les tests suivants.

---

## Semaine 2 — Cerveau langage et mémoire (RAG)

- [x] **W2-01 — Téléchargement et gestion des modèles**
  - `llm/downloader.py` : télécharge le modèle GGUF du profil (depuis `models.yaml`)
    dans `~/.mide/models/`, avec confirmation, barre de progression, vérification de taille/hash.
  - `mide models list`, `mide models pull`.
  - ✅ Critères : tests avec téléchargement mocké ; aucun téléchargement sans confirmation.

- [x] **W2-02 — Runtime LLM local**
  - `llm/runtime.py` : wrapper `llama-cpp-python` (contexte, threads selon CPU, offload GPU si dispo).
  - Interface `LLM.generate(prompt, max_tokens, temperature)` + version streaming.
  - Faux LLM (`FakeLLM`) pour les tests.
  - ✅ Critères : tests avec FakeLLM ; paramètres adaptés au profil matériel.

- [x] **W2-03 — Embeddings**
  - `rag/embeddings.py` : modèle multilingue choisi selon le profil, traitement par lots.
  - Faux embedder déterministe pour les tests.
  - ✅ Critères : tests de dimension et de déterminisme.

- [x] **W2-04 — Chunking**
  - Découpage des documents (taille + chevauchement configurables).
  - Pour les tableaux : génération de résumés textuels (schéma + statistiques) indexables.
  - ✅ Critères : tests sur longueurs de chunks et métadonnées (source, page, ligne).

- [x] **W2-05 — Index vectoriel + indexation incrémentale**
  - `rag/store.py` (ChromaDB persistant dans `~/.mide/index/`).
  - `mide index` : n'indexe que les fichiers nouveaux ou modifiés (hash + date).
  - ✅ Critères : test : réindexation sans changement → 0 nouveau chunk.

- [x] **W2-06 — Retriever + réponses avec sources**
  - `rag/retriever.py` : top-k + filtrage par source.
  - `mide ask "question"` : RAG + LLM, réponse avec citations des sources.
  - Prompts dans `llm/prompts.py`, FR/EN.
  - ✅ Critères : test bout-en-bout avec FakeLLM/FakeEmbedder ; les sources sont citées.

- [x] **W2-07 — Mode conversation**
  - `mide chat` : boucle interactive avec historique court.
  - ✅ Critères : test de la gestion d'historique (troncature).

---

## Semaine 3 — Intelligence business (entraînement automatique)

- [x] **W3-01 — Détection du type de tâche**
  - `automl/task_detector.py` : pour un dataset + une cible, déterminer
    régression / classification / série temporelle.
  - ✅ Critères : tests sur les 3 cas avec le jeu de démo.

- [x] **W3-02 — Entraîneur AutoML**
  - `automl/trainer.py` : préparation automatique (encodage, valeurs manquantes, features de date),
    validation croisée (temporelle pour les séries), LightGBM + baseline simple.
  - Taille des modèles et durée limitées selon le profil matériel.
  - ✅ Critères : le modèle bat la baseline sur le jeu de démo ; tests de reproductibilité (seed).

- [x] **W3-03 — Évaluation + registre de modèles**
  - `automl/evaluator.py` : métriques (MAE/MAPE, AUC/F1…), importance des variables.
  - `automl/registry.py` : sauvegarde versionnée dans `~/.mide/models_trained/` + métadonnées.
  - `mide train --dataset X --target Y`, `mide models trained`.
  - ✅ Critères : tests de sauvegarde/chargement.

- [x] **W3-04 — Module ventes**
  - `business/sales.py` : prévision 30/60/90 jours, top/flop produits, tendances, saisonnalité.
  - ✅ Critères : sur le jeu de démo, détecte la saisonnalité générée.

- [x] **W3-05 — Module clients**
  - `business/customers.py` : segmentation RFM, score de risque de churn.
  - ✅ Critères : segments cohérents sur le jeu de démo ; tests.

- [x] **W3-06 — Module marketing**
  - `business/marketing.py` : performance par canal/campagne (coût, conversions, ROI),
    canaux qui sous-performent, réallocation de budget suggérée.
  - ✅ Critères : tests sur le jeu de démo.

- [x] **W3-07 — Insights & anomalies**
  - `business/insights.py` : KPIs principaux, détection d'anomalies (chutes/pics anormaux).
  - ✅ Critères : retrouve les anomalies volontaires du jeu de démo.

- [x] **W3-08 — Agent décisionnel**
  - `agent/router.py` : la question va vers le RAG, un module business, ou les deux.
  - `agent/decision.py` : le LLM transforme les résultats chiffrés en recommandations
    actionnables (« quoi faire, pourquoi, impact estimé, données utilisées »).
  - `mide ask` utilise maintenant l'agent.
  - ✅ Critères : tests de routage ; chaque recommandation contient ses chiffres sources.

- [x] **W3-09 — Auto-apprentissage planifié**
  - `mide auto` : scan → indexation incrémentale → réentraînement si les données ont changé
    → rapport. Réentraîne uniquement si le nouveau modèle est meilleur (sinon garde l'ancien).
  - ✅ Critères : test : données inchangées → aucun réentraînement.

---

## Semaine 4 — Produit, fine-tuning et livraison

- [x] **W4-01 — Dashboard Streamlit**
  - `app/dashboard.py` : pages Accueil (KPIs), Ventes, Clients, Marketing, Poser une question,
    Sources de données, Matériel & modèles.
  - `mide ui` lance le dashboard.
  - ✅ Critères : se lance sans erreur sur le jeu de démo.

- [x] **W4-02 — Rapport hebdomadaire**
  - `mide report` : génère un rapport Markdown/HTML (KPIs, prévisions, alertes, 3 actions prioritaires).
  - ✅ Critères : rapport généré sur le jeu de démo, testé.

- [x] **W4-03 — Fine-tuning LoRA optionnel**
  - `llm/lora.py` : uniquement si profil `medium`/`large` avec GPU.
  - Génère un petit dataset Q/R à partir des documents de l'entreprise, entraîne un adaptateur LoRA,
    évalue avant/après, n'active l'adaptateur que s'il améliore les résultats.
  - Sinon : message clair « fine-tuning indisponible sur cette machine, le RAG est utilisé ».
  - ✅ Critères : désactivé proprement sans GPU ; tests du chemin « non disponible ».

- [x] **W4-04 — Performance et robustesse**
  - Mesurer RAM/temps sur le profil `tiny` ; traitement par lots pour gros fichiers ;
    gestion des erreurs utilisateur avec messages clairs (FR/EN).
  - ✅ Critères : jeu de démo traité entièrement avec < 4 Go RAM (hors LLM).

- [x] **W4-05 — Sécurité et confidentialité**
  - Audit : aucun appel réseau hors téléchargement de modèle, sources respectées,
    mode lecture seule SQL, aucune donnée en log en clair.
  - `mide privacy` affiche ce qui est lu et stocké.
  - ✅ Critères : test bloquant tout accès réseau pendant `mide ask`.

- [x] **W4-06 — Packaging**
  - Dockerfile + installation `pip install mide-engine` ; script d'installation Windows/Linux.
  - ✅ Critères : `docker build` OK ; démarrage avec le jeu de démo documenté.

- [x] **W4-07 — Documentation**
  - `README.md` complet (FR + EN) : installation, ajout de sources, commandes, architecture,
    limites, FAQ confidentialité.
  - ✅ Critères : un nouvel utilisateur peut faire la démo en suivant le README.

- [x] **W4-08 — Démo finale**
  - Script `scripts/demo.sh` : génère les données, indexe, entraîne, pose 5 questions business,
    produit le rapport.
  - ✅ Critères : la démo tourne de bout en bout sans intervention.

---

## Backlog (après le mois, ne pas commencer sans validation)

- Connecteurs Google Sheets / Odoo / QuickBooks
- API REST locale (FastAPI) pour intégration dans d'autres logiciels (ex. Baryon)
- Version desktop (Tauri/Electron)
- Support du swahili
- Multi-utilisateurs et rôles
