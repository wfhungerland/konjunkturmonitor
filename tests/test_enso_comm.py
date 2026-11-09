import io

import numpy as np
import pandas as pd

from monitor.build import _enso_comm
from monitor.pinksheet import parse


def _roni(idx):
    # abwechselnd 24 Monate El Niño (1,0) und 24 Monate neutral (0,0)
    return pd.Series([1.0 if (i // 24) % 2 == 0 else 0.0 for i in range(len(idx))], index=idx)


def test_enso_comm_separates_phases():
    idx = pd.date_range("1975-01-01", "2024-12-01", freq="MS")
    roni = _roni(idx)
    # Preis wächst 6 Monate nach El Niño stärker: monatliche Rate hängt von der Phase 6 Monate zuvor ab
    phase = roni.shift(6).fillna(0)
    price = pd.Series(np.exp(np.cumsum(np.where(phase > 0.5, 0.02, 0.0))), index=idx) * 100
    flat = pd.Series(100.0 + np.sin(np.arange(len(idx))), index=idx)
    data = {"enso_roni": roni, "a": price, "b": flat, "c": flat * 2}
    E = _enso_comm({"items": {"a": "A", "b": "B", "c": "C"}, "lag": 6}, data)
    a = next(r for r in E["rows"] if r["id"] == "a")
    assert a["nino"] > a["neutral"] and a["sig"]
    assert E["rows"][-1]["id"] == "a"  # größter Abstand zuletzt


def test_pinksheet_parse_reads_named_columns():
    head = [["World Bank Commodity Price Data (The Pink Sheet)"] + [None] * 9, [None] * 10, [None] * 10, ["Updated on November 03, 2026"] + [None] * 9,
            [None, "Crude oil, average", "Soybeans", "Maize", "Rice, Thai 5% ", "Wheat, US HRW", "Cocoa", "Coffee, Robusta", "Palm oil", "Sugar, world"],
            [None, "($/bbl)", "($/mt)", "($/mt)", "($/mt)", "($/mt)", "($/kg)", "($/kg)", "($/mt)", "($/kg)"]]
    rows = [[f"{1960 + i // 12}M{i % 12 + 1:02d}"] + [1.0 + i / 100] * 9 for i in range(300)]
    rows[3][3] = "…"
    buf = io.BytesIO()
    pd.DataFrame(head + rows).to_excel(buf, sheet_name="Monthly Prices", header=False, index=False)
    out = parse(buf.getvalue())
    assert set(out) == {"soybeans", "maize", "rice", "wheat", "cocoa", "coffee", "palmoil", "sugar"}
    assert len(out["maize"]) == 299 and out["soybeans"].index[0] == pd.Timestamp("1960-01-01")
