"""Schätzungen des Produktionspotenzials für Deutschland als statische Reihen (Wachstum ggü. Vorjahr in %).

Läuft vor dem Datenabruf (python -m monitor run) und schreibt nach data/static/<key>.csv (date,value):
- ameco_potential_de: Europäische Kommission, AMECO, Potenzial-BIP (OVGD) über DBnomics.
- oecd_potential_de: OECD Economic Outlook, Potenzial-BIP in konstanten Preisen (GDPVTR).
- imf_potential_de: IWF World Economic Outlook; Potenzialwachstum aus realem BIP-Wachstum (NGDP_RPCH) und
  Produktionslücke in % des Potenzials (NGAP_NPGDP): (1 + g) * (1 + Lücke Vorjahr) / (1 + Lücke) - 1.
Alle drei veröffentlichen zweimal im Jahr neue Schätzungen samt Prognosejahren. Ein gestörter Abruf lässt die
vorhandene Datei unverändert.
"""
from __future__ import annotations

import io
import json
import logging
import urllib.request
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
OECD = ("https://sdmx.oecd.org/public/rest/data/OECD.ECO.MAD,DSD_EO@DF_EO,/DEU.GDPVTR.A?startPeriod=1991",
        {"Accept": "application/vnd.sdmx.data+csv; charset=utf-8"})
IMF = "https://www.imf.org/external/datamapper/api/v1/{ind}/DEU"
AMECO = 'https://api.db.nomics.world/v22/series/AMECO/OVGD?dimensions={"geo":["deu"]}&observations=1&format=json'


def _get(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor", **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8")


def _growth(level: pd.Series) -> pd.Series:
    level = level.sort_index().astype(float)
    return ((level / level.shift(1) - 1) * 100).dropna().round(3)


def oecd() -> pd.Series:
    df = pd.read_csv(io.StringIO(_get(*OECD)))
    s = df.set_index(df["TIME_PERIOD"].astype(int))["OBS_VALUE"]
    return _growth(s)


def imf() -> pd.Series:
    def ind(name):
        v = json.loads(_get(IMF.format(ind=name)))["values"][name]["DEU"]
        return pd.Series({int(k): float(x) for k, x in v.items() if x is not None})
    g, gap = ind("NGDP_RPCH"), ind("NGAP_NPGDP")
    df = pd.DataFrame({"g": g, "gap": gap}).dropna().sort_index()
    pot = ((1 + df["g"] / 100) * (1 + df["gap"].shift(1) / 100) / (1 + df["gap"] / 100) - 1) * 100
    return pot.dropna().round(3)


def ameco() -> pd.Series:
    docs = json.loads(_get(AMECO))["series"]["docs"]
    doc = next(d for d in docs if d.get("dimensions", {}).get("unit", "").startswith("mrd"))  # Niveau in Mrd. Euro, konstante Preise
    s = pd.Series([v for v in doc["value"]], index=[int(p) for p in doc["period"]]).replace("NA", None).dropna()
    return _growth(s)


def update_potential(static: Path) -> None:
    for key, f in (("oecd_potential_de", oecd), ("imf_potential_de", imf), ("ameco_potential_de", ameco)):
        try:
            s = f()
            s = s[s.index >= 1992]
            if len(s) < 10:
                raise ValueError(f"nur {len(s)} Werte")
            old = static / f"{key}.csv"
            if old.exists():  # Plausibilität: eine neue Ausgabe verschiebt Schätzungen, aber nicht im Mittel um mehr als 0,5 Pp
                o = pd.read_csv(old)
                o = pd.Series(o["value"].values, index=pd.to_datetime(o["date"]).dt.year)
                common = o.index.intersection(s.index)
                if len(common) >= 5 and (o[common] - s[common]).abs().mean() > 0.5:
                    raise ValueError("weicht stark vom bisherigen Stand ab; bitte Abruf prüfen")
            pd.DataFrame({"date": [f"{y}-01-01" for y in s.index], "value": s.values}).to_csv(static / f"{key}.csv", index=False)
            log.info("Potenzial %s: %d Jahre bis %d", key, len(s), s.index.max())
        except Exception as e:  # Datei bleibt, wie sie ist
            log.warning("Potenzial %s nicht aktualisiert: %s", key, e)
