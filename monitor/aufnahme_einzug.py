"""Aufnahmefähigkeit der Kreise: Baukapazität je Einzugsgebiet.

Die Bauleute eines Kreises arbeiten nicht nur dort. Das Schwerkraftmodell (monitor.aufnahme_schwerkraft) sagt,
wie stark der Strom der Aufträge mit der Fahrzeit abfällt. Damit wird die Kapazität jedes Sitz-Kreises i auf
die Leistungskreise j verteilt, im Verhältnis zu Erreichbarkeit und Nachfrage (Huff-Verteilung, wie im
Zwei-Stufen-Einzugsgebietsverfahren):

    Anteil_ij = w_ij · N_j / Σ_k w_ik · N_k,   w_ij = exp(−β · t_ij), im eigenen Kreis zusätzlich · δ
    Kapazität_j = Σ_i Bauleute_i · Anteil_ij

N ist die Nachfrage (Bevölkerung), t die Pkw-Fahrzeit, β und δ stammen aus dem Schwerkraftmodell der regionalen
Firmen. Jede Fachkraft zählt so genau einmal. Kennzahl: Kapazität im Einzugsgebiet je 1.000 Einwohner, verglichen
mit der Zahl im eigenen Kreis.

    python -m monitor.aufnahme_einzug [--merkmal svb_bauberufe] [--stichtag 2026-03] [--ziel docs]

Liest data/static/aufnahme_ba_kreise.csv, aufnahme_kreise_de.csv, aufnahme_fahrzeiten.csv und
aufnahme_schwerkraft.csv; schreibt aufnahme_einzug.csv (data/static) und aufnahme_einzug.md (docs).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

import numpy as np

DATEN = Path(__file__).resolve().parent.parent / "data" / "static"


def parameter(gruppe: str = "regional") -> tuple[float, float]:
    for r in csv.DictReader((DATEN / "aufnahme_schwerkraft.csv").open(encoding="utf-8")):
        if r["gruppe"] == gruppe:
            return float(r["beta_je_minute"]), float(r["faktor_eigener_kreis"])
    raise KeyError(gruppe)


def verteilen(S: np.ndarray, N: np.ndarray, T: np.ndarray, beta: float, delta: float) -> np.ndarray:
    """Kapazität je Zielkreis; T in Minuten, np.inf für nicht erreichbar."""
    W = np.exp(-beta * T)
    np.fill_diagonal(W, np.diag(W) * delta)
    WN = W * N[None, :]
    anteil = WN / WN.sum(1, keepdims=True)
    return S @ anteil


def berechnen(merkmal: str, stichtag: str, ziel_md: Path, ziel_csv: Path) -> None:
    endung = "" if merkmal == "svb_bauberufe" else "_" + merkmal.removeprefix("svb_")
    kreise = list(csv.DictReader((DATEN / "aufnahme_kreise_de.csv").open(encoding="utf-8")))
    idx = {k["nuts3"]: i for i, k in enumerate(kreise)}
    n = len(kreise)
    N = np.array([float(k["bevoelkerung"]) for k in kreise])
    werte = {}
    for r in csv.DictReader((DATEN / "aufnahme_ba_kreise.csv").open(encoding="utf-8")):
        if r["merkmal"] == merkmal and r["stichtag"] == stichtag and r["wert"]:
            werte[r["nuts3"]] = float(r["wert"])
    fehlt = [k["nuts3"] for k in kreise if k["nuts3"] not in werte]
    if fehlt and merkmal != "svb_bauberufe":
        # Gesperrte Werte (BA-Geheimhaltung) schätzen: Bauberufe des Kreises mal bundesweites Verhältnis
        bb = {}
        for r in csv.DictReader((DATEN / "aufnahme_ba_kreise.csv").open(encoding="utf-8")):
            if r["merkmal"] == "svb_bauberufe" and r["stichtag"] == stichtag and r["wert"]:
                bb[r["nuts3"]] = float(r["wert"])
        gemeinsam = [k for k in werte if k in bb]
        faktor = sum(werte[k] for k in gemeinsam) / sum(bb[k] for k in gemeinsam)
        for k in fehlt:
            if k in bb:
                werte[k] = bb[k] * faktor
    geschaetzt = [k for k in fehlt if k in werte]
    fehlt = [k for k in fehlt if k not in werte]
    S = np.array([werte.get(k["nuts3"], 0.0) for k in kreise])
    T = np.full((n, n), np.inf)
    np.fill_diagonal(T, 0.0)
    for r in csv.DictReader((DATEN / "aufnahme_fahrzeiten.csv").open(encoding="utf-8")):
        a, b = idx.get(r["von_nuts3"]), idx.get(r["nach_nuts3"])
        if a is not None and b is not None and a != b and r["minuten"]:
            T[a, b] = float(r["minuten"])
    beta, delta = parameter()
    K = verteilen(S, N, T, beta, delta)
    lokal, einzug = 1000 * S / N, 1000 * K / N
    mittel = 1000 * S.sum() / N.sum()

    ziel_csv.mkdir(parents=True, exist_ok=True)
    with (ziel_csv / f"aufnahme_einzug{endung}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ags", "nuts3", "name", "bevoelkerung", f"{merkmal}_kreis", f"{merkmal}_einzug",
                    "je_1000_kreis", "je_1000_einzug", "index_einzug_bund_100", "kreiswert_geschaetzt"])
        for i, k in enumerate(kreise):
            w.writerow([k["ags"], k["nuts3"], k["name"], int(N[i]), int(S[i]), round(K[i]), round(lokal[i], 2),
                        round(einzug[i], 2), round(100 * einzug[i] / mittel, 1), int(k["nuts3"] in geschaetzt)])

    ordnung = np.argsort(einzug)
    korr = np.corrcoef(lokal, einzug)[0, 1]
    streu_l, streu_e = np.std(lokal) / np.mean(lokal), np.std(einzug) / np.mean(einzug)

    def zeile(i):
        return (f"| {kreise[i]['name']} | {lokal[i]:.1f} | {einzug[i]:.1f} | {100 * einzug[i] / mittel:.0f} |")

    kopf = ["| Kreis | je 1.000 Einwohner im Kreis | je 1.000 Einwohner im Einzugsgebiet | Index Bund = 100 |",
            "|---|---:|---:|---:|"]
    text = [f"## Baukapazität je Einzugsgebiet vom {dt.date.today():%d.%m.%Y}", "",
            f"Merkmal: {merkmal} (BA, Arbeitsort, Stichtag {stichtag}). Nachfrage: Bevölkerung (Destatis). "
            f"Abfall aus dem Schwerkraftmodell der regionalen Firmen: β = {beta:.4f} je Minute "
            f"(Halbwertszeit {np.log(2) / beta:.0f} min), Faktor eigener Kreis {delta:.1f}. "
            f"Bund: {mittel:.1f} je 1.000 Einwohner." + (f" Ohne Wert: {', '.join(fehlt)}." if fehlt else "")
            + (f" Von der BA gesperrt und aus den Bauberufen des Kreises geschätzt (bundesweites Verhältnis "
               f"{faktor:.3f}): {', '.join(kreise[idx[k]]['name'] for k in geschaetzt)}." if geschaetzt else ""), "",
            f"Das Einzugsgebiet gleicht aus: Die Streuung über die Kreise (Variationskoeffizient) sinkt von "
            f"{streu_l:.2f} auf {streu_e:.2f}; die Korrelation zwischen beiden Maßen beträgt {korr:.2f}.", "",
            "### Geringste Kapazität im Einzugsgebiet", "", *kopf, *[zeile(i) for i in ordnung[:15]],
            "", "### Höchste Kapazität im Einzugsgebiet", "", *kopf, *[zeile(i) for i in ordnung[::-1][:15]],
            "", f"Alle Kreise: data/static/aufnahme_einzug{endung}.csv. Lesart: Kapazität im Einzugsgebiet ist der Teil der "
            "Bauleute aller Kreise, der nach Fahrzeit und Nachfrage auf diesen Kreis entfällt."]
    ziel_md.mkdir(parents=True, exist_ok=True)
    (ziel_md / f"aufnahme_einzug{endung}.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(f"Streuung {streu_l:.2f} -> {streu_e:.2f}, Korrelation {korr:.2f}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.aufnahme_einzug")
    ap.add_argument("--merkmal", default="svb_bauberufe")
    ap.add_argument("--stichtag", default="2026-03")
    ap.add_argument("--ziel", type=Path, default=Path("docs"))
    ap.add_argument("--daten", type=Path, default=DATEN)
    a = ap.parse_args(argv)
    berechnen(a.merkmal, a.stichtag, a.ziel, a.daten)


if __name__ == "__main__":
    main(sys.argv[1:])
