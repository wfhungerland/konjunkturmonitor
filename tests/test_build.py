import pandas as pd

from monitor.build import _band, _calendar, _start_rows, _workdays


def test_workdays_skip_weekend_and_fixed_holidays():
    days = _workdays(2026, 10)
    assert all(d.weekday() < 5 for d in days)
    assert pd.Timestamp("2026-10-03") not in days


def test_band_uses_2015_to_2019():
    s = pd.Series(range(120), index=pd.date_range("2012-01-01", periods=120, freq="MS"), dtype=float)
    b = _band(s)
    assert b["lo"] == 36 and b["hi"] == 95


def test_start_rows_comparisons_and_tendency():
    idx = pd.date_range("2014-01-01", periods=150, freq="MS")
    data = {"x": pd.Series([100 + i for i in range(150)], index=idx, dtype=float),
            "r": pd.Series([2.0] * 149 + [2.5], index=idx, dtype=float),
            "n": pd.Series([50.0] * 150, index=idx, dtype=float)}
    cfg = {"start_table": [{"label": "X", "series": "x", "kind": "level", "unit": "Index", "topic": "t"},
                           {"label": "R", "series": "r", "kind": "rate", "unit": "%", "up_bad": True, "topic": "t"},
                           {"label": "N", "series": "n", "kind": "level", "seasonal": True, "unit": "Anzahl", "topic": "u"}]}
    x, r, n = _start_rows(cfg, data, {}, {"t": "Thema"})
    assert x["group"] == "Thema" and x["prev"] > 0 and x["yoy"] > 0 and x["m3"] > 0 and x["tendency"] == "up" and x["change_unit"] == "%"
    assert abs(r["prev"] - 0.5) < 1e-9 and r["change_unit"] == "Pp" and r["tendency"] == "up"
    assert n["prev"] is None and n["m3"] is None and n["yoy"] == 0 and n["tendency"] == "flat"


def test_calendar_rules(tmp_path):
    (tmp_path / "data" / "static").mkdir(parents=True)
    (tmp_path / "data" / "static" / "kalender.yaml").write_text(
        "items:\n  - {name: A, rule: {workday: 1}}\n  - {name: B, rule: {last_workday: 0}}\n  - {name: C, rule: {weekday: 1}}\n", encoding="utf-8")
    cal = _calendar(tmp_path, pd.Timestamp("2026-11-03"), 1)
    names = [e["name"] for e in cal["events"]]
    assert names.count("A") == 1 and names.count("B") == 1 and names.count("C") == 4
    assert cal["events"][0]["date"] == "2026-11-02"
