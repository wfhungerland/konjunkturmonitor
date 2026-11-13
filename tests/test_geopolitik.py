import io

import pandas as pd

from monitor import geopolitik
from monitor.build import chart_sentences


def test_gpr_rescaled_to_1985_2019_mean():
    months = pd.date_range("1985-01-01", "2020-12-01", freq="MS")
    df = pd.DataFrame({"month": months, "GPRC_DEU": 0.5, "GPR": 80.0})
    df.loc[df["month"] >= "2020-01-01", "GPRC_DEU"] = 1.0
    buf = io.BytesIO()
    df.to_stata(buf, write_index=False)
    out = geopolitik.gpr(buf.getvalue())
    assert round(out["gpr_de"].loc["2019-12-01"], 6) == 100
    assert round(out["gpr_de"].loc["2020-06-01"], 6) == 200
    assert round(out["gpr_world"].mean(), 6) == 100


def test_leiden_counts_quarters_and_germany(tmp_path):
    rows = [(2024, "January", "Germany"), (2024, "February", "France"), (2024, "March", "Germany; Poland"),
            (2024, "November", "Poland"), (2025, "Unknown", "Germany")]
    df = pd.DataFrame(rows, columns=["IncidentYear", "IncidentMonth", "Where"])
    path = tmp_path / "leiden.xlsx"
    df.to_excel(path, sheet_name="EventData", index=False)
    out = geopolitik.leiden(path)
    de, eu = out["leiden_ops_de"], out["leiden_ops_eu"]
    assert de.loc["2024-01-01"] == 2 and eu.loc["2024-01-01"] == 1  # Vorfall in mehreren Ländern zählt für Deutschland
    assert eu.loc["2024-10-01"] == 1 and de.loc["2024-07-01"] == 0  # leere Quartale als 0
    assert de.sum() == 2  # ohne bekannten Monat nicht gezählt


def test_cow_germany_no_double_count(tmp_path):
    rows = [(255, 1945, 0.08), (265, 1954, 0.01), (260, 1955, 0.04), (265, 1955, 0.01),
            (260, 1990, 0.03), (265, 1990, 0.01), (255, 1990, 0.035), (2, 1990, 0.15)]
    path = tmp_path / "nmc.csv"
    pd.DataFrame(rows, columns=["ccode", "year", "cinc"]).to_csv(path, index=False)
    s = geopolitik.cow(path)["cow_cinc_deu"]
    s.index = s.index.year
    assert list(s.index) == [1945, 1955, 1990]  # 1954 nur die DDR: kein Wert
    assert round(s[1955], 6) == 5 and round(s[1990], 6) == 3.5


def test_annual_count_sentence():
    x = [f"{y}-{m:02d}-01" for y in (2024, 2025) for m in (1, 4, 7, 10)]
    c = {"freq": "Q", "series": [{"id": "a", "x": x, "y": [1, 2, 3, 4, 1, 1, 1, 1]}, {"id": "b", "x": x, "y": [5] * 8}],
         "annual_count": {"verb": "zählt die Datenbank", "series": {"a": "Vorfälle in Deutschland", "b": "im übrigen Europa"}}}
    assert chart_sentences(c) == ["Im Jahr 2025 zählt die Datenbank 4 Vorfälle in Deutschland und 20 im übrigen Europa, nach 10 und 20 im Jahr 2024."]


def test_gta_counts_harmful_affecting_germany(tmp_path):
    rows = [("Red", "China", "Germany, France", "2020-03-01"), ("Amber", "United States of America", "Germany", "2020-05-01"),
            ("Green", "China", "Germany", "2020-06-01"), ("Red", "India", "France", "2020-07-01"),
            ("Red", "Brazil", "Germany", "2021-01-01"), ("Red", "China", "East Germany", "2021-02-01")]
    path = tmp_path / "gta.csv"
    pd.DataFrame(rows, columns=["GTA Evaluation", "Implementing Jurisdictions", "Affected Jurisdictions", "Date Implemented"]).to_csv(path, index=False)
    out = {k: v.set_axis(v.index.year) for k, v in geopolitik.gta(path).items()}
    assert out["gta_de_chn"][2020] == 1 and out["gta_de_chn"][2021] == 0  # grün und Namensähnlichkeit zählen nicht
    assert out["gta_de_usa"][2020] == 1 and out["gta_de_other"][2021] == 1 and out["gta_de_other"][2020] == 0


def test_trade_sums_partners_over_twelve_months(monkeypatch):
    import json
    monkeypatch.setattr(geopolitik, "TRADE", {"a": ["RU", "BY"], "b": ["KG"]})
    times = [f"2020-{m:02d}" for m in range(1, 13)] + ["2021-01", "2021-02"]
    partners = ["BY", "KG", "RU"]
    value = {}
    for p, part in enumerate(partners):
        for t, _ in enumerate(times[:-1]):  # letzter Monat fehlt noch
            value[str(p * len(times) + t)] = {"RU": 2e9, "BY": 1e9, "KG": 0.5e9}[part]
    raw = json.dumps({"id": ["partner", "time"], "size": [3, len(times)], "value": value,
                      "dimension": {"partner": {"category": {"index": {p: i for i, p in enumerate(partners)}}},
                                    "time": {"category": {"index": {t: i for i, t in enumerate(times)}}}}})
    out = geopolitik.trade(raw)
    assert list(out["a"].index.strftime("%Y-%m")) == ["2020-12", "2021-01"]  # erst ab zwölf Monaten, ohne fehlenden Monat
    assert out["a"].iloc[-1] == 36 and out["b"].iloc[-1] == 6


def test_kmpt_reads_origin_table(tmp_path):
    rows = [[None, "Figure 3"], [None, None], [None, "Year", "Germany only", "Germany and foreign partnership", "European, non-Germany", "Non-European only", "Total"],
            [None, 2024, 25.0, 11.0, 0.0, 4.3, 40.3], [None, 2099, 1.0, 1.0, 1.0, 1.0, 4.0], [None, "Total", 26.0, 12.0, 1.0, 5.3, 44.3]]
    path = tmp_path / "kmpt.xlsx"
    months = [[None, "Month", "Total military orders"]] + [[None, pd.Timestamp(2024, m, 1), float(m)] for m in range(1, 13)] + [[None, pd.Timestamp(2025, 1, 1), 0.0], [None, "Total", 78.0]]
    with pd.ExcelWriter(path) as w:
        pd.DataFrame(rows).to_excel(w, sheet_name="Fig 3 DE Origin (%)", header=False, index=False)
        pd.DataFrame([[None, "Figure A1"]] + months).to_excel(w, sheet_name="A1 DE Total Orders", header=False, index=False)
    out = geopolitik.kmpt(path)
    assert list(out["kmpt_de_orders_12m"].round(1)) == [78.0, 77.0]  # Summe 1 bis 12, dann ohne Januar 2024
    assert list(out["kmpt_noneu"].index.year) == [2024]  # ohne laufendes oder künftiges Jahr und ohne Summenzeile
    assert out["kmpt_de_only"].iloc[0] == 25.0 and out["kmpt_noneu"].iloc[0] == 4.3
