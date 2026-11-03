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


def test_start_rows_pct3_and_relation():
    idx = pd.date_range("2014-01-01", periods=150, freq="MS")
    data = {"x": pd.Series([100 + i for i in range(150)], index=idx, dtype=float)}
    rows = _start_rows({"start_table": [{"label": "X", "series": "x", "show": "pct3", "unit": "%", "topic": "t"}]}, data)
    assert rows and rows[0]["value"] > 0 and rows[0]["rel"]


def test_calendar_rules(tmp_path):
    (tmp_path / "data" / "static").mkdir(parents=True)
    (tmp_path / "data" / "static" / "kalender.yaml").write_text(
        "items:\n  - {name: A, rule: {workday: 1}}\n  - {name: B, rule: {last_workday: 0}}\n  - {name: C, rule: {weekday: 1}}\n", encoding="utf-8")
    cal = _calendar(tmp_path, pd.Timestamp("2026-11-03"), 1)
    names = [e["name"] for e in cal["events"]]
    assert names.count("A") == 1 and names.count("B") == 1 and names.count("C") == 4
    assert cal["events"][0]["date"] == "2026-11-02"
