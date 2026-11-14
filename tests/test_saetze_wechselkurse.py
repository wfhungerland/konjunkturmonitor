from monitor.build import chart_sentences


def test_tpl_decimals_round_only_the_sentence():
    x = ["2025-11-13", "2026-11-13"]
    c = {"type": "line", "freq": "B", "unit": "US-$ je €", "decimals": 4, "tpl_decimals": 3,
         "series": [{"id": "usd", "x": x, "y": [1.1622, 1.1052]}], "tpl": ["{when} ${n[usd]} ({chg[usd]})."]}
    assert chart_sentences(c) == ["Am 13. November 2026 $1,105 (-4,9 %)."]
