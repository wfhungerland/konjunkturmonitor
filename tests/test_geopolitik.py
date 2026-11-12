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
