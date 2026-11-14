"""Sanierungsbedarf der Kreise, Baustein Kommunalinvestitionen: Abruf aus der Regionaldatenbank.

Die Schnittstelle der Regionaldatenbank (GENESIS-Webservice) verlangt ein kostenloses Konto. Benutzername und
Passwort werden beim Start abgefragt und nicht gespeichert. Nur Standardbibliothek, damit es unter Windows läuft.

    python -m monitor.kommunal_invest abruf C:\\Daten\\Regionalstatistik

Tabellen:
  71717-Z-05     Rechnungsergebnisse der kommunalen Kernhaushalte: Auszahlungen, darunter Investitionstätigkeit,
                 2018 bis jüngstes Jahr, Gemeinden und Gemeindeverbände
  71517-02-03-4  Kassenstatistik, Bruttoausgaben der Gemeinden je Kreis, 1995 bis 2014 (Vermögenshaushalt)
  71517-04-02-4  Kassenstatistik, Bruttoausgaben der Kreise, 1995 bis 2014 (Vermögenshaushalt)

Große Tabellen rechnet der Server als Auftrag im Hintergrund; das Skript wartet und holt das Ergebnis ab.
Gespeichert wird je Tabelle eine CSV-Datei (flaches Format ffcsv) im Ordner.
"""
from __future__ import annotations

import getpass
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.regionalstatistik.de/genesisws/rest/2020/"
TABELLEN = [
    ("71717-Z-05", "2018", "2030"),
    ("71517-02-03-4", "1995", "2014"),
    ("71517-04-02-4", "1995", "2014"),
]


def _post(pfad: str, kopf: dict, felder: dict, zeit: int = 600) -> bytes:
    req = urllib.request.Request(API + pfad, data=urllib.parse.urlencode(felder).encode(), method="POST",
                                 headers={**kopf, "Content-Type": "application/x-www-form-urlencoded",
                                          "User-Agent": "konjunkturmonitor (Sanierungsbedarf)"})
    try:
        with urllib.request.urlopen(req, timeout=zeit) as r:
            return r.read()
    except urllib.error.HTTPError as e:  # der Server meldet Fehler und Aufträge teils mit Fehlercode und JSON
        inhalt = e.read()
        if inhalt[:1] == b"{":
            return inhalt
        raise


def _meldung(daten: bytes) -> dict | None:
    """Fehler- oder Statusmeldung des Servers (JSON) statt Daten."""
    if daten[:1] != b"{":
        return None
    try:
        return json.loads(daten.decode("utf-8"))
    except ValueError:
        return None


def abruf(ordner: Path) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    nutzer = input("Benutzername Regionaldatenbank: ").strip()
    kopf = {"username": nutzer, "password": getpass.getpass("Passwort (wird nicht angezeigt): ")}
    # Erstanmeldung: Die Regionaldatenbank verlangt ein neues Passwort; die Schnittstelle kann es setzen
    # (profile/password, GENESIS-Webservices, Abschnitt 2.7.1)
    if input("Passwort jetzt ändern? Bei der ersten Anmeldung nötig (j/n): ").strip().lower().startswith("j"):
        while True:
            neu = getpass.getpass("Neues Passwort (10 bis 20 Zeichen, 3 von: klein, GROSS, Ziffer, Sonderzeichen): ")
            if neu == getpass.getpass("Neues Passwort wiederholen: "):
                break
            print("Die beiden Eingaben stimmen nicht überein, bitte noch einmal.")
        antwort = _meldung(_post("profile/password", kopf, {"new": neu, "repeat": neu, "language": "de"})) or {}
        status = antwort.get("Status") or antwort
        print("Passwortänderung:", status.get("Content", status) if isinstance(status, dict) else status)
        if isinstance(status, dict) and str(status.get("Code")) not in ("0", "None"):
            print("Das Passwort wurde nicht geändert. Bitte die Meldung prüfen und neu starten.")
            sys.exit(1)
        kopf["password"] = neu
    try:  # nur zur Auskunft; manche Server beantworten die Prüfung mit 400, der Abruf klappt trotzdem
        probe = _meldung(_post("helloworld/logincheck", kopf, {}))
        print("Anmeldung:", (probe or {}).get("Status", probe))
    except urllib.error.HTTPError as e:
        print(f"Anmeldeprüfung nicht möglich ({e.code}); weiter mit dem Abruf")
    for name, von, bis in TABELLEN:
        ziel = ordner / f"{name}.csv"
        if ziel.exists() and ziel.stat().st_size > 1000:
            print(f"{name}: schon vorhanden, übersprungen")
            continue
        felder = {"name": name, "area": "all", "format": "ffcsv", "compress": "false", "startyear": von,
                  "endyear": bis, "language": "de", "job": "true"}
        print(f"{name}: abrufen ...", flush=True)
        daten = _post("data/tablefile", kopf, felder)
        m = _meldung(daten)
        if m:  # Auftrag im Hintergrund angelegt oder Fehler
            text = str(m.get("Content", ""))
            print(f"  Server: {m.get('Code')} {text}")
            treffer = re.search(re.escape(name) + r"_\d+", text)  # Name des Hintergrundauftrags, etwa 71717-Z-05_123456
            if not treffer and "Auftrag" not in text:
                continue
            ergebnis = treffer.group(0) if treffer else name
            for versuch in range(120):  # bis zu zwei Stunden warten
                time.sleep(60)
                try:
                    daten = _post("data/resultfile", kopf, {"name": ergebnis, "area": "all", "format": "ffcsv",
                                                             "compress": "false", "language": "de"})
                except urllib.error.HTTPError as e:
                    print(f"  noch nicht fertig ({e.code})", flush=True)
                    continue
                m = _meldung(daten)
                if not m:
                    break
                print(f"  noch nicht fertig: {m.get('Content', '')[:80]}", flush=True)
            else:
                print(f"  {name}: kein Ergebnis nach zwei Stunden")
                continue
        ziel.write_bytes(daten)
        print(f"  gespeichert: {ziel} ({len(daten) / 1e6:.1f} MB)")


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[0] != "abruf":
        print(__doc__)
        sys.exit(1)
    abruf(Path(argv[1]))


if __name__ == "__main__":
    main()
