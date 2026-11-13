"""Manifest der Seite und Abgleich im Wächter."""
import json

from monitor.manifest import ANCHOR, NAME, sha256, write
from monitor.waechter import check_manifest


def _site(tmp_path):
    site = tmp_path / "site"
    (site / "en").mkdir(parents=True)
    for name, text in {"index.html": "<p>de</p>", "en/index.html": "<p>en</p>", "data.json": "{}", "dl.csv": "a,b"}.items():
        (site / name).write_text(text, encoding="utf-8")
    write(site, tmp_path)
    return site


def test_manifest_lists_every_file_and_anchors_itself(tmp_path):
    site = _site(tmp_path)
    m = json.loads((site / NAME).read_text(encoding="utf-8"))
    assert set(m["files"]) == {"index.html", "en/index.html", "data.json", "dl.csv"} and m["n"] == 4
    assert m["files"]["index.html"] == sha256(b"<p>de</p>")
    assert (tmp_path / ANCHOR).read_text(encoding="utf-8").split()[0] == sha256((site / NAME).read_bytes())


def test_waechter_detects_changed_page_and_foreign_manifest(tmp_path):
    site = _site(tmp_path)
    get = lambda u: (site / u.split("/km/", 1)[1]).read_bytes()
    assert check_manifest("https://x/km/", tmp_path, get=get) is None
    (site / "index.html").write_text("<p>manipuliert</p>", encoding="utf-8")  # Datei im Netz verändert
    assert "`index.html`" in check_manifest("https://x/km/", tmp_path, get=get)
    write(site, tmp_path / "anderswo")                                        # Seite samt Manifest ersetzt, Repository nicht
    assert "passt nicht" in check_manifest("https://x/km/", tmp_path, get=get)
    assert check_manifest("https://x/km/", tmp_path / "ohne-anker", get=get) is None
