"""Tests for scheduled auto-learning."""

from __future__ import annotations

import pandas as pd
import pytest

from mide.automl import auto
from mide.automl.registry import list_models, save_model
from mide.automl.trainer import train


@pytest.fixture
def setup(tmp_path):
    rng_df = pd.DataFrame(
        {"x": range(120), "z": [i % 7 for i in range(120)], "amount": [3.0 * i + (i % 7) for i in range(120)]}
    )
    model = train(rng_df, "amount", profile="tiny", seed=1)
    reg = tmp_path / "reg"
    save_model(model, reg, "sales-amount", {"dataset": "sales", "data_hash": auto.fingerprint(rng_df)})
    return rng_df, reg, tmp_path / "state.json"


def test_unchanged_data_does_not_retrain(setup, monkeypatch):
    df, reg, state = setup
    monkeypatch.setattr(auto, "train", lambda *a, **k: pytest.fail("must not retrain"))
    out = auto.retrain_if_changed({"sales.csv": df}, reg, state, profile="tiny")
    assert [o.status for o in out] == ["unchanged"]
    assert len(list_models(reg)) == 1


def test_changed_data_promotes_only_if_better(setup):
    df, reg, state = setup
    bigger = pd.concat([df, df.assign(x=df.x + 120, amount=df.amount + 360)], ignore_index=True)
    out = auto.retrain_if_changed({"sales.csv": bigger}, reg, state, profile="tiny")
    assert out[0].status in ("promoted", "kept")
    expected = 2 if out[0].status == "promoted" else 1
    assert len(list_models(reg)) == expected
    # Second run on the same data: fingerprint recorded, nothing retrained.
    again = auto.retrain_if_changed({"sales.csv": bigger}, reg, state, profile="tiny")
    assert again[0].status == "unchanged"


def test_worse_model_is_kept_out(setup, monkeypatch):
    df, reg, state = setup
    real = auto.train

    def worse(*a, **k):
        m = real(*a, **k)
        m.metrics = {key: v * 10 + 100 for key, v in m.metrics.items()}
        return m

    monkeypatch.setattr(auto, "train", worse)
    out = auto.retrain_if_changed({"sales.csv": df.assign(amount=df.amount + 1)}, reg, state, "tiny")
    assert out[0].status == "kept"
    assert len(list_models(reg)) == 1


def test_missing_dataset_skipped(setup):
    _df, reg, state = setup
    out = auto.retrain_if_changed({}, reg, state, profile="tiny")
    assert out[0].status == "skipped"


def test_recorded_item_is_matched_exactly(tmp_path):
    # A model that recorded its exact file is retrained on it, never on another file
    # with the same name; when that file is gone the model is skipped.
    df = pd.DataFrame({"x": range(60), "amount": [2.0 * i for i in range(60)]})
    reg = tmp_path / "reg"
    save_model(train(df, "amount", profile="tiny", seed=1), reg, "sales-amount",
               {"dataset": "sales", "item": "/a/sales.csv", "data_hash": auto.fingerprint(df)})
    other = df.assign(amount=df.amount + 5)
    out = auto.retrain_if_changed({"/b/sales.csv": other}, reg, tmp_path / "s.json", "tiny")
    assert [o.status for o in out] == ["skipped"]
    out = auto.retrain_if_changed(
        {"/b/sales.csv": other, "/a/sales.csv": df}, reg, tmp_path / "s.json", "tiny")
    assert [o.status for o in out] == ["unchanged"]


def test_promoted_outcome_reports_target_leakage(tmp_path):
    # New data adds a column computed from the target: the retrained model is better
    # (so promoted) but the outcome names the leaking column and the target.
    rows = range(120)
    df = pd.DataFrame({"x": [i % 10 for i in rows],
                       "amount": [10.0 * (i % 10) + (i * 7) % 23 for i in rows]})
    reg, state = tmp_path / "reg", tmp_path / "state.json"
    plain = train(df, "amount", profile="tiny", seed=1)
    assert plain.leakage_suspects == []
    save_model(plain, reg, "sales-amount", {"dataset": "sales", "data_hash": auto.fingerprint(df)})
    leaky = df.assign(amount_ttc=df.amount * 1.18)
    out = auto.retrain_if_changed({"sales.csv": leaky}, reg, state, profile="tiny")
    assert out[0].status == "promoted"
    assert out[0].target == "amount"
    assert out[0].leakage_suspects[0] == "amount_ttc"
    assert list_models(reg)[-1].metadata["leakage_suspects"][0] == "amount_ttc"
    # Nothing is reported for an unchanged dataset.
    again = auto.retrain_if_changed({"sales.csv": leaky}, reg, state, profile="tiny")
    assert again[0].status == "unchanged" and again[0].leakage_suspects == []
