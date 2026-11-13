"""Aufnahmefähigkeit der Kreise: Schwerkraftmodell der Bauzuschläge zwischen Kreisen.

Zahl der Zuschläge von Firmen mit Sitz im Kreis i für Leistungen im Kreis j:

    E[F_ij] = exp(a_i + b_j + δ·[i = j] − β·t_ij)

a_i misst das Angebot am Sitz, b_j die Nachfrage am Leistungsort, δ den Vorteil des eigenen Kreises und β den
Abfall mit der Fahrzeit t_ij (Minuten, OSRM) bzw. der Luftlinie (km). Geschätzt als Poisson-Pseudo-Maximum-
Likelihood: Bei gegebenem β treffen die festen Effekte Zeilen-, Spalten- und Diagonalsummen (iterative
Anpassung); β löst die Bedingung, dass beobachtete und geschätzte Summe von F·t übereinstimmen (Bisektion).
Halbwertszeit = ln 2 / β: nach dieser Fahrzeit halbiert sich der Strom bei gegebenem Angebot und Nachfrage.

    python -m monitor.aufnahme_schwerkraft <ted-ordner> [--ziel docs]

Braucht im Ordner die TED-Rohdaten, nuts3_de.csv und fahrzeiten_nuts3.csv (siehe monitor.aufnahme).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import sys
from pathlib import Path

import numpy as np

from monitor import aufnahme as au


def schaetzen(F: np.ndarray, T: np.ndarray, tol: float = 1e-7) -> dict:
    """PPML mit Herkunfts-, Ziel- und Diagonaleffekt; gibt β, Halbwert und Diagonalfaktor zurück."""
    n = F.shape[0]
    zeilen, spalten, diag = F.sum(1), F.sum(0), np.trace(F)
    eye = np.eye(n, dtype=bool)
    ziel_ft = (F * T).sum()

    def anpassen(beta: float):
        K = np.exp(-beta * T)
        r, c, d = np.ones(n), np.ones(n), 1.0
        for _ in range(5000):
            Kd = np.where(eye, K * d, K)
            r = np.divide(zeilen, Kd @ c, out=np.zeros(n), where=zeilen > 0)
            c = np.divide(spalten, Kd.T @ r, out=np.zeros(n), where=spalten > 0)
            pred_diag = (r * np.diag(K) * c).sum() * d
            d_neu = d * diag / pred_diag if pred_diag > 0 else d
            fertig = abs(d_neu / d - 1) < tol
            d = d_neu
            if fertig:
                Kd = np.where(eye, K * d, K)
                fehler = np.abs((Kd @ c) * r - zeilen).max()
                if fehler < 1e-6 * max(1.0, zeilen.max()):
                    break
        Fh = r[:, None] * Kd * c[None, :]
        return Fh, d

    def g(beta: float) -> float:
        Fh, _ = anpassen(beta)
        return (Fh * T).sum() - ziel_ft

    lo, hi = 0.0, 0.05
    while g(hi) > 0:
        hi *= 2
    for _ in range(50):
        mitte = (lo + hi) / 2
        if g(mitte) > 0:
            lo = mitte
        else:
            hi = mitte
        if hi - lo < 1e-7:
            break
    beta = (lo + hi) / 2
    Fh, d = anpassen(beta)
    # Pseudo-R²: Anteil der erklärten Poisson-Devianz gegenüber einem Modell nur mit festen Effekten (β = 0)
    def devianz(Fh_):
        mask = F > 0
        return 2 * ((F[mask] * np.log(F[mask] / Fh_[mask])).sum() - (F - Fh_).sum())
    Fh0, _ = anpassen(0.0)
    return {"beta": beta, "halbwert": math.log(2) / beta if beta > 0 else math.inf, "diagonal": d,
            "zuschlaege": int(F.sum()), "devianz_erklaert": 1 - devianz(Fh) / devianz(Fh0)}


def _matrizen(ordner: Path):
    kreise = [r["nuts3"] for r in csv.DictReader((ordner / "nuts3_de.csv").open(encoding="utf-8"))]
    lage = {r["nuts3"]: (float(r["lat"]), float(r["lon"]))
            for r in csv.DictReader((ordner / "nuts3_de.csv").open(encoding="utf-8"))}
    idx = {k: i for i, k in enumerate(kreise)}
    n = len(kreise)
    T = np.zeros((n, n))
    for r in csv.DictReader((ordner / "fahrzeiten_nuts3.csv").open(encoding="utf-8")):
        if r["von_nuts3"] in idx and r["nach_nuts3"] in idx and r["minuten"]:
            T[idx[r["von_nuts3"]], idx[r["nach_nuts3"]]] = float(r["minuten"])
    np.fill_diagonal(T, 0.0)
    D = np.array([[au._km(lage[a], lage[b]) for b in kreise] for a in kreise])
    return kreise, idx, T, D


def auswerten(ordner: Path, ziel: Path) -> None:
    kreise, idx, T, D = _matrizen(ordner)
    zeilen = au.datensatz(ordner)
    typ = au.firmentypen(zeilen)
    paare = [z for z in zeilen if len(z["sitz"]) == 1 and len(z["ort"]) == 1
             and z["sitz"][0] in idx and z["ort"][0] in idx]
    for z in paare:
        z["typ"] = typ.get(z["firma"], "mehrere oder keine Auftragnehmer")

    def matrix(gruppe):
        F = np.zeros((len(kreise), len(kreise)))
        for z in gruppe:
            F[idx[z["sitz"][0]], idx[z["ort"][0]]] += 1
        return F

    gruppen = [("alle", paare), ("regional", [z for z in paare if z["typ"] == "regional"]),
               ("überregional, meldet Niederlassung", [z for z in paare if z["typ"] == "überregional, meldet Niederlassung"]),
               ("überregional, meldet Zentrale", [z for z in paare if z["typ"] == "überregional, meldet Zentrale"])]
    for g in sorted({z["gewerk"] for z in paare}):
        gruppe = [z for z in paare if z["typ"] == "regional" and z["gewerk"] == g]
        if len(gruppe) >= 500:
            gruppen.append((f"regional: {g}", gruppe))

    erg = []
    for name, gruppe in gruppen:
        F = matrix(gruppe)
        m, k = schaetzen(F, T), schaetzen(F, D)
        erg.append({"gruppe": name, **{f"{x}_min": v for x, v in m.items()},
                    "beta_km": k["beta"], "halbwert_km": k["halbwert"]})
        print(f"{name}: Halbwertszeit {m['halbwert']:.0f} min, {k['halbwert']:.0f} km", flush=True)

    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "aufnahme_schwerkraft.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["gruppe", "zuschlaege", "beta_je_minute", "halbwertszeit_min", "faktor_eigener_kreis",
                    "devianz_erklaert", "beta_je_km", "halbwertsdistanz_km"])
        for e in erg:
            w.writerow([e["gruppe"], e["zuschlaege_min"], f"{e['beta_min']:.5f}", f"{e['halbwert_min']:.1f}",
                        f"{e['diagonal_min']:.2f}", f"{e['devianz_erklaert_min']:.3f}", f"{e['beta_km']:.5f}",
                        f"{e['halbwert_km']:.1f}"])
    text = [f"## Schwerkraftmodell der Bauzuschläge vom {dt.date.today():%d.%m.%Y}", "",
            "Poisson-Schätzung mit festen Effekten für Sitz- und Leistungskreis und einem Aufschlag für den eigenen "
            "Kreis. Halbwertszeit: Fahrzeit, nach der sich der Strom der Zuschläge zwischen zwei Kreisen bei "
            "gegebenem Angebot und gegebener Nachfrage halbiert. Faktor eigener Kreis: wie viel mehr Zuschläge im "
            "eigenen Kreis bleiben, als die Fahrzeit null allein erwarten ließe. Erklärte Devianz: Anteil, den die "
            "Entfernung über die festen Effekte hinaus erklärt.", "",
            "| Gruppe | Zuschläge | Halbwertszeit min | Faktor eigener Kreis | erklärte Devianz | "
            "Halbwertsdistanz km (Luftlinie) |", "|---|---:|---:|---:|---:|---:|"]
    for e in erg:
        text.append(f"| {e['gruppe']} | {e['zuschlaege_min']} | {e['halbwert_min']:.0f} | {e['diagonal_min']:.1f} | "
                    f"{100 * e['devianz_erklaert_min']:.0f} % | {e['halbwert_km']:.0f} |")
    text += ["", "Gewerke nur mit mindestens 500 Zuschlägen regionaler Firmen. Parameter: "
             "data/static/aufnahme_schwerkraft.csv."]
    (ziel / "aufnahme_schwerkraft.md").write_text("\n".join(text) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.aufnahme_schwerkraft")
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    auswerten(a.ordner, a.ziel or a.ordner)


if __name__ == "__main__":
    main(sys.argv[1:])
