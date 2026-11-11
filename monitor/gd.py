"""Reihen der Abbildungen zur Gemeinschaftsdiagnose aus data/static/gd_prognosen.csv.

Der Datensatz ist eine abgeleitete Kopie; kanonisch liegt er auf dem Server des Herausgebers.
Aufruf nach jeder neuen Fassung des Datensatzes: python -m monitor.gd
Schreibt data/static/gd_*.csv (date,value) und gibt die Kennzahlen für Sätze und Methodentexte aus.
"""
from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "static" / "gd_prognosen.csv"

# Größe im Datensatz -> Kürzel der Reihen; Saldoquote nur auf das BIP bezogen
GROESSEN = {"BIP real": "bip", "Verbraucherpreise": "vpi", "Arbeitslose": "alo", "Finanzierungssaldo % BIP": "saldo"}
ZIELJAHRE = 4  # Verlauf für die jüngsten vier Zieljahre


def _num(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path: Path = SRC) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def herbst(rows: list[dict], groesse: str) -> dict[int, dict]:
    """Herbstprognose der Mehrheit für das Folgejahr, je Prognosejahr."""
    out = {}
    for r in rows:
        if r["groesse"] != groesse or r["runde"] != "H" or r["horizont"] != "1" or r["variante"] != "Mehrheit":
            continue
        if groesse == "Finanzierungssaldo % BIP" and "BSP" in r["einheit"]:
            continue
        if _num(r["wert"]) is None:
            continue
        out[int(r["prognosejahr"])] = r
    return out


def _write(name: str, pts: list[tuple[str, float]]) -> None:
    with open(ROOT / "data" / "static" / f"{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for d, v in sorted(pts):
            w.writerow([d, round(v, 4)])


def _datum(r: dict) -> str:
    return r["datum"] or f'{r["gutachten_jahr"]}-{"04" if r["runde"] == "F" else "10"}-15'


def build(rows: list[dict] | None = None) -> dict:
    rows = rows if rows is not None else load()
    stats = {}
    for groesse, k in GROESSEN.items():
        h = herbst(rows, groesse)
        _write(f"gd_{k}_prog", [(f"{y}-01-01", _num(r["wert"])) for y, r in h.items()])
        _write(f"gd_{k}_ist", [(f"{y}-01-01", _num(r["ist_erstmeldung"])) for y, r in h.items() if _num(r["ist_erstmeldung"]) is not None])
        _write(f"gd_{k}_heute", [(f"{y}-01-01", _num(r["ist_heute"])) for y, r in h.items() if _num(r["ist_heute"]) is not None])
        paar = {y: (_num(r["wert"]), _num(r["ist_erstmeldung"])) for y, r in h.items() if _num(r["ist_erstmeldung"]) is not None}
        if paar:
            fe = {y: p - i for y, (p, i) in paar.items()}
            # Vergleich: Prognose "wie die erste Meldung des Vorjahres"
            naiv = [abs(paar[y - 1][1] - i) for y, (_, i) in paar.items() if y - 1 in paar]
            stats[k] = {"n": len(fe), "von": min(fe), "bis": max(fe), "mittel": mean(fe.values()),
                        "mae": mean(abs(v) for v in fe.values()), "naiv_mae": mean(naiv) if naiv else None, "naiv_n": len(naiv)}
            if k == "bip":
                _write("gd_bip_fehler", [(f"{y}-01-01", abs(v)) for y, v in fe.items()])
                dek = {}
                for y, v in fe.items():
                    dek.setdefault(y - y % 10, []).append(abs(v))
                stats["bip_dekaden"] = {d: (len(v), mean(v)) for d, v in sorted(dek.items())}
    # Verlauf der Prognosen für die jüngsten Zieljahre: alle Runden der Mehrheit, BIP real
    bip = [r for r in rows if r["groesse"] == "BIP real" and r["variante"] == "Mehrheit" and _num(r["wert"]) is not None]
    letzte = max(int(r["prognosejahr"]) for r in bip if r["horizont"] == "0")
    ziele = list(range(letzte - ZIELJAHRE + 1, letzte + 1))
    for z in ziele:
        rr = sorted((r for r in bip if int(r["prognosejahr"]) == z), key=_datum)
        _write(f"gd_ziel_{z}", [(_datum(r), _num(r["wert"])) for r in rr])
        # erste Meldung: im Frühjahrsgutachten des Folgejahres gedruckt, gleich in allen Zeilen des Zieljahres
        erst = next((r for r in rr if _num(r["ist_erstmeldung"]) is not None and "spätere" not in r["flag"]), None)
        if erst:
            _write(f"gd_ziel_{z}_ist", [(f"{z + 1}-04-15", _num(erst["ist_erstmeldung"]))])
        stats.setdefault("ziel", {})[z] = [(_datum(r), r["wert"]) for r in rr] + ([("erste Meldung", erst["ist_erstmeldung"])] if erst else [])
    return stats


if __name__ == "__main__":
    import json

    print(json.dumps(build(), indent=1, ensure_ascii=False, default=str))
