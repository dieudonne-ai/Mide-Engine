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
               "Le format doit être 'md' ou 'html'.", f"Rapport écrit : {out}"),
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
    assert "Indexation : ignorée (sentence-transformers is not installed)." in result.output
    assert len(calls) == 1 and any("sales.csv" in key for key in calls[0])
    assert "Aucun modèle entraîné" in result.output


def test_error_prefix_follows_language(tmp_path, monkeypatch) -> None:
    # Command failures use "Erreur :" in French (default) and "Error:" in English.
    monkeypatch.setenv("MIDE_HOME", str(tmp_path / "home"))
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    args = ["--config-dir", str(cfg)]
    for language, prefix in (("fr", "Erreur : "), ("en", "Error: ")):
        (cfg / "default.yaml").write_text(f"language: {language}\n", encoding="utf-8")
        result = runner.invoke(app, ["train", "--dataset", "nope", "--target", "y", *args])
        assert result.exit_code == 1, language
        assert result.output.startswith(prefix), (language, result.output)
    # A broken config cannot give its language: the default (French) is used.
    (cfg / "default.yaml").write_text("language: [\n", encoding="utf-8")
    for command in (["models", "list"], ["index"], ["privacy"], ["auto"], ["finetune"]):
        result = runner.invoke(app, [*command, *args])
        assert result.exit_code == 1, command
        assert result.output.startswith("Erreur : "), (command, result.output)


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
            "Analyse : 1 jeux de données/documents.",
            "Indexation : ignorée (sentence-transformers is not installed).",
            "Modèle a : remplacé (3 -> 2) le nouveau modèle est meilleur",
            "Modèle b : conservé (2 -> 2.5) l'ancien modèle est conservé",
            "Modèle c : inchangé",
            "Modèle d : ignoré le jeu de données n'est plus disponible",
            "Modèle e : erreur boom",
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
             "Tâche : série temporelle - cible numérique avec la colonne de date 'date'"),
            (detect_task(dated.drop(columns=["date"]), "amount"),
             "Tâche : régression - cible numérique continue, pas de colonne de date utilisable"),
            (detect_task(pd.DataFrame({"y": ["a", "b", "a"]}), "y"),
             "Tâche : classification - cible non numérique avec 2 classes"),
            (detect_task(pd.DataFrame({"y": [0, 1, 2, 1]}), "y"),
             "Tâche : classification - cible entière avec seulement 3 valeurs"),
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
    assert _task_line(legacy, "fr") == "Tâche : régression - some reason"


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
    for language, prefix in (("fr", "Erreur : Fichier de sources invalide"),
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
    for language, prefix, text, other in (("fr", "Erreur : ", fr_text, en_text),
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
        "fr": (("Erreur : sentence-transformers n'est pas installé. Installez-le avec "
               "`pip install mide-engine[rag]`."),
               ("Indexation : ignorée (sentence-transformers n'est pas installé. Installez-le "
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
    assert ("Erreur : llama-cpp-python n'est pas installé. Installez-le avec "
            "`pip install mide-engine[llm]`.") in result.output
