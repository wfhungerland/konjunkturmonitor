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

# Größe im Datensatz -> Kürzel der Reihen; Saldoquote bis 1993 auf das BSP bezogen (Einheit je Zeile im Datensatz)
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




# ---------------------------------------------------------------------------
# Inhaltliche Auswertung: Empfehlungen, Themen, Schwerpunkte, Voten
# Quelle: data/static/gd_positionen_dauerfragen.csv, gd_themen.csv, gd_schwerpunkte.csv, gd_voten.csv (abgeleitet, kanonisch auf dem Server)

FRAGEN = {"Lohnpolitik": "l", "Geldpolitik": "g", "Finanzpolitik": "f", "Arbeitsmarkt und Sozialstaat": "a"}
RUNDE = {"F": "Frühjahrsgutachten", "H": "Herbstgutachten"}
VOTUM = ("Votum", "Patt", "Sondergutachten", "Enthaltung")


def _csv(name: str) -> list[dict]:
    with open(ROOT / "data" / "static" / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _esc(t: str) -> str:
    return str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _jahre(*tabs) -> list[int]:
    ys = sorted({int(r.get("gutachten_jahr") or r.get("jahrgang")) for t in tabs for r in t})
    return list(range(ys[0], ys[-1] + 1))


def build_inhalte() -> dict:
    import json

    pos, them, schw, vot = (_csv(f) for f in ("gd_positionen_dauerfragen.csv", "gd_themen.csv", "gd_schwerpunkte.csv", "gd_voten.csv"))
    stats = {}
    # A: Empfehlungen der Herbstgutachten je Dauerfrage; Reihe nur mit eindeutiger Einordnung, alles andere im Tooltip
    att, ser = {}, {k: [] for k in FRAGEN.values()}
    for r in pos:
        if r["runde"] != "H" or r["frage"] not in FRAGEN:
            continue
        k, y = FRAGEN[r["frage"]], int(r["gutachten_jahr"])
        e = {"s": r["skala"], "k": r["kategorie"], "p": r["position"], "seite": r["seite"], "sich": r["sicherheit"], "lab": f"Herbstgutachten {y}"}
        if "kein Text" in r["flag"]:
            e = {"lab": f"Herbstgutachten {y}", "x": 1}
        elif "offen" in r["flag"]:
            e = {"lab": f"Herbstgutachten {y}", "o": 1, "p": ""}
        elif r["skala"] in ("-1", "0", "+1"):
            ser[k].append((f"{y}-01-01", float(r["skala"])))
        att.setdefault(k.upper(), {})[str(y)] = e
    for k, pts in ser.items():
        _write(f"gd_stance_{k}", pts)
    (ROOT / "data" / "static" / "gd_positionen.json").write_text(json.dumps(att, ensure_ascii=False), encoding="utf-8")
    svr = json.loads((ROOT / "data" / "static" / "svr_positionen.json").read_text(encoding="utf-8"))
    both = {k: {y: dict(v, lab=f"Sachverständigenrat, Jahresgutachten {y}") for y, v in svr.get(k, {}).items()} for k in "LGFA"}
    both.update({"G" + k: v for k, v in att.items()})
    (ROOT / "data" / "static" / "gd_svr_positionen.json").write_text(json.dumps(both, ensure_ascii=False), encoding="utf-8")
    # Gleichlauf mit dem SVR je Frage: Jahre, in denen beide eine eindeutige Stufe haben
    for k in "lgfa":
        g = dict(ser[k])
        sv = {f"{y}-01-01": float(v["s"]) for y, v in svr.get(k.upper(), {}).items() if v.get("s") not in (None, "", "NA")}
        common = [d for d in g if d in sv]
        stats[f"gleich_{k}"] = (sum(g[d] == sv[d] for d in common), len(common))
    # D: Voten je Jahr (beide Runden)
    years = _jahre(pos)
    text_years = {int(r["jahrgang"]) for r in vot if r["art"] != "kein Text"}
    cnt, tip = {}, {}
    for r in vot:
        y = int(r["jahrgang"])
        if r["art"] in VOTUM:
            cnt[y] = cnt.get(y, 0) + 1
            tip.setdefault(y, []).append(f'{RUNDE.get(r["runde"], "")}: {_esc(r["institute"] or "nicht genannt")}, {_esc(r["thema"] or r["kapitel"] or r["art"])}'
                                         + (f' (S. {_esc(r["seite"])})' if r["seite"] else ""))
    ys = [y for y in years if y in text_years]
    _write("gd_voten_n", [(f"{y}-01-01", cnt.get(y, 0)) for y in ys])
    (ROOT / "data" / "static" / "gd_dissens.json").write_text(json.dumps({
        "mode": "bar", "unit": "Anzahl", "years": ys, "values": [cnt.get(y, 0) for y in ys],
        "text": [f"<b>{y}: {cnt.get(y, 0)} abweichende Voten</b>" + "".join(f"<br>{t}" for t in tip.get(y, [])[:8]) + ("<br>…" if len(tip.get(y, [])) > 8 else "") for y in ys]},
        ensure_ascii=False), encoding="utf-8")
    stats["voten"] = (sum(cnt.values()), len([y for y in ys if cnt.get(y)]), len(ys))
    # B: Anteil der Seiten je Thema und Jahr (beide Runden, ohne Anhang und ohne offene Einordnung)
    katalog = [t for t in ("Weltwirtschaft", "Europa und Währungsunion", "Konjunktur Deutschland (Lage und Prognose)", "Preise und Inflation", "Arbeitsmarkt und Löhne",
                           "Geldpolitik und Finanzmärkte", "Finanzpolitik und Staatshaushalt", "Sozialversicherung und Demografie", "Migration", "Energie und Rohstoffe", "Klima",
                           "Investitionen und Bau", "Wohnen", "Privater Konsum", "Außenhandel und Wettbewerbsfähigkeit", "Wachstum, Potenzial und Struktur",
                           "Ostdeutschland und Vereinigung", "Sonstiges")]
    seiten, titel = {}, {}
    for r in them:
        if r["thema"] in ("", "Anhang") or "offen" in r["flag"] or "kein Text" in r["flag"]:
            continue
        try:
            n = int(r["seiten"])
        except ValueError:
            continue
        y = int(r["gutachten_jahr"])
        seiten[(y, r["thema"])] = seiten.get((y, r["thema"]), 0) + n
        titel.setdefault((y, r["thema"]), []).append(r["titel"])
    rows = [t for t in katalog if any(k[1] == t for k in seiten)][::-1]
    tyears = sorted({k[0] for k in seiten})
    tot = {y: sum(v for (yy, _), v in seiten.items() if yy == y) for y in tyears}
    cells = []
    for (y, t), v in seiten.items():
        if t not in rows:
            continue
        sh = round(100 * v / tot[y], 1)
        tt = titel[(y, t)]
        cells.append({"r": rows.index(t), "y": y, "v": sh, "t": f"<b>{y}, {_esc(t)}</b>: {str(sh).replace('.', ',')} % der Seiten"
                      + "".join(f"<br>{_esc(x[:70])}" for x in tt[:5]) + ("<br>…" if len(tt) > 5 else "")})
    (ROOT / "data" / "static" / "gd_themen_grid.json").write_text(json.dumps({"mode": "share", "unit": "% der Seiten", "rows": rows, "years": list(range(tyears[0], tyears[-1] + 1)),
                                                                             "zmax": 40, "cells": cells}, ensure_ascii=False), encoding="utf-8")
    # C: Schwerpunkte als Punkte je Thema und Jahr
    sp = {}
    for r in schw:
        if "kein Text" in r["flag"] or "offen" in r["flag"] or not r["thema"]:
            continue
        y = int(r["gutachten_jahr"])
        sp.setdefault((y, r["thema"]), []).append(f'{RUNDE.get(r["runde"], "")}: {_esc(r["titel"][:80])}' + (f' (S. {r["seite_von"]}-{r["seite_bis"]})' if r["seite_von"] else ""))
    srows = [t for t in katalog if any(k[1] == t for k in sp)][::-1]
    syears = sorted({k[0] for k in sp})
    scells = [{"r": srows.index(t), "y": y, "t": f"<b>{y}, {_esc(t)}</b>" + "".join(f"<br>{x}" for x in v[:6]) + ("<br>…" if len(v) > 6 else "")} for (y, t), v in sp.items()]
    (ROOT / "data" / "static" / "gd_schwerpunkte_grid.json").write_text(json.dumps({"mode": "dot", "unit": "", "rows": srows, "years": list(range(min(syears), max(syears) + 1)),
                                                                                   "cells": scells}, ensure_ascii=False), encoding="utf-8")
    stats["schwerpunkte"] = (len(sp), len({k[0] for k in sp}))
    return stats


if __name__ == "__main__":
    import json

    print(json.dumps({k: v for k, v in build().items() if k != "ziel"}, indent=1, ensure_ascii=False, default=str))
    print(json.dumps(build_inhalte(), indent=1, ensure_ascii=False, default=str))
