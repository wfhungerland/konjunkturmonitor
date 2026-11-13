"""Sperre vor der Veröffentlichung: auffällige Reihen bleiben auf dem letzten geprüften Stand."""
import json
from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd

from monitor.sperre import anomaly, apply, load_releases

IDX = pd.date_range("2020-01-01", periods=60, freq="MS")
CALM = pd.Series(100 + np.random.default_rng(1).normal(0, 1, 60).cumsum(), index=IDX)


def test_anomaly_rules():
    nxt = IDX[-1] + pd.offsets.MonthBegin()
    assert anomaly(CALM, CALM) is None
    assert anomaly(CALM, pd.concat([CALM, pd.Series([CALM.iloc[-1] + 0.5], index=[nxt])])) is None  # gewöhnlicher neuer Monat
    assert anomaly(CALM, CALM + 0.05) is None                                                        # übliche Revision
    assert "fehlen" in anomaly(CALM, CALM.iloc[30:])                                                 # Regel 1: Werte verloren
    assert "weichen stark" in anomaly(CALM, CALM * 1000)                                             # Regel 2: andere Einheit
    assert "weichen stark" in anomaly(CALM, CALM / CALM.iloc[40] * 100 + 30)                         # Regel 2: neue Basis
    assert "jüngste Veränderung" in anomaly(CALM, pd.concat([CALM, pd.Series([CALM.iloc[-1] + 60], index=[nxt])]))  # Regel 3
    assert anomaly(CALM.iloc[:10], CALM.iloc[:10] * 1000) is None                                    # zu kurz für ein Urteil


def _run(tmp_path, new: dict, releases=None, derive=None):
    def tidy(d):
        return pd.concat([pd.DataFrame({"series_id": k, "date": v.index, "value": v.values, "unit": "x", "source": "s",
                                        "retrieved_at": "2026-11-12T08:00:00Z"}) for k, v in d.items()], ignore_index=True)
    previous = tidy({"a": CALM, "b": CALM, "c": CALM * 2})
    result = SimpleNamespace(observations=tidy(new), statuses=[
        SimpleNamespace(series_id=k, status="ok", n_obs=len(v), last="", last_value=None, retrieved_at="", message="") for k, v in new.items()])
    catalog = SimpleNamespace(series=[SimpleNamespace(id=k, frequency="M", derive=(derive or {}).get(k, {})) for k in new])
    if releases is not None:
        (tmp_path / "data" / "static").mkdir(parents=True)
        (tmp_path / "data" / "static" / "freigaben.yaml").write_text(json.dumps({"freigaben": releases}), encoding="utf-8")
    frozen = apply(result, previous, catalog, tmp_path, today=date(2026, 11, 13))
    return frozen, result


def test_apply_freezes_only_the_affected_series(tmp_path):
    frozen, result = _run(tmp_path, {"a": CALM * 1000, "b": CALM + 0.01, "c": CALM * 2}, derive={"c": {"from": "a"}})
    assert [f["series_id"] for f in frozen] == ["a", "c"]  # c wird aus a berechnet und bleibt mit stehen
    obs = result.observations
    assert np.allclose(obs[obs.series_id == "a"]["value"], CALM.values)           # alter Stand
    assert np.allclose(obs[obs.series_id == "b"]["value"], (CALM + 0.01).values)  # unauffällige Reihe: neuer Stand
    assert result.statuses[0].message.startswith("angehalten") and result.statuses[1].message == ""
    saved = json.loads((tmp_path / "data" / "processed" / "sperre.json").read_text(encoding="utf-8"))
    assert saved["angehalten"][0] == {"series_id": "a", "grund": frozen[0]["grund"], "seit": "2026-11-13"}


def test_release_lets_new_values_through(tmp_path):
    new = {"a": CALM * 1000, "b": CALM, "c": CALM * 2}
    assert _run(tmp_path / "1", new, releases=[{"reihe": "a", "bis": "2026-11-20", "grund": "geprüft"}])[0] == []
    assert _run(tmp_path / "2", new, releases=[{"reihe": "*", "bis": "2026-11-13", "grund": "Schock"}])[0] == []
    assert len(_run(tmp_path / "3", new, releases=[{"reihe": "a", "bis": "2026-11-12", "grund": "abgelaufen"}])[0]) == 1
    assert load_releases(tmp_path / "leer") == set()
