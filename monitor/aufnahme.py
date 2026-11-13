"""Aufnahmefähigkeit der Kreise für Infrastrukturinvestitionen: Vergabedaten aus TED.

Zieht alle deutschen Bauzuschläge (CPV 45) aus der Such-API von TED, wertet den Füllgrad der Felder aus und
schätzt, wie weit Auftragnehmer von ihrem Sitz bis zum Ort der Leistung reisen (Distanzabfall).

Nur Standardbibliothek, damit es auch mit einem nackten Python unter Windows läuft.

    python -m monitor.aufnahme abzug  <ordner> [--ab 20250101]   # Rohdaten als JSONL je Monat
    python -m monitor.aufnahme orte   <ordner>                   # Kreismittelpunkte (GISCO, NUTS 2024)
    python -m monitor.aufnahme auswertung <ordner> [--ziel docs] # Füllgrad, Distanzabfall, Sitzprüfung

Rohdaten bleiben außerhalb des Repos (C:\\Daten\\TED); ins Repo kommen nur die Auswertungen.
Ein erneuter Abzug überspringt Monate, deren Datei schon vollständig ist (Marker .fertig).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

API = "https://api.ted.europa.eu/v3/notices/search"
GISCO = ("https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/"
         "NUTS_LB_2024_4326_LEVL_3.geojson")
TYPEN = "(can-standard can-social can-desg can-modif)"
FELDER = [
    "publication-number", "publication-date", "notice-type", "buyer-name", "classification-cpv",
    "winner-name", "winner-post-code", "winner-city", "winner-country", "winner-country-sub",
    "place-of-performance-subdiv-lot", "place-of-performance-subdiv-proc",
    "received-submissions-type-code", "received-submissions-type-val", "tender-value",
]
SEITE = 250

# Gewerke nach CPV-Abteilung 45, vierstellig; Rest unter „sonstiges“
GEWERKE = {
    "4511": "Abbruch, Erdarbeiten", "4512": "Abbruch, Erdarbeiten",
    "4521": "Hochbau", "4522": "Ingenieurbau", "4523": "Straßen, Schiene, Leitungen",
    "4524": "Wasserbau", "4525": "Anlagenbau", "4526": "Dach, Spezialbau",
    "4531": "Elektro", "4532": "Dämmung", "4533": "Sanitär, Heizung", "4534": "Zäune, Sonstige Installation",
    "4535": "Gebäudetechnik", "4541": "Ausbau", "4542": "Ausbau", "4543": "Ausbau", "4544": "Ausbau",
    "4545": "Ausbau",
}
GROESSEN = [(0, 1e6, "unter 1 Mio."), (1e6, 5e6, "1-5 Mio."), (5e6, 25e6, "5-25 Mio."),
            (25e6, math.inf, "über 25 Mio.")]


# ---------------------------------------------------------------- Abzug

def _post(body: dict, versuche: int = 6) -> dict:
    daten = json.dumps(body).encode()
    for i in range(versuche):
        req = urllib.request.Request(API, data=daten, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "konjunkturmonitor (Aufnahmefähigkeit der Kreise)"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and i < versuche - 1:
                time.sleep(5 * (i + 1))
                continue
            raise RuntimeError(f"TED antwortet {e.code}: {text}") from e
        except (urllib.error.URLError, TimeoutError):
            if i < versuche - 1:
                time.sleep(5 * (i + 1))
                continue
            raise
    raise RuntimeError("TED nicht erreichbar")


def _abfrage(von: str, bis: str) -> str:
    return (f"notice-type IN {TYPEN} AND buyer-country=DEU AND classification-cpv IN (45000000) "
            f"AND publication-date>={von} AND publication-date<={bis}")


def _monate(ab: str, bis: dt.date):
    j, m = int(ab[:4]), int(ab[4:6])
    while (j, m) <= (bis.year, bis.month):
        anfang = dt.date(j, m, 1)
        ende = (dt.date(j + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
        yield anfang, min(ende, bis)
        j, m = j + (m == 12), m % 12 + 1


def abzug(ordner: Path, ab: str = "20250101") -> None:
    """Je Monat eine JSONL-Datei; Paginierung über iterationNextToken (ohne Obergrenze von 15.000 Treffern)."""
    ordner.mkdir(parents=True, exist_ok=True)
    heute = dt.date.today()
    gesamt = 0
    for anfang, ende in _monate(ab, heute):
        name = f"ted_bau_{anfang:%Y-%m}"
        datei, marke = ordner / f"{name}.jsonl", ordner / f"{name}.fertig"
        if marke.exists() and ende < heute.replace(day=1):
            gesamt += sum(1 for _ in datei.open(encoding="utf-8"))
            continue
        body = {"query": _abfrage(f"{anfang:%Y%m%d}", f"{ende:%Y%m%d}"), "fields": FELDER, "limit": SEITE,
                "scope": "ALL", "paginationMode": "ITERATION", "checkQuerySyntax": False}
        n, erwartet = 0, None
        with datei.open("w", encoding="utf-8") as f:
            while True:
                antwort = _post(body)
                erwartet = antwort.get("totalNoticeCount", erwartet)
                for notiz in antwort.get("notices", []):
                    f.write(json.dumps(notiz, ensure_ascii=False) + "\n")
                    n += 1
                token = antwort.get("iterationNextToken")
                if not token or not antwort.get("notices"):
                    break
                body["iterationNextToken"] = token
                time.sleep(0.3)
        gesamt += n
        print(f"{anfang:%Y-%m}: {n} Bekanntmachungen (TED meldet {erwartet})", flush=True)
        if ende < heute.replace(day=1) and (erwartet is None or n >= erwartet):
            marke.write_text(f"{n}\n", encoding="utf-8")
    print(f"zusammen {gesamt}")


def orte(ordner: Path) -> None:
    """Mittelpunkte (Label-Punkte) der deutschen NUTS-3-Regionen, also der Kreise, aus GISCO."""
    req = urllib.request.Request(GISCO, headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=120) as r:
        geo = json.loads(r.read().decode("utf-8"))
    zeilen = []
    for ft in geo["features"]:
        p = ft["properties"]
        if p.get("CNTR_CODE") == "DE":
            lon, lat = ft["geometry"]["coordinates"]
            zeilen.append((p["NUTS_ID"], p.get("NAME_LATN", ""), round(lat, 5), round(lon, 5)))
    with (ordner / "nuts3_de.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nuts3", "name", "lat", "lon"])
        w.writerows(sorted(zeilen))
    print(f"{len(zeilen)} Kreise")


# ---------------------------------------------------------------- Auswertung

def _liste(wert) -> list:
    """TED liefert Felder als Wert, Liste oder Sprach-Wörterbuch; hier immer eine flache Liste von Texten."""
    if wert is None:
        return []
    if isinstance(wert, dict):
        if "amount" in wert:
            return [wert]
        aus = []
        for v in wert.values():
            aus.extend(_liste(v))
        return aus
    if isinstance(wert, list):
        aus = []
        for v in wert:
            aus.extend(_liste(v))
        return aus
    return [str(wert)]


# TED meldet teils noch NUTS 2021; in Thüringen wurden die Codes 2024 neu vergeben (Eisenach im Wartburgkreis)
NUTS21_24 = {"DEG04": "DEG0S", "DEG0B": "DEG0Q", "DEG0F": "DEG0T", "DEG0H": "DEG0V", "DEG0I": "DEG0U",
             "DEG0N": "DEG0R", "DEG0P": "DEG0R"}


def _de3(codes: list) -> list[str]:
    return sorted({NUTS21_24.get(c, c) for c in codes if isinstance(c, str) and c.startswith("DE") and len(c) == 5})


def _betrag(wert) -> float | None:
    summe = 0.0
    for v in _liste(wert):
        try:
            summe += float(v["amount"] if isinstance(v, dict) else v)
        except (TypeError, ValueError, KeyError):
            continue
    return summe or None


def _gewerk(cpvs: list) -> str:
    for c in cpvs:
        if isinstance(c, str) and c.startswith("45"):
            return GEWERKE.get(c[:4], "sonstiges")
    return "sonstiges"


def _groesse(betrag: float | None) -> str:
    if betrag is None:
        return "ohne Wert"
    return next(n for lo, hi, n in GROESSEN if lo <= betrag < hi)


def _km(a: tuple, b: tuple) -> float:
    (la1, lo1), (la2, lo2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2
         + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def lies(ordner: Path):
    gesehen = set()
    for datei in sorted(ordner.glob("ted_bau_*.jsonl")):
        for zeile in datei.open(encoding="utf-8"):
            n = json.loads(zeile)
            nr = n.get("publication-number")
            if nr in gesehen:
                continue
            gesehen.add(nr)
            yield n


def datensatz(ordner: Path) -> list[dict]:
    """Eine Zeile je Bekanntmachung mit den Merkmalen, die die Auswertung braucht."""
    aus = []
    for n in lies(ordner):
        sitz = _de3(_liste(n.get("winner-country-sub")))
        ort = _de3(_liste(n.get("place-of-performance-subdiv-lot"))) or \
            _de3(_liste(n.get("place-of-performance-subdiv-proc")))
        namen = sorted(set(_liste(n.get("winner-name"))))
        laender = set(_liste(n.get("winner-country")))
        kaeufer = " ".join(_liste(n.get("buyer-name")))
        angebote = [v for v in _liste(n.get("received-submissions-type-val")) if v.replace(".", "").isdigit()]
        aus.append({
            "nr": n.get("publication-number"),
            "jahr": (_liste(n.get("publication-date")) or ["?"])[0][:4],
            "auftraggeber": "DB InfraGO" if "DB InfraGO" in kaeufer else
                            ("andere DB" if "DB " in kaeufer or "Deutsche Bahn" in kaeufer else "übrige"),
            "gewerk": _gewerk(_liste(n.get("classification-cpv"))),
            "groesse": _groesse(_betrag(n.get("tender-value"))),
            "namen": namen, "plz": sorted(set(_liste(n.get("winner-post-code")))),
            "ausland": bool(laender - {"DEU"}) if laender else False,
            "sitz": sitz, "ort": ort, "angebote": len(angebote) > 0,
        })
    return aus


def _anteil(z: int, n: int) -> str:
    return f"{100 * z / n:.0f} %" if n else "-"


def auswertung(ordner: Path, ziel: Path) -> None:
    zeilen = datensatz(ordner)
    lage = {}
    for p in csv.DictReader((ordner / "nuts3_de.csv").open(encoding="utf-8")):
        lage[p["nuts3"]] = (float(p["lat"]), float(p["lon"]))

    # Füllgrad
    fuell = defaultdict(Counter)
    for z in zeilen:
        for schluessel in (("alle",), ("jahr", z["jahr"]), ("auftraggeber", z["auftraggeber"]),
                           ("gewerk", z["gewerk"])):
            c = fuell[schluessel]
            c["n"] += 1
            c["name"] += bool(z["namen"])
            c["sitz"] += bool(z["sitz"])
            c["ort"] += bool(z["ort"])
            c["paar"] += bool(z["sitz"] and z["ort"])
            c["eindeutig"] += len(z["sitz"]) == 1 and len(z["ort"]) == 1
            c["angebote"] += z["angebote"]

    # Distanzen: nur Bekanntmachungen mit genau einem Sitz-Kreis und einem Leistungskreis
    paare = []
    for z in zeilen:
        if len(z["sitz"]) == 1 and len(z["ort"]) == 1 and z["sitz"][0] in lage and z["ort"][0] in lage:
            km = _km(lage[z["sitz"][0]], lage[z["ort"][0]])
            paare.append({**z, "km": km, "gleich": z["sitz"][0] == z["ort"][0]})

    def abfall(gruppe: list[dict]) -> dict:
        n = len(gruppe)
        aussen = [p["km"] for p in gruppe if not p["gleich"]]
        return {
            "n": n,
            "gleich": _anteil(sum(p["gleich"] for p in gruppe), n),
            "bis50": _anteil(sum(p["km"] <= 50 for p in gruppe), n),
            "bis100": _anteil(sum(p["km"] <= 100 for p in gruppe), n),
            "bis200": _anteil(sum(p["km"] <= 200 for p in gruppe), n),
            "median": f"{statistics.median([p['km'] for p in gruppe]):.0f}" if n else "-",
            # Exponentialverteilung jenseits des eigenen Kreises: Schätzer der mittleren Reichweite ist der
            # Mittelwert; Halbwertsdistanz = Mittelwert · ln 2
            "halbwert": f"{statistics.mean(aussen) * math.log(2):.0f}" if len(aussen) >= 20 else "-",
        }

    tab_gewerk = {g: abfall([p for p in paare if p["gewerk"] == g]) for g in sorted({p["gewerk"] for p in paare})}
    tab_groesse = {g: abfall([p for p in paare if p["groesse"] == g])
                   for g in [n for *_, n in GROESSEN] + ["ohne Wert"]}
    tab_kaeufer = {g: abfall([p for p in paare if p["auftraggeber"] == g])
                   for g in ("DB InfraGO", "andere DB", "übrige")}

    # Sitz oder Niederlassung: wie viele verschiedene Postleitzahlen meldet derselbe Auftragnehmer?
    plz_je = defaultdict(set)
    zahl_je = Counter()
    for z in zeilen:
        if len(z["namen"]) == 1:
            plz_je[z["namen"][0]].update(z["plz"])
            zahl_je[z["namen"][0]] += 1
    top = zahl_je.most_common(30)

    # Kantenliste für spätere Schätzungen (Schwerkraftmodell), aggregiert, ohne Firmennamen
    kanten = Counter((p["sitz"][0], p["ort"][0], p["gewerk"]) for p in paare)
    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "aufnahme_kanten.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sitz_nuts3", "ort_nuts3", "gewerk", "zuschlaege"])
        for (a, b, g), k in sorted(kanten.items()):
            w.writerow([a, b, g, k])

    def tabelle(kopf: str, daten: dict) -> list[str]:
        t = [f"| {kopf} | Zuschläge | gleicher Kreis | bis 50 km | bis 100 km | bis 200 km | Median km | "
             "Halbwertsdistanz km |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for k, v in daten.items():
            t.append(f"| {k} | {v['n']} | {v['gleich']} | {v['bis50']} | {v['bis100']} | {v['bis200']} | "
                     f"{v['median']} | {v['halbwert']} |")
        return t

    text = [f"## TED-Auswertung vom {dt.date.today():%d.%m.%Y}", "",
            f"Bekanntmachungen: {len(zeilen)}; davon mit genau einem Sitz- und einem Leistungskreis: {len(paare)}; "
            f"Auftragnehmer im Ausland: {sum(z['ausland'] for z in zeilen)}.", "",
            "### Füllgrad", "",
            "| Gruppe | Bekanntmachungen | Auftragnehmer genannt | Sitz-Kreis | Leistungskreis | beides | "
            "beides eindeutig | Zahl der Angebote |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, c in sorted(fuell.items(), key=lambda kv: (kv[0][0] != "alle", kv[0])):
        text.append(f"| {' '.join(k)} | {c['n']} | {_anteil(c['name'], c['n'])} | {_anteil(c['sitz'], c['n'])} | "
                    f"{_anteil(c['ort'], c['n'])} | {_anteil(c['paar'], c['n'])} | "
                    f"{_anteil(c['eindeutig'], c['n'])} | {_anteil(c['angebote'], c['n'])} |")
    text += ["", "### Distanzabfall nach Gewerk", "", *tabelle("Gewerk", tab_gewerk),
             "", "### Distanzabfall nach Auftragsgröße", "", *tabelle("Auftragswert", tab_groesse),
             "", "### Distanzabfall nach Auftraggeber", "", *tabelle("Auftraggeber", tab_kaeufer),
             "", "### Sitz oder Niederlassung: die 30 häufigsten Auftragnehmer", "",
             "Meldet ein Auftragnehmer viele verschiedene Postleitzahlen, gibt er offenbar die ausführende "
             "Niederlassung an; eine einzige Postleitzahl spricht für den eingetragenen Sitz.", "",
             "| Auftragnehmer | Zuschläge | verschiedene Postleitzahlen |", "|---|---:|---:|"]
    text += [f"| {name} | {k} | {len(plz_je[name])} |" for name, k in top]
    text += ["", "Distanz: Luftlinie zwischen den Mittelpunkten der Kreise (GISCO, NUTS 2024). Halbwertsdistanz: "
             "Entfernung, bis zu der die Hälfte der Aufträge außerhalb des eigenen Kreises vergeben wird, unter der "
             "Annahme eines exponentiellen Abfalls. Kantenliste je Kreispaar und Gewerk: "
             "data/static/aufnahme_kanten.csv."]
    (ziel / "aufnahme_ted.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(f"{len(zeilen)} Bekanntmachungen, {len(paare)} Paare; geschrieben nach {ziel}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.aufnahme")
    ap.add_argument("schritt", choices=["abzug", "orte", "auswertung", "alles"])
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--ab", default="20250101")
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    ziel = a.ziel or a.ordner
    if a.schritt in ("abzug", "alles"):
        abzug(a.ordner, a.ab)
    if a.schritt in ("orte", "alles"):
        orte(a.ordner)
    if a.schritt in ("auswertung", "alles"):
        auswertung(a.ordner, ziel)


if __name__ == "__main__":
    main(sys.argv[1:])
