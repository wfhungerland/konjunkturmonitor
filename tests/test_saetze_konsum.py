from monitor.build import chart_sentences
from monitor.ausschreiben import spell

M = [f"{y}-{m:02d}-01" for y in (2025, 2026) for m in range(1, 13)][:21]  # bis September 2026


def test_tpl_three_month_comparisons():
    y = [100.0] * 15 + [110.0] * 3 + [99.0] * 3
    c = {"type": "line", "freq": "M", "unit": "Index 2021=100", "decimals": 1, "series": [{"id": "r", "x": M, "y": y}],
         "tpl": ["{when}: {chg[r]}; bis {per} {m3[r]}, {m3y_abs[r]} % {m3y_mehr[r]}."]}
    assert chart_sentences(c) == ["Im September 2026: -1,0 %; bis September 2026 -10,0 %, 1,0 % weniger."]


def test_negative_saldo_in_dative():
    assert spell("lag der Saldo bei \u221214,5 Pp, 3,7 Pp niedriger") == "lag der Saldo bei \u221214,5\xa0Prozentpunkten, 3,7\xa0Prozentpunkte niedriger"
