import json

from monitor import aufnahme


def _notiz(nr, sitz, ort, cpv="45234000", wert=2e6, name="Bau GmbH", plz="10115", kaeufer="Stadt X"):
    return {"publication-number": nr, "publication-date": ["2025-03-04+01:00"], "notice-type": "can-standard",
            "buyer-name": {"deu": [kaeufer]}, "classification-cpv": [cpv], "winner-name": {"deu": [name]},
            "winner-post-code": [plz], "winner-country": ["DEU"], "winner-country-sub": [sitz],
            "place-of-performance-subdiv-proc": [ort], "received-submissions-type-val": ["3"],
            "tender-value": [str(wert)]}  # so liefert TED den Wert (geprüft 13.11.2026)


def test_auswertung(tmp_path):
    with (tmp_path / "ted_bau_2025-03.jsonl").open("w") as f:
        for i, (s, o) in enumerate([("DE300", "DE300"), ("DE300", "DE405"), ("DE405", "DE300"),
                                    ("DE300", "DE212"), ("DE300", "DE300")]):
            f.write(json.dumps(_notiz(str(i), s, o, kaeufer="DB InfraGO AG" if i == 1 else "Stadt X")) + "\n")
        f.write(json.dumps(_notiz("0", "DE300", "DE300")) + "\n")  # Dublette
    (tmp_path / "nuts3_de.csv").write_text(
        "nuts3,name,lat,lon\nDE300,Berlin,52.52,13.40\nDE405,Potsdam,52.40,13.06\nDE212,München,48.14,11.58\n")
    zeilen = aufnahme.datensatz(tmp_path)
    assert len(zeilen) == 5
    assert zeilen[0]["jahr"] == "2025" and zeilen[0]["gewerk"] == "Straßen, Schiene, Leitungen"
    assert zeilen[1]["auftraggeber"] == "DB InfraGO" and zeilen[0]["groesse"] == "1-5 Mio."
    aufnahme.auswertung(tmp_path, tmp_path)
    text = (tmp_path / "aufnahme_ted.md").read_text()
    assert "Bekanntmachungen: 5" in text and "| Bau GmbH | 5 | 1 |" in text
    assert (tmp_path / "aufnahme_kanten.csv").read_text().count("\n") == 5


def test_monate():
    import datetime as dt
    m = list(aufnahme._monate("20251101", dt.date(2026, 1, 15)))
    assert [a.month for a, _ in m] == [11, 12, 1] and m[-1][1] == dt.date(2026, 1, 15)


def test_nuts2021_auf_2024():
    assert aufnahme._de3(["DEG0N", "DEG0P", "DE300", "DEG", "AT130"]) == ["DE300", "DEG0R"]


def test_betrag_ohne_platzhalter():
    assert aufnahme._betrag(["-1"]) is None
    assert aufnahme._betrag(["100.5", "-1", "200"]) == 300.5
