"""Abgleich mit der Projektion: nötige Rate je fehlendem Quartal (exakt aus Quartalssummen)."""
import pandas as pd

from monitor.build import _nwj, _projection

Q = pd.date_range("2025-01-01", periods=7, freq="QS")


def _setup(tmp_path, ka="values_ka: {2026: 0.8}, "):
    (tmp_path / "data" / "static").mkdir(parents=True)
    (tmp_path / "data" / "static" / "prognosen.yaml").write_text(
        "- {by: Bundesregierung, round: Frühjahrsprojektion 2026, date: 2026-04-22, values: {2026: 0.5}}\n"
        "- {by: Bundesregierung, round: Herbstprojektion 2026, date: 2026-10-08, " + ka + "values: {2026: 1.0}}\n", encoding="utf-8")


def _data():
    nsa = pd.Series([100.0, 98.0, 101.0, 103.0, 101.0, 99.0, 101.5], index=Q)
    sa = pd.Series([100.0, 100.2, 100.4, 100.6, 100.8, 101.0, 101.1], index=Q)
    yoy = pd.Series([0.0] * 4 + [1.0, 1.0, 0.5], index=Q)
    return {"de_gdp_index_nsa": nsa, "de_gdp_index": sa, "de_gdp_yoy": yoy, "de_gdp_qoq": sa.pct_change() * 100}


def test_projection_exact(tmp_path):
    _setup(tmp_path)
    p = _projection({}, _data(), tmp_path)
    assert p["year"] == 2026 and p["rest"] == [4] and p["round"] == "Herbstprojektion 2026"
    s = 1.01 * 402.0 - (101.0 + 99.0 + 101.5)  # nötige Summe des fehlenden Quartals
    assert abs(p["need"] - (s / 103.0 - 1) * 100) < 1e-9
    g = (1.008 * (100.0 + 100.2 + 100.4 + 100.6) - (100.8 + 101.0 + 101.1)) / 101.1 - 1
    assert abs(p["need_qoq"] - g * 100) < 1e-6
    assert p["alt"]["series"][0]["y"][-1] == round(g * 100, 2)
    assert p["prev"] == {"round": "Frühjahrsprojektion 2026", "value": 0.5}
    assert p["series"][0]["req"] == 1


def test_no_adjusted_target_no_switch(tmp_path):
    _setup(tmp_path, ka="")
    p = _projection({}, _data(), tmp_path)
    assert p["need"] is not None and p["need_qoq"] is None and p["alt"] is None


def test_full_year(tmp_path):
    _setup(tmp_path)
    d = _data()
    q = pd.date_range("2025-01-01", periods=8, freq="QS")
    d["de_gdp_index_nsa"] = pd.Series([100.0, 98.0, 101.0, 103.0, 101.0, 99.0, 101.5, 104.0], index=q)
    p = _projection({}, d, tmp_path)
    assert p["rest"] == [] and abs(p["done_rate"] - (405.5 / 402.0 - 1) * 100) < 1e-9


def test_nwj_several_quarters():
    g = _nwj(100.0, 100.0, 3, 100.0 + 100.0 * (1.01 + 1.01 ** 2 + 1.01 ** 3))
    assert abs(g - 0.01) < 1e-9
