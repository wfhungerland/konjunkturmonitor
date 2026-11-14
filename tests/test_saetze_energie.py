from monitor.build import chart_sentences

M = [f"{y}-{m:02d}-01" for y in (2021, 2022, 2023, 2024, 2025, 2026) for m in range(1, 13)][:69]  # bis September 2026


def test_vs_year_all_below_base():
    s = lambda lab, v: {"id": lab, "label": "20 " + lab, "x": M, "y": [100.0] * 68 + [v]}
    c = {"type": "line", "freq": "M", "unit": "Index 2021=100", "decimals": 1, "series": [s("Chemie", 77.0), s("Glas", 90.0)],
         "vs_year": {"year": 2021, "what": "Branchen", "names": {"Chemie": "in der Chemie"}}}
    assert chart_sentences(c) == ["Im September 2026 lag die Produktion in allen zwei Branchen unter dem Mittel des Jahres 2021, am weitesten in der Chemie (-23,0 %)."]


def test_tpl_own_uses_each_series_last_value():
    d = ["2025-11-11", "2026-10-30", "2026-11-11"]
    c = {"type": "line", "freq": "B", "unit": "US-Dollar je Barrel", "decimals": 1, "tpl_own": True,
         "series": [{"id": "d", "x": d, "y": [64.0, 120.0, 92.0]}, {"id": "m", "freq": "M", "x": ["2026-09-01", "2026-10-01"], "y": [114.0, 124.0]}],
         "tpl": ["{w[d]} ${n[d]}, ${dabs[d]} {dmehr[d]}; im {p[m]} ${n[m]}."]}
    assert chart_sentences(c) == ["Am 11. November 2026 $92,0, $28,0 mehr; im Oktober 2026 $124,0."]
