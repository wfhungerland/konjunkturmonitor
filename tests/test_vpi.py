import pandas as pd

from monitor.answers import inflation


def test_inflation_lists_vpi_parts_of_same_month():
    idx = pd.date_range("2026-08-01", periods=3, freq="MS")
    data = {"cpi": pd.Series([2.1, 2.4, 2.8], idx), "en": pd.Series([1.0, 2.0, 3.5], idx),
            "old": pd.Series([1.0, 1.5], idx[:2])}
    a = inflation({"series": "cpi", "parts": {"Energie": "en", "Alt": "old"}}, data)
    joined = " ".join(a["more"])
    assert "Energie +3,5 %" in joined and "Alt" not in joined
