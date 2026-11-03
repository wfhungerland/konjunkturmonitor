import pandas as pd

from monitor.answers import answer, num


def s(vals, freq="MS", start="2024-01-01"):
    return pd.Series(vals, index=pd.date_range(start, periods=len(vals), freq=freq))


def test_num_german_format():
    assert num(1234.5) == "1.234,5" and num(-0.25, 2) == "−0,25" and num(0.3, sign=True) == "+0,3"


def test_growth_sentence_and_verdict():
    data = {"g": s([0.4, 0.1, 0.2], "QS"), "y": s([1.0, 1.1, 1.3], "QS")}
    a = answer({"id": "wachstum", "kind": "growth", "series": "g", "yoy": "y"}, data)
    assert a["head"].startswith("Im 3. Quartal 2024 ist die Wirtschaft um 0,2 % gewachsen")
    assert a["verdict"] == "wächst leicht" and "Gegenüber dem Vorjahr: +1,3 %." in a["more"]


def test_inflation_target_wording():
    a = answer({"id": "preise", "kind": "inflation", "series": "p"}, {"p": s([3.3, 2.8])})
    assert a["head"] == "Im Februar 2024 waren die Preise um 2,8 % höher als ein Jahr zuvor."
    assert a["verdict"] == "über dem Ziel" and "gesunken" in a["more"][0]


def test_index_three_month_comparison():
    data = {"ip": s([100, 100, 100, 101, 102, 103])}
    a = answer({"id": "industrie", "kind": "index_mom", "series": "ip"}, data)
    assert "1,0 % mehr hergestellt" in a["head"] and a["verdict"] == "zieht an"


def test_missing_series_gives_none():
    assert answer({"id": "export", "kind": "level_mom", "series": "x"}, {}) is None
