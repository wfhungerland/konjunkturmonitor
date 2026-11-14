from monitor.build import chart_sentences


def test_tpl_ref_line_and_x100():
    x = ["2025-10-01", "2026-10-01"]
    c = {"type": "line", "freq": "M", "unit": "Index", "decimals": 0, "refs": [{"y": 84.12, "label": "Mittel"}],
         "series": [{"id": "e", "x": x, "y": [452.7, 373.6]}], "tpl": ["{n[e]} Punkte, das {x100[e]}-Fache; Mittel {ref}; {dabs[e]} {hoeher[e]}."]}
    assert chart_sentences(c) == ["374 Punkte, das 3,7-Fache; Mittel 84,1; 79 niedriger."]
