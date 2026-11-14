from monitor.build import chart_sentences


def test_tpl_credit_standards_verbs_and_signed_change():
    x = ["2025-10-01", "2026-10-01"]
    s = lambda i, a, b: {"id": i, "x": x, "y": [a, b]}
    c = {"type": "line", "freq": "Q", "unit": "Saldo in %", "decimals": 0, "series": [s("a", 9.7, 6.5), s("b", 3.6, -3.7), s("c", 1.0, 0.2)],
         "tpl": ["{std_v[a]} a{std_k[a]}, {std_v[b]} b, {std_v[c]} c{std_k[c]}; {up_s[b]}; {dsg[a]}."]}
    assert chart_sentences(c) == ["verschärften a, lockerten b, veränderten c kaum; sank; -3."]
