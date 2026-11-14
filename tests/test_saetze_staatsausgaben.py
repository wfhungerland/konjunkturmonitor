from monitor.build import chart_sentences


def test_treemap_sum_biggest_block_and_leaf():
    A = {"price_base": 2024, "parent": {"A": "", "A1": "A", "A2": "A", "B1": "B", "B": ""}, "labels": {"A": "Soziales", "A1": "Alter", "A2": "Krankheit", "B": "Rest"},
         "steps": [{"key": "2000", "label": "2000", "values": {"A1": 50.0, "B1": 50.0}}, {"key": "2024", "label": "2024", "values": {"A1": 60.0, "A2": 20.0, "B1": 20.0}}]}
    out = chart_sentences({"type": "treemap", "attach": A})
    assert out == ["Im Jahr 2024 gab der Staat 100 Mrd. € aus, davon 80 Mrd. € (80 %) für „Soziales“, am meisten davon für „Alter“ (60 Mrd. €).",
                   "Im Jahr 2000 waren es 100 Mrd. € (in Preisen von 2024)."]


def test_tpl_maxd_names_largest_change():
    x = ["2023-01-01", "2024-01-01"]
    s = lambda i, lab, a, b: {"id": i, "label": lab, "unit": "% der Staatsausgaben", "x": x, "y": [a, b]}
    c = {"type": "line", "freq": "A", "unit": "% der Staatsausgaben", "decimals": 1, "series": [s("a", "Soziales", 40.6, 41.3), s("b", "Verkehr", 12.1, 11.0)],
         "tpl": ["{maxd}."]}
    assert chart_sentences(c) == ["„Verkehr“ (-1,1 Pp)."]
