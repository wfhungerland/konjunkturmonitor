from monitor.build import chart_sentences

M = [f"2026-{m:02d}-01" for m in range(1, 10)]


def test_combine_each_month_and_above_mark():
    s = lambda lab, ys: {"id": lab, "label": lab, "x": M[:len(ys)], "y": ys}
    c = {"type": "line", "freq": "M", "unit": "Index", "decimals": 1, "series": [s("Italien", [100.0] * 9), s("Spanien", [105.0] * 9), s("Euroraum", [97.0] * 8)],
         "combine": {"common": True, "each_month": True, "lead": "lag der Indikator", "mid": " bei", "pre": "in ", "sign": False,
                     "above": 100, "agg": ["Euroraum"], "above_word": "dem Durchschnitt"}}
    assert chart_sentences(c) == ["Im September 2026 lag der Indikator in Italien bei 100,0 und in Spanien bei 105,0; in Euroraum im August 2026 bei 97,0; über dem Durchschnitt lag nur Spanien."]
