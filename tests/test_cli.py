import pytest
from typer.testing import CliRunner

from mide import __version__
from mide.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_doctor_ok() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_auto_no_sources(tmp_path):
    from typer.testing import CliRunner

    from mide.cli import app

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    result = CliRunner().invoke(app, ["auto", "--config-dir", str(cfg)])
    assert result.exit_code == 0
    assert "Aucune source autorisée. Utilisez `mide sources add`." in result.output


def test_no_sources_hint_follows_language(tmp_path) -> None:
    # scan / index / auto answer in the configured language when no source is authorized.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    args = ["--config-dir", str(cfg)]
    for command in ("scan", "index", "auto"):
        result = runner.invoke(app, [command, *args])
        assert result.exit_code == 0, command
        assert "Aucune source autorisée. Utilisez `mide sources add`." in result.output, command
    (cfg / "default.yaml").write_text("language: en\n", encoding="utf-8")
    for command in ("scan", "index", "auto"):
        result = runner.invoke(app, [command, *args])
        assert result.exit_code == 0, command
        assert "No authorized sources. Use `mide sources add`." in result.output, command


def test_models_and_report_messages_follow_language(tmp_path, monkeypatch) -> None:
    # `models trained` hint and `report` format/written messages use the configured language.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    args = ["--config-dir", str(cfg)]
    out = tmp_path / "r.md"
    expected = {
        "fr": ("Aucun modèle entraîné. Utilisez `mide train --dataset X --target Y`.",
               "Le format doit être 'md' ou 'html'.", f"Rapport écrit\u00a0: {out}"),
        "en": ("No trained models. Use `mide train --dataset X --target Y`.",
               "Format must be 'md' or 'html'.", f"Report written: {out}"),
    }
    for language, (no_models, bad_format, written) in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["models", "trained", *args])
        assert result.exit_code == 0 and no_models in result.output, language
        result = runner.invoke(app, ["report", "--format", "pdf", *args])
        assert result.exit_code == 2 and bad_format in result.output, language
        result = runner.invoke(app, ["report", "-o", str(out), *args])
        assert result.exit_code == 0 and written in result.output, language


def test_ui_help_shows_install_extra() -> None:
    # Rich markup must not swallow the "[ui]" extra in the install hint.
    result = runner.invoke(app, ["ui", "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "mide-engine[ui]" in result.output
    assert "\\[ui]" not in result.output


def test_auto_without_rag_extra_still_retrains(tmp_path, monkeypatch) -> None:
    # Without sentence-transformers, `mide auto` skips indexing but still retrains.
    from mide import cli
    from mide.rag.embeddings import EmbeddingError

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales.csv").write_text("x,amount\n1,2\n2,4\n", encoding="utf-8")
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    assert runner.invoke(app, ["sources", "add", str(data), "--config-dir", str(cfg)]).exit_code == 0

    def no_embedder(_cfg):
        raise EmbeddingError("sentence-transformers is not installed.")

    calls: list[dict] = []
    monkeypatch.setattr(cli, "_get_embedder", no_embedder)
    monkeypatch.setattr(cli, "retrain_if_changed", lambda datasets, *a, **k: calls.append(datasets) or [])
    result = runner.invoke(app, ["auto", "--config-dir", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "Indexation\u00a0: ignorée (sentence-transformers is not installed)." in result.output
    assert len(calls) == 1 and any("sales.csv" in key for key in calls[0])
    assert "Aucun modèle entraîné" in result.output


def test_error_prefix_follows_language(tmp_path, monkeypatch) -> None:
    # Command failures use "Erreur :" in French (default) and "Error:" in English.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    args = ["--config-dir", str(cfg)]
    for language, prefix in (("fr", "Erreur\u00a0: "), ("en", "Error: ")):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["train", "--dataset", "nope", "--target", "y", *args])
        assert result.exit_code == 1, language
        assert result.output.startswith(prefix), (language, result.output)
    # A broken config cannot give its language: the default (French) is used.
    (cfg / "default.yaml").write_text("language: [\n", encoding="utf-8")
    for command in (["models", "list"], ["index"], ["privacy"], ["auto"], ["finetune"]):
        result = runner.invoke(app, [*command, *args])
        assert result.exit_code == 1, command
        assert result.output.startswith("Erreur\u00a0: "), (command, result.output)


def test_auto_summary_follows_language(tmp_path, monkeypatch) -> None:
    # The `mide auto` scan/index/model lines use the configured language.
    from mide import cli
    from mide.automl.auto import ModelOutcome
    from mide.rag.embeddings import EmbeddingError

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales.csv").write_text("x,amount\n1,2\n2,4\n", encoding="utf-8")
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    args = ["--config-dir", str(cfg)]
    assert runner.invoke(app, ["sources", "add", str(data), *args]).exit_code == 0

    def no_embedder(_cfg):
        raise EmbeddingError("sentence-transformers is not installed.")

    outcomes = [
        ModelOutcome("a", "promoted", "new model is better", 3.0, 2.0),
        ModelOutcome("b", "kept", "previous model kept", 2.0, 2.5),
        ModelOutcome("c", "unchanged"),
        ModelOutcome("d", "skipped", "dataset no longer available"),
        ModelOutcome("e", "error", "boom"),
    ]
    monkeypatch.setattr(cli, "_get_embedder", no_embedder)
    monkeypatch.setattr(cli, "retrain_if_changed", lambda *a, **k: outcomes)
    expected = {
        "fr": [
            "Analyse\u00a0: 1 jeux de données/documents.",
            "Indexation\u00a0: ignorée (sentence-transformers is not installed).",
            "Modèle a\u00a0: remplacé (3 -> 2) le nouveau modèle est meilleur",
            "Modèle b\u00a0: conservé (2 -> 2,5) l'ancien modèle est conservé",
            "Modèle c\u00a0: inchangé",
            "Modèle d\u00a0: ignoré le jeu de données n'est plus disponible",
            "Modèle e\u00a0: erreur boom",
        ],
        "en": [
            "Scan: 1 datasets/documents.",
            "Index: skipped (sentence-transformers is not installed).",
            "Model a: promoted (3 -> 2) new model is better",
            "Model b: kept (2 -> 2.5) previous model kept",
            "Model c: unchanged",
            "Model d: skipped dataset no longer available",
            "Model e: error boom",
        ],
    }
    for language, lines in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["auto", *args])
        assert result.exit_code == 0, result.output
        assert result.output.splitlines() == lines, language


def test_auto_and_models_trained_show_target_leakage(tmp_path, monkeypatch) -> None:
    # A model promoted by `mide auto` with leakage suspects gets the same FR/EN warning
    # as `mide train`; `mide models trained` repeats it for a flagged model only.
    from mide import cli
    from mide.automl.auto import ModelOutcome
    from mide.rag.embeddings import EmbeddingError

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    folder = tmp_path / "data"
    folder.mkdir()
    lines = ["price,total"] + [f"{i},{3 * i}" for i in range(60)]
    (folder / "orders.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["x,amount"] + [f"{i % 5},{10 * (i % 5) + (i * 7) % 11}" for i in range(60)]
    (folder / "sales.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    args = ["--config-dir", str(cfg)]
    assert runner.invoke(app, ["sources", "add", str(folder), *args]).exit_code == 0
    for dataset, target in (("orders", "total"), ("sales", "amount")):
        result = runner.invoke(app, ["train", "--dataset", dataset, "--target", target, *args])
        assert result.exit_code == 0, result.output

    def no_embedder(_cfg):
        raise EmbeddingError("sentence-transformers is not installed.")

    outcomes = [
        ModelOutcome("orders-total", "promoted", "new model is better", 3.0, 2.0,
                     target="total", leakage_suspects=["price"]),
        ModelOutcome("sales-amount", "kept", "previous model kept", 2.0, 2.5),
    ]
    monkeypatch.setattr(cli, "_get_embedder", no_embedder)
    monkeypatch.setattr(cli, "retrain_if_changed", lambda *a, **k: outcomes)
    expected = {
        "fr": ("Attention\u00a0: score presque parfait, fuite de la cible probable. Vérifiez que "
               "price ne sont pas calculées à partir de 'total' ni connues après lui\u00a0; "
               "sinon retirez-les des données avant d'entraîner."),
        "en": ("Warning: near-perfect score, likely target leakage. Check that price "
               "are not computed from 'total' or only known after it; if so, remove "
               "them from the data before training."),
    }
    for language, warning in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["auto", *args])
        assert result.exit_code == 0, result.output
        out = result.output.splitlines()
        assert out[-3].startswith(("Modèle orders-total", "Model orders-total"))
        assert out[-2] == warning
        assert out[-1].startswith(("Modèle sales-amount", "Model sales-amount"))
        result = runner.invoke(app, ["models", "trained", *args])
        assert result.exit_code == 0, result.output
        out = result.output.splitlines()
        assert out[0].startswith("orders-total v1") and out[1] == "  " + warning
        assert out[2].startswith("sales-amount v1") and len(out) == 3


def test_train_task_line_follows_language():
    # The "Task: <task> - <reason>" line of `mide train` is translated in French.
    import pandas as pd

    from mide.automl.task_detector import TaskInfo, TaskType, detect_task
    from mide.cli import _task_line

    dated = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=12, freq="D"),
        "amount": [1.5 * i + 0.25 for i in range(12)],
    })
    cases = {
        "fr": [
            (detect_task(dated, "amount"),
             "Tâche\u00a0: série temporelle - cible numérique avec la colonne de date 'date'"),
            (detect_task(dated.drop(columns=["date"]), "amount"),
             "Tâche\u00a0: régression - cible numérique continue, pas de colonne de date utilisable"),
            (detect_task(pd.DataFrame({"y": ["a", "b", "a"]}), "y"),
             "Tâche\u00a0: classification - cible non numérique avec 2 classes"),
            (detect_task(pd.DataFrame({"y": [0, 1, 2, 1]}), "y"),
             "Tâche\u00a0: classification - cible entière avec seulement 3 valeurs"),
        ],
        "en": [
            (detect_task(dated, "amount"),
             "Task: time_series - numeric target with date column 'date'"),
            (detect_task(dated.drop(columns=["date"]), "amount"),
             "Task: regression - continuous numeric target, no usable date column"),
            (detect_task(pd.DataFrame({"y": ["a", "b", "a"]}), "y"),
             "Task: classification - non-numeric target with 2 classes"),
        ],
    }
    for language, pairs in cases.items():
        for info, expected in pairs:
            assert _task_line(info, language) == expected
    # Without a known code, the English reason is kept as it is.
    legacy = TaskInfo(TaskType.REGRESSION, "y", "some reason")
    assert _task_line(legacy, "fr") == "Tâche\u00a0: régression - some reason"


def test_broken_sources_file_gives_clear_error(tmp_path, monkeypatch) -> None:
    # A malformed sources.yaml gives "Erreur : ..." / "Error: ..." and exit code 1,
    # not the last-resort "Unexpected error" handler; the language still comes from default.yaml.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "sources.yaml").write_text("sources: [\n", encoding="utf-8")
    args = ["--config-dir", str(cfg)]
    commands = (["scan"], ["sources", "list"], ["sources", "add", str(tmp_path)],
                ["sources", "remove", str(tmp_path)])
    for language, prefix in (("fr", "Erreur\u00a0: Fichier de sources invalide"),
                             ("en", "Error: Invalid sources file")):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        for command in commands:
            result = runner.invoke(app, [*command, *args])
            assert result.exit_code == 1, (language, command, result.output)
            assert result.output.startswith(prefix), (
                language, command, result.output)
            assert "inattendue" not in result.output and "Unexpected" not in result.output
    assert (cfg / "sources.yaml").read_text(encoding="utf-8") == "sources: [\n"


@pytest.mark.parametrize(
    ("models_yaml", "fr_text", "en_text"),
    [
        ("profiles: [\n", "YAML invalide dans", "Invalid YAML in"),
        ("- a\n- b\n", "doit contenir un dictionnaire", "must contain a mapping at top level"),
        ("unknown_key: 1\n", "Configuration invalide dans", "Invalid configuration in"),
    ],
)
def test_broken_models_file_error_follows_language(
    tmp_path, monkeypatch, models_yaml: str, fr_text: str, en_text: str
) -> None:
    # The details of config errors follow the language read from default.yaml.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "models.yaml").write_text(models_yaml, encoding="utf-8")
    for language, prefix, text, other in (("fr", "Erreur\u00a0: ", fr_text, en_text),
                                          ("en", "Error: ", en_text, fr_text)):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["privacy", "--config-dir", str(cfg)])
        assert result.exit_code == 1, (language, result.output)
        assert result.output.startswith(prefix), (language, result.output)
        assert text in result.output and other not in result.output, (language, result.output)
        assert "models.yaml" in result.output


def test_missing_dependency_messages_follow_language(tmp_path, monkeypatch) -> None:
    # `mide index`, `mide auto` and `mide chat` explain a missing optional extra in the
    # configured language, without the "unexpected error" wording.
    from mide import cli
    from mide.llm.runtime import LLMDependencyError
    from mide.rag.embeddings import EmbeddingDependencyError

    data = tmp_path / "data"
    data.mkdir()
    (data / "sales.csv").write_text("x,amount\n1,2\n2,4\n", encoding="utf-8")
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    args = ["--config-dir", str(cfg)]
    assert runner.invoke(app, ["sources", "add", str(data), *args]).exit_code == 0

    def no_embedder(_cfg):
        raise EmbeddingDependencyError("sentence-transformers", "rag")

    def no_llm(_cfg):
        raise LLMDependencyError("llama-cpp-python", "llm")

    class OneDoc:
        def __init__(self, *_a, **_k) -> None:
            pass

        def count(self) -> int:
            return 1

    monkeypatch.setattr(cli, "_get_embedder", no_embedder)
    monkeypatch.setattr(cli, "_get_llm", no_llm)
    monkeypatch.setattr(cli, "retrain_if_changed", lambda *a, **k: [])
    monkeypatch.setattr(cli, "VectorStore", OneDoc)
    expected = {
        "fr": (("Erreur\u00a0: sentence-transformers n'est pas installé. Installez-le avec "
               "`pip install mide-engine[rag]`."),
               ("Indexation\u00a0: ignorée (sentence-transformers n'est pas installé. Installez-le "
               "avec `pip install mide-engine[rag]`).")),
        "en": (("Error: sentence-transformers is not installed. Install it with "
               "`pip install mide-engine[rag]`."),
               ("Index: skipped (sentence-transformers is not installed. Install it with "
               "`pip install mide-engine[rag]`).")),
    }
    for language, (index_error, auto_line) in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["index", *args])
        assert result.exit_code == 1
        assert index_error in result.output
        assert "inattendue" not in result.output and "Unexpected" not in result.output
        result = runner.invoke(app, ["auto", *args])
        assert result.exit_code == 0, result.output
        assert auto_line in result.output
        result = runner.invoke(app, ["chat", *args], input="exit\n")
        assert result.exit_code == 1
        assert index_error in result.output


def test_ask_without_llama_cpp_and_no_figures_gives_clear_error(tmp_path, monkeypatch) -> None:
    # Documents-only question, no llama-cpp-python: a localized error, exit code 1.
    from mide import cli
    from mide.llm.runtime import LLMDependencyError

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))

    def no_llm(_cfg):
        raise LLMDependencyError("llama-cpp-python", "llm")

    monkeypatch.setattr(cli, "_get_llm", no_llm)
    monkeypatch.setattr(cli, "ask_answer", lambda *a, **k: cli._get_llm(None))
    (cfg / "default.yaml").write_text("language: fr\n", encoding="utf-8")
    result = runner.invoke(app, ["ask", "Que dit le rapport annuel ?", "--config-dir", str(cfg)])
    assert result.exit_code == 1
    assert ("Erreur\u00a0: llama-cpp-python n'est pas installé. Installez-le avec "
            "`pip install mide-engine[llm]`.") in result.output


def _write_sales(folder, rows: int = 40) -> None:
    folder.mkdir(parents=True)
    lines = ["x,amount"] + [f"{i},{2 * i + i % 3}" for i in range(rows)]
    (folder / "sales.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_train_refuses_ambiguous_dataset_name(tmp_path, monkeypatch) -> None:
    # Two authorized files named sales.csv: the short name is refused (FR/EN) and lists
    # both paths; the full path picks one and the model gets the short, path-free name.
    import json

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    first, second = tmp_path / "a", tmp_path / "b"
    _write_sales(first)
    _write_sales(second)
    args = ["--config-dir", str(cfg)]
    for folder in (first, second):
        assert runner.invoke(app, ["sources", "add", str(folder), *args]).exit_code == 0
    expected = {
        "fr": "Plusieurs jeux de données s'appellent 'sales'",
        "en": "Several datasets are named 'sales'",
    }
    for language, text in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount", *args])
        assert result.exit_code == 1, result.output
        assert text in result.output
        assert str(first / "sales.csv") in result.output
        assert str(second / "sales.csv") in result.output
    assert not any((tmp_path / "home" / "models_trained").glob("*"))

    full = str((second / "sales.csv").resolve())
    result = runner.invoke(app, ["train", "--dataset", full, "--target", "amount", *args])
    assert result.exit_code == 0, result.output
    assert "sales-amount v1" in result.output
    meta = json.loads(
        (tmp_path / "home" / "models_trained" / "sales-amount" / "v1" / "metadata.json")
        .read_text(encoding="utf-8"))
    assert meta["dataset"] == "sales" and meta["item"] == full


def test_train_model_name_is_the_same_whatever_the_dataset_spelling(tmp_path, monkeypatch) -> None:
    # `sales`, `sales.csv` and the full path are one dataset: one model, new versions.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    folder = tmp_path / "data"
    _write_sales(folder)
    args = ["--config-dir", str(cfg)]
    assert runner.invoke(app, ["sources", "add", str(folder), *args]).exit_code == 0
    full = str((folder / "sales.csv").resolve())
    for version, spelling in enumerate(("sales", "sales.csv", full), start=1):
        result = runner.invoke(app, ["train", "--dataset", spelling, "--target", "amount", *args])
        assert result.exit_code == 0, result.output
        assert f"sales-amount v{version}" in result.output
    assert [p.name for p in (tmp_path / "home" / "models_trained").iterdir()] == ["sales-amount"]


def test_train_warns_about_target_leakage(tmp_path, monkeypatch) -> None:
    # total = 3 x price: the near-perfect score triggers a FR/EN warning naming price,
    # and the suspects are stored in the model metadata. A plausible model has no warning.
    import json

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    folder = tmp_path / "data"
    folder.mkdir()
    lines = ["price,total"] + [f"{i},{3 * i}" for i in range(60)]
    (folder / "orders.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plain = tmp_path / "plain"
    plain.mkdir()
    lines = ["x,amount"] + [f"{i % 5},{10 * (i % 5) + (i * 7) % 11}" for i in range(60)]
    (plain / "sales.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    args = ["--config-dir", str(cfg)]
    for source in (folder, plain):
        assert runner.invoke(app, ["sources", "add", str(source), *args]).exit_code == 0
    expected = {
        "fr": "Attention\u00a0: score presque parfait, fuite de la cible probable. Vérifiez que price",
        "en": "Warning: near-perfect score, likely target leakage. Check that price",
    }
    for language, text in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["train", "--dataset", "orders", "--target", "total", *args])
        assert result.exit_code == 0, result.output
        assert text in result.output
        assert "'total'" in result.output
    meta = json.loads(
        (tmp_path / "home" / "models_trained" / "orders-total" / "v1" / "metadata.json")
        .read_text(encoding="utf-8"))
    assert meta["leakage_suspects"] == ["price"]

    result = runner.invoke(app, ["train", "--dataset", "sales", "--target", "amount", *args])
    assert result.exit_code == 0, result.output
    assert "leakage" not in result.output


def test_auto_outcome_line_explains_leak_blocked_model() -> None:
    # A candidate refused for target leakage is reported as kept, with the reason, in FR/EN.
    from mide.automl.auto import ModelOutcome
    from mide.cli import _auto_outcome_line

    outcome = ModelOutcome("sales-amount", "kept_leak", "candidate suspected of target leakage",
                           5.0, 0.1, target="amount", leakage_suspects=["amount_ttc"])
    assert _auto_outcome_line(outcome, "fr") == (
        "Modèle sales-amount\u00a0: conservé (5 -> 0,1) fuite de la cible probable dans le "
        "nouveau modèle, l'ancien est conservé")
    assert _auto_outcome_line(outcome, "en") == (
        "Model sales-amount: kept (5 -> 0.1) likely target leakage in the new model, "
        "previous model kept")


def test_cli_numbers_follow_french_format(tmp_path, monkeypatch) -> None:
    # scan, train and models trained write numbers in the French format in French
    # ('1 200', '313,4', '31 %', non-breaking spaces) and keep the English one in English.
    import re

    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    folder = tmp_path / "data"
    folder.mkdir()
    lines = ["x,amount"] + [f"{i % 7},{(i * 37) % 101 / 3:.3f}" for i in range(1200)]
    (folder / "sales.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    args = ["--config-dir", str(cfg)]
    assert runner.invoke(app, ["sources", "add", str(folder), *args]).exit_code == 0
    english_number = re.compile(r"\d\.\d|\d%")  # "8,464" is a French decimal
    outputs = {}
    for language in ("fr", "en"):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        output = ""
        for command in (["scan"], ["train", "--dataset", "sales", "--target", "amount"],
                        ["models", "trained"]):
            result = runner.invoke(app, [*command, *args])
            assert result.exit_code == 0, result.output
            output += result.output
        outputs[language] = output.replace(str(tmp_path), "")
    assert "1\u00a0200 lignes" in outputs["fr"] and "1,200 rows" in outputs["en"]
    assert re.search(r"VC mae\u00a0: \d+,\d+ \(référence \d+,\d+\)", outputs["fr"])
    assert re.search(r"x \(\d+\u00a0%\)", outputs["fr"])
    assert re.search(r"x \(\d+%\)", outputs["en"])
    assert re.search(r"mae=\d+,\d+ bat_reference", outputs["fr"])
    assert not english_number.search(outputs["fr"]), outputs["fr"]
    assert english_number.search(outputs["en"])


def test_doctor_numbers_follow_french_format(tmp_path, monkeypatch) -> None:
    # RAM, VRAM and free disk use a decimal comma in French, a dot in English.
    from mide import cli
    from mide.hardware.profiler import GPUInfo, HardwareReport

    report = HardwareReport(ram_gb=15.7, cpu_cores=4, os_name="Linux",
                            gpu=GPUInfo(name="RTX", vram_gb=7.5), disk_free_gb=59.25,
                            profile="medium")
    monkeypatch.setattr(cli, "profile_hardware", lambda: report)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    expected = {
        "fr": ["RAM\u00a0: 15,7 Go", "RTX (7,5 Go de VRAM)", "Espace disque libre\u00a0: 59,25 Go"],
        "en": ["RAM: 15.7 GB", "RTX (7.5 GB VRAM)", "Disk free: 59.25 GB"],
    }
    for language, texts in expected.items():
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["doctor", "--config-dir", str(cfg)])
        assert result.exit_code == 0, result.output
        for text in texts:
            assert text in result.output, language


def test_models_pull_size_follows_french_format() -> None:
    from mide.cli import _fmt_size

    assert _fmt_size(1_930_000_000, "fr") == "1,93 Go"
    assert _fmt_size(1_930_000_000, "en") == "1.93 GB"
    assert _fmt_size(None, "fr") == "?"
