"""Staatsausgaben je Einwohner nach Aufgaben als feste Reihen (Euro je Einwohner und Jahr).

Läuft vor dem Datenabruf (python -m monitor run) und schreibt nach data/static/staat_pk_<gruppe>.csv (date,value).
Grundlage: Eurostat gov_10a_exp (Ausgaben des Staates nach Aufgaben, COFOG, Mio. Euro) und nama_10_pe
(Bevölkerung, Tausend Personen). Die zehn Aufgabenbereiche sind zu fünf Gruppen zusammengefasst. Ein gestörter
Abruf lässt die vorhandenen Dateien unverändert.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)
API = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
GROUPS = {
    "sozial": ["GF10"],  # Soziale Sicherung: Renten, Familie, Arbeitslosigkeit
    "gesundheit": ["GF07"],
    "bildung": ["GF09"],
    "verwaltung": ["GF01"],  # Allgemeine öffentliche Verwaltung, darunter Zinsen
    "uebrige": ["GF02", "GF03", "GF04", "GF05", "GF06", "GF08"],  # Verteidigung, Sicherheit, Wirtschaft, Umwelt, Wohnen, Kultur
}


def _get(q: str) -> dict:
    req = urllib.request.Request(API + q, headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def _series(d: dict, dim: str) -> dict[str, dict[int, float]]:
    """Werte je Ausprägung von dim und Jahr; die übrigen Dimensionen haben je eine Ausprägung."""
    ids, size = d["id"], d["size"]
    cats = {k: {v: i for v, i in d["dimension"][k]["category"]["index"].items()} for k in ids}
    inv = {k: {i: v for v, i in cats[k].items()} for k in ids}
    out: dict[str, dict[int, float]] = {}
    for flat, val in d["value"].items():
        i, idx = int(flat), {}
        for k, s in zip(reversed(ids), reversed(size)):
            idx[k] = inv[k][i % s]
            i //= s
        out.setdefault(idx[dim], {})[int(idx["time"])] = float(val)
    return out


def update_prokopf(static: Path) -> None:
    try:
        codes = "&".join(f"cofog99={c}" for g in GROUPS.values() for c in g)
        exp = _series(_get(f"gov_10a_exp?geo=DE&sector=S13&na_item=TE&unit=MIO_EUR&{codes}&sinceTimePeriod=1995"), "cofog99")
        pop = _series(_get("nama_10_pe?geo=DE&na_item=POP_NC&unit=THS_PER&sinceTimePeriod=1995"), "na_item")["POP_NC"]
        years = sorted(y for y in pop if all(y in exp.get(c, {}) for g in GROUPS.values() for c in g))
        if len(years) < 10:
            raise ValueError(f"nur {len(years)} Jahre")
        for name, cs in GROUPS.items():
            rows = [f"{y}-01-01,{round(sum(exp[c][y] for c in cs) * 1e6 / (pop[y] * 1e3), 0):.0f}" for y in years]
            (static / f"staat_pk_{name}.csv").write_text("date,value\n" + "\n".join(rows) + "\n", encoding="utf-8")
        log.info("Staatsausgaben je Einwohner: %d Jahre bis %d", len(years), years[-1])
    except Exception as e:  # Dateien bleiben, wie sie sind
        log.warning("Staatsausgaben je Einwohner nicht aktualisiert: %s", e)
