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


def test_chart_text_and_outliers():
    from monitor.build import _outliers, chart_text
    x = [d.strftime("%Y-%m-%d") for d in pd.date_range("2014-01-01", periods=150, freq="MS")]
    y = [100 + (i % 3) * 0.5 for i in range(150)]
    y[-5] = 140.0
    c = {"type": "line", "unit": "Index 2021=100", "decimals": 1, "freq": "M",
         "series": [{"id": "a", "label": "Aufträge", "freq": "M", "x": x, "y": y}]}
    assert chart_text(c).startswith("Im Juni 2026 lag der Wert für „Aufträge“ ") and "Vorjahresmonats." in chart_text(c)
    out = _outliers(c)
    assert out and out[0]["date"] == x[-5]
    s = {"type": "stacked", "unit": "Pp", "decimals": 1, "freq": "Q", "series": [
        {"id": "b", "label": "Konsum", "style": "bar", "x": ["2026-07-01"], "y": [0.2]},
        {"id": "t", "label": "BIP", "style": "line", "x": ["2026-07-01"], "y": [-0.04]}]}
    assert chart_text(s) == "Im 3. Quartal 2026 lag die Rate insgesamt bei 0,0 %. Im 3. Quartal 2026 trug „Konsum“ am meisten bei: +0,2 Pp."


def test_archive_revisions_and_news(tmp_path):
    from monitor.reuse import mark_revisions, news, update_archive
    r1 = [{"series": "x", "label": "X", "date": "2026-08-01", "period": "August 2026", "value": 1.0, "decimals": 1}]
    update_archive(tmp_path, r1, "2026-10-01")
    r2 = [{"series": "x", "label": "X", "date": "2026-09-01", "period": "September 2026", "value": 2.0, "decimals": 1}]
    arch = update_archive(tmp_path, r2, "2026-11-01")
    assert [n["period"] for n in news(arch, "2026-11-01")] == ["September 2026"]
    r3 = [{"series": "x", "label": "X", "date": "2026-09-01", "period": "September 2026", "value": 2.3, "decimals": 1}]
    arch = update_archive(tmp_path, r3, "2026-11-02")
    mark_revisions(r3, arch)
    assert r3[0]["revised"] == {"from": 2.0, "stand": "2026-11-01"}
    assert len(arch) == 3


def test_gdp_revisions_first_and_latest():
    from monitor.wetter import gdp_revisions
    hdr = ("DATAFLOW;BBK_STD_FREQ;BBK_STD_AREA;BBK_STD_ADJUSTMENT;BBK_RTD_ACCOUNTSYS;BBK_RTD_IND_CATEG;BBK_RTD_IND_IDENT;BBK_PRICEUNIT;"
           "BBK_RTD_CALCBASIS;BBK_RTD_REL_YEAR;BBK_RTD_REL_MONTH;BBK_RTD_REL_DAY;TIME_PERIOD;OBS_VALUE")
    rows = [("2026;08;25", "2026-Q1", 100), ("2026;08;25", "2026-Q2", 100.5),
            ("2026;10;30", "2026-Q1", 100), ("2026;10;30", "2026-Q2", 100.3), ("2026;10;30", "2026-Q3", 100.5)]
    text = "﻿" + hdr + "\n" + "\n".join(f"BBK:BBKRT(1.0);Q;DE;Y;A;AG1;CA010;A;I;{v};{p};{x}" for v, p, x in rows)
    first, latest = gdp_revisions(text)
    assert first.round(2).tolist() == [0.5, 0.2]   # Q2 zuerst mit 0,5 % gemeldet, Q3 mit 0,2 %
    assert latest.round(2).tolist() == [0.3, 0.2]  # Q2 heute 0,3 %
