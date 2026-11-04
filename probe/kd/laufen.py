"""Startet beide Abrufe nacheinander und hängt eine Zeile an LAUFPROTOKOLL.txt an.

Diese Datei ruft die Windows-Aufgabenplanung täglich auf. Ein Fehler in einem Abruf hält den anderen nicht auf.
Protokollzeile: Zeitpunkt | Pegel: neue Zeilen | Wetter: neue Zeilen | Fehler
"""
import traceback
from datetime import datetime
from pathlib import Path

import pegel_tageswerte
import wetter_monat

ORDNER = Path(__file__).resolve().parent


def sicher(name, f):
    try:
        e = f()
        return e, [f"{name}: {x}" for x in e.get("fehler", [])]
    except Exception as ex:
        return None, [f"{name}: {ex.__class__.__name__}: {ex}"]


def main():
    p, fp = sicher("Pegel", pegel_tageswerte.lauf)
    w, fw = sicher("Wetter", wetter_monat.lauf)
    fehler = fp + fw
    teile = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             f"Pegel: {p['neu']} neue Zeilen ({p['gesamt']} insgesamt)" if p else "Pegel: abgebrochen",
             f"Wetter: {w['neu']} neue Zeilen ({w['gesamt']} insgesamt)" if w else "Wetter: abgebrochen",
             "Fehler: " + ("; ".join(fehler) if fehler else "keine")]
    zeile = " | ".join(teile)
    with open(ORDNER / "LAUFPROTOKOLL.txt", "a", encoding="utf-8") as f:
        f.write(zeile + "\n")
    print(zeile)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(ORDNER / "LAUFPROTOKOLL.txt", "a", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " | Abbruch: " + traceback.format_exc().replace("\n", " ") + "\n")
        raise
