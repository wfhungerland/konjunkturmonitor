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


def _xlsx(pfad, blaetter):
    """Kleinste xlsx-Datei mit Inline-Texten, nur für Tests."""
    import zipfile
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(pfad, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rns}><sheets>' + "".join(
            f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(blaetter, 1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
                       f'<Relationship Id="rId{i}" Target="worksheets/s{i}.xml"/>' for i in range(1, len(blaetter) + 1))
                   + "</Relationships>")
        for i, zeilen in enumerate(blaetter.values(), 1):
            xml = "".join("<row>" + "".join(
                f'<c r="{sp}{j}" t="inlineStr"><is><t>{w}</t></is></c>' if isinstance(w, str) else f'<c r="{sp}{j}"><v>{w}</v></c>'
                for sp, w in z.items()) + "</row>" for j, z in enumerate(zeilen, 1))
            z.writestr(f"xl/worksheets/s{i}.xml", f"<worksheet {ns}><sheetData>{xml}</sheetData></worksheet>")


def test_regionalreport(tmp_path):
    from monitor import aufnahme_kreise as k
    kopf = {"E": "Mrz. 26", "F": "Dez. 25"}
    _xlsx(tmp_path / "r.xlsx", {
        "Tabelle 2.3": [{"D": "Mrz. 26", "E": "Dez. 25"}, {"A": "F", "B": "Baugewerbe", "C": 9.1, "D": 5004, "E": 4745}],
        "Tabelle 2.4": [kopf, {"A": "Bauberufe", "D": 7.7, "E": 4211, "F": "*"},
                        {"A": 32, "B": "Hoch- und Tiefbauberufe", "D": 2.9, "E": 1596, "F": 1311}],
    })
    werte = sorted(k.regionalreport(tmp_path / "r.xlsx"))
    assert ("2026-03", "svb_wz_f_baugewerbe", 5004.0) in werte
    assert ("2025-12", "svb_bauberufe", None) in werte
    assert ("2025-12", "svb_kldb32_hoch_tiefbau", 1311.0) in werte


def test_schwerkraft_simulation():
    import numpy as np
    from monitor.aufnahme_schwerkraft import schaetzen
    rng = np.random.default_rng(1)
    n = 40
    xy = rng.uniform(0, 300, (n, 2))
    T = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
    mu = np.exp(rng.normal(0, 1, n)[:, None] + rng.normal(0, 1, n)[None] - 0.02 * T) * np.where(np.eye(n, dtype=bool), 3, 1)
    F = rng.poisson(mu * 20000 / mu.sum()).astype(float)
    e = schaetzen(F, T)
    assert abs(e["beta"] - 0.02) < 0.002 and abs(e["diagonal"] - 3) < 0.5
