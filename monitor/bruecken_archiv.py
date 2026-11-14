"""Frühere Ausgaben der BASt-Brückenstatistik aus dem Internet Archive holen (für die Prognose je Brücke).

Die BASt bietet nur den jüngsten Stand an. Das Internet Archive hat frühere Fassungen der CSV gespeichert. Das Skript
sucht alle gespeicherten Fassungen (verschiedener Inhalt), lädt sie und behält je Teilbauwerk nur Bauwerksnummer,
Teilbauwerk, Baujahr, Fläche, Baustoff und Zustandsnote, mit dem Abrufdatum des Archivs als Stand.

    python -m monitor.bruecken_archiv C:\\Daten\\BASt

Ergebnis: brueckenstatistik_staende.csv.gz im Ordner (klein genug zum Hochladen). Nur Standardbibliothek; läuft auf
dem eigenen Rechner, weil die Cloud-Umgebung das Archiv nicht erreicht.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

CDX = ("https://web.archive.org/cdx/search/cdx?url=bast.de/DE/Publikationen/Statistik/Bruecken/*"
       "&output=json&fl=timestamp,original,statuscode,digest&collapse=digest&filter=statuscode:200")
SPALTEN = ["bwnr", "tbwnr", "baujahr", "flaeche", "baustoffklasse", "zustandsnote"]


def _hol(url: str, versuche: int = 4) -> bytes:
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor (Brueckenstatistik)"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:  # Archiv antwortet oft langsam
            print(f"  Versuch {i + 1}: {e}", flush=True)
            time.sleep(10 * (i + 1))
    raise RuntimeError(f"nicht erreichbar: {url}")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        sys.exit(1)
    ordner = Path(argv[0])
    ordner.mkdir(parents=True, exist_ok=True)
    print("Suche gespeicherte Fassungen im Internet Archive ...", flush=True)
    treffer = json.loads(_hol(CDX).decode("utf-8"))[1:]
    csvs = [(t, u) for t, u, *_ in treffer if ".csv" in u.lower()]
    print(f"{len(csvs)} verschiedene CSV-Fassungen gefunden", flush=True)
    ziel = ordner / "brueckenstatistik_staende.csv.gz"
    gesehen = set()
    with gzip.open(ziel, "wt", encoding="utf-8", newline="") as aus:
        w = csv.writer(aus)
        w.writerow(["stand"] + SPALTEN)
        for t, u in sorted(csvs):
            print(f"{t[:8]}: laden ...", flush=True)
            roh = _hol(f"https://web.archive.org/web/{t}id_/{u}")
            for kodierung in ("utf-8-sig", "cp1252"):
                try:
                    text = roh.decode(kodierung)
                    break
                except UnicodeDecodeError:
                    continue
            trenner = ";" if text[:2000].count(";") > text[:2000].count(",") else ","
            leser = csv.DictReader(io.StringIO(text), delimiter=trenner)
            felder = {f.strip().strip('"').lower(): f for f in leser.fieldnames or []}
            # Spaltennamen wechseln zwischen den Ausgaben (etwa teil_bw_zustandsnote statt zustandsnote):
            # fehlt ein Name, die erste Spalte nehmen, die ihn enthält
            for s, auch in (("zustandsnote", ("zustandsnote", "zust_note", "zn")), ("baujahr", ("baujahr",)),
                            ("flaeche", ("flaeche", "fläche")), ("baustoffklasse", ("baustoff",))):
                if s not in felder:
                    k = next((f for f in felder if any(a in f for a in auch)), None)
                    if k:
                        felder[s] = felder[k]
                        print(f"  Spalte {s}: {k}")
            if not all(s in felder for s in ("bwnr", "zustandsnote")):
                print(f"  übersprungen, Spalten: {', '.join(felder)}")
                continue
            n = 0
            for r in leser:
                zeile = [t[:8]] + [(r.get(felder[s]) or "").strip() if s in felder else "" for s in SPALTEN]
                schluessel = tuple(zeile)
                if schluessel in gesehen:
                    continue
                gesehen.add(schluessel)
                w.writerow(zeile)
                n += 1
            print(f"  {n} Zeilen", flush=True)
    print(f"Fertig: {ziel} ({ziel.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
