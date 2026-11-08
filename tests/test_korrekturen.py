"""Korrekturseite: Einträge laden, nach Abbildung filtern, Seite schreiben."""
from pathlib import Path

from monitor.korrekturen import for_chart, load, write_page


def test_korrekturen(tmp_path):
    root = Path(__file__).resolve().parents[1]
    rows = load(root)
    assert rows and rows == sorted(rows, key=lambda r: r["date"], reverse=True)
    assert all(r["art"] in ("Korrektur", "Quelle", "Methode") and r["text"] for r in rows)
    assert for_chart(rows, "potential")
    payload = {"site": {"repo": "https://github.com/x/y"}, "topics": [{"charts": [{"chart": "potential", "no": 3, "title": "Potenzial"}]}]}
    write_page(rows, payload, tmp_path)
    html = (tmp_path / "korrekturen.html").read_text(encoding="utf-8")
    assert "Abb. 3 Potenzial" in html and "/pull/50" in html
