"""Abgleich mit der Projektion: nötige Rate je fehlendem Quartal."""
import pandas as pd

from monitor.build import _projection


def test_projection(tmp_path):
    (tmp_path / "data" / "static").mkdir(parents=True)
    (tmp_path / "data" / "static" / "prognosen.yaml").write_text(
        "- {by: Bundesregierung, round: Frühjahrsprojektion 2026, date: 2026-04-22, values: {2026: 0.5}}\n"
        "- {by: Bundesregierung, round: Herbstprojektion 2026, date: 2026-10-08, values: {2026: 1.0}}\n", encoding="utf-8")
    q = pd.date_range("2025-01-01", periods=7, freq="QS")
    idx = pd.Series([100.0] * 4 + [101, 101, 101], index=q)  # gleiche Gewichte im Vorjahr
    yoy = pd.Series([0.0] * 4 + [1.0, 1.0, 0.4], index=q)
    p = _projection({}, {"de_gdp_index": idx, "de_gdp_yoy": yoy, "de_gdp_qoq": idx.pct_change() * 100}, tmp_path)
    assert p["year"] == 2026 and p["rest"] == [4] and p["round"] == "Herbstprojektion 2026"
    assert abs(p["need"] - 1.6) < 1e-9  # 4 * 1,0 - (1,0 + 1,0 + 0,4)
    assert abs(p["need_qoq"] - (100 * 1.016 / 101 - 1) * 100) < 1e-9
    assert p["prev"] == {"round": "Frühjahrsprojektion 2026", "value": 0.5}
    assert p["series"][0]["req"] == 1 and p["series"][0]["y"][-1] == 1.6
