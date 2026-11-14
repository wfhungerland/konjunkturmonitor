from monitor.build import chart_sentences


def test_tpl_mark_and_inverse_change_for_deficit():
    x = ["2025-04-01", "2026-04-01"]
    c = {"type": "line", "freq": "Q", "unit": "% des BIP", "decimals": 1, "tpl_mark": 3, "tpl_mark_abs": True,
         "series": [{"id": "b", "x": x, "y": [-2.4, -4.1]}], "tpl": ["{abs[b]} %, {dabs[b]} Pp {hoeher_inv[b]}; {um[b]} 3 %."]}
    assert chart_sentences(c) == ["4,1 %, 1,7 Pp höher; über 3 %."]
