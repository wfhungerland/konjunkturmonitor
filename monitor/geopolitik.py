"""Reihen für den Teil Geopolitik als statische Dateien (data/static/<key>.csv mit date,value).

Täglich im Lauf (python -m monitor run):
- gpr_de, gpr_world: Geopolitical Risk Index nach Caldara und Iacoviello (2022), Monatswerte. Der Länderindex
  ist der Anteil der Zeitungsartikel mit geopolitischen Risiken und Bezug auf Deutschland; beide Reihen hier
  normiert auf ein Mittel von 100 in den Jahren 1985 bis 2019.

Von Hand nach einer neuen Ausgabe der Quelle (python -m monitor.geopolitik <quelle> <datei>):
- leiden: Russian Operations Against Europe Dataset (Universität Leiden, Harvard Dataverse, CC BY 4.0),
  Vorfälle je Quartal mit Deutschland und im übrigen Europa.
- sipri: SIPRI Military Expenditure Database, Militärausgaben in % des BIP.
- cow: Correlates of War, National Material Capabilities, Anteil am Machtindex CINC in %.
- kiel: Kiel Ukraine Support Tracker, Zuteilungen Deutschlands je Quartal in Mrd. €.
- de_exp_rusblr, de_exp_cauca (täglich): Exporte nach Russland und Belarus sowie in sechs Länder in Kaukasus und
  Zentralasien (Comext), Summe der letzten zwölf Monate in Mrd. €.
- gta: Global Trade Alert, Export aller Eingriffe (interventions.csv): schädliche Eingriffe (rot und gelb)
  mit Deutschland unter den betroffenen Ländern je Jahr des Inkrafttretens, nach China, USA und übrigen Staaten.
"""
from __future__ import annotations

import io
import logging
import sys
import urllib.request
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
GPR = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.dta"
SIPRI = {"deu": "Germany", "fra": "France", "gbr": "United Kingdom", "pol": "Poland", "usa": "United States of America", "rus": "Russia"}
COW = {"deu": (255, 260, 265)}  # Deutschland 1955–1989: BRD und DDR
COMEXT = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
          "?reporter=DE&{partners}&product=TOTAL&flow=2&indicators=VALUE_IN_EUROS&freq=M&sinceTimePeriod=2018-01")
TRADE = {"de_exp_rusblr": ["RU", "BY"], "de_exp_cauca": ["AM", "GE", "KZ", "KG", "TJ", "UZ"]}  # Russland und Belarus; Kaukasus und Zentralasien


def _write(path: Path, s: pd.Series, digits: int = 3) -> None:
    s = s.dropna().sort_index()
    pd.DataFrame({"date": pd.to_datetime(s.index).strftime("%Y-%m-%d"), "value": s.round(digits).values}).to_csv(path, index=False)


def _years(s: pd.Series) -> pd.Series:
    s.index = pd.to_datetime([f"{int(y)}-01-01" for y in s.index])
    return s


def gpr(raw: bytes) -> dict[str, pd.Series]:
    df = pd.read_stata(io.BytesIO(raw)).set_index("month")
    out = {}
    for key, col in (("gpr_de", "GPRC_DEU"), ("gpr_world", "GPR")):
        s = df[col].dropna().astype(float)
        out[key] = s / s.loc["1985":"2019"].mean() * 100
    return out


def update_gpr(static: Path) -> None:
    req = urllib.request.Request(GPR, headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    for key, s in gpr(raw).items():
        if len(s) < 400 or s.index.max() < pd.Timestamp.today() - pd.DateOffset(months=6):
            raise ValueError(f"{key}: Reihe unvollständig")
        _write(static / f"{key}.csv", s, 1)
        log.info("GPR %s: bis %s", key, s.index.max().strftime("%Y-%m"))


def leiden(path: Path) -> dict[str, pd.Series]:
    df = pd.read_excel(path, sheet_name="EventData").dropna(subset=["IncidentYear"])
    month = pd.to_datetime(df["IncidentMonth"], format="%B", errors="coerce").dt.month
    ok = month.notna()  # Vorfälle ohne bekannten Monat fehlen in der Quartalszählung
    df, month = df[ok], month[ok].astype(int)
    df = df.assign(q=pd.PeriodIndex.from_fields(year=df["IncidentYear"].astype(int).values, quarter=((month - 1) // 3 + 1).values, freq="Q"))
    de = df["Where"].astype(str).str.contains("German", case=False)
    full = pd.period_range(f"{int(df['IncidentYear'].min())}Q1", f"{int(df['IncidentYear'].max())}Q4", freq="Q")
    out = {}
    for key, part in (("leiden_ops_de", df[de]), ("leiden_ops_eu", df[~de])):
        s = part.groupby("q").size().reindex(full, fill_value=0).astype(float)
        s.index = s.index.to_timestamp()
        out[key] = s
    return out


def _sipri_row(x: pd.DataFrame, name: str, factor: float) -> pd.Series:
    r = pd.to_numeric(x.loc[name], errors="coerce").dropna() * factor
    return _years(r[[str(c).isdigit() and len(str(c)) == 4 for c in r.index]])


def sipri(path: Path) -> dict[str, pd.Series]:
    gdp = pd.read_excel(path, sheet_name="Share of GDP", header=5).set_index("Country")
    gov = pd.read_excel(path, sheet_name="Share of Govt. spending", header=7).set_index("Country")
    usd = pd.read_excel(path, sheet_name="Constant (2024) US$", header=5).set_index("Country")
    reg = pd.read_excel(path, sheet_name="Regional totals", header=13).set_index("Region")
    out = {}
    for key, name in SIPRI.items():
        out[f"sipri_milex_{key}"] = _sipri_row(gdp, name, 100)
        out[f"sipri_gov_{key}"] = _sipri_row(gov, name, 100)
    out["sipri_usd_rus"] = _sipri_row(usd, "Russia", 0.001)  # Mio. US-$ in Mrd.
    out["sipri_usd_cwe"] = _sipri_row(reg, "Central and Western Europe", 1)
    return out


def trade(raw: str) -> dict[str, pd.Series]:
    """Comext (JSON-stat): Exporte Deutschlands je Partner und Monat; Summe je Gruppe über zwölf Monate in Mrd. €."""
    import json
    d = json.loads(raw)
    dims, size = d["id"], d["size"]
    idx = {k: {v: i for v, i in d["dimension"][k]["category"]["index"].items()} for k in dims}
    times = sorted(idx["time"], key=idx["time"].get)
    stride = {k: int(pd.Series(size[dims.index(k) + 1:]).prod()) if dims.index(k) + 1 < len(dims) else 1 for k in dims}
    val = {int(k): v for k, v in d["value"].items()}
    get = lambda p, t: val.get(idx["partner"][p] * stride["partner"] + idx["time"][t] * stride["time"])
    everyone = [p for ps in TRADE.values() for p in ps]
    times = times[:max(i for i, t in enumerate(times) if all(get(p, t) is not None for p in everyone)) + 1]  # bis zum jüngsten vollständigen Monat
    out = {}
    for key, partners in TRADE.items():
        vals = [[get(p, t) for t in times] for p in partners]
        if any(v is None for vs in vals for v in vs):
            raise ValueError(f"{key}: Monate fehlen")
        m = pd.Series([sum(vs) for vs in zip(*vals)], index=pd.to_datetime(times))
        out[key] = (m.rolling(12).sum() / 1e9).dropna()
    return out


def update_trade(static: Path) -> None:
    partners = "&".join(f"partner={p}" for ps in TRADE.values() for p in ps)
    req = urllib.request.Request(COMEXT.format(partners=partners), headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8")
    for key, s in trade(raw).items():
        _write(static / f"{key}.csv", s, 3)
        log.info("Handel %s: bis %s", key, s.index.max().strftime("%Y-%m"))


def cow(path: Path) -> dict[str, pd.Series]:
    n = pd.read_csv(path)
    out = {}
    for key, codes in COW.items():
        sub = n[n["ccode"].isin(codes)]
        if len(codes) > 1:  # Gesamtstaat, wo vorhanden (auch 1990); sonst BRD und DDR, aber nicht die DDR allein (1954)
            whole = set(sub[sub["ccode"] == codes[0]]["year"])
            sub = sub[(sub["ccode"] == codes[0]) | ~sub["year"].isin(whole)]
            sub = sub[sub["year"].isin(whole | set(sub[sub["ccode"] == codes[1]]["year"]))]
        s = sub.groupby("year")["cinc"].sum() * 100
        out[f"cow_cinc_{key}"] = _years(s)
    return out


def kiel(path: Path) -> dict[str, pd.Series]:
    def row(sheet: str) -> pd.Series:
        d = pd.read_excel(path, sheet_name=sheet, header=None)
        months = d.iloc[10]
        cols = [c for c in d.columns if pd.api.types.is_number(months[c]) and not pd.isna(months[c]) and c > 2]
        r = d[d[1].astype(str).str.strip() == "Germany"].iloc[0]
        return pd.Series([float(r[c] or 0) for c in cols], index=pd.date_range("2022-01-01", periods=len(cols), freq="MS"))
    total, mil = row("Allocations per Month"), row("Allocations per Month Military")
    q = lambda s: s.groupby(s.index.to_period("Q")).agg(["sum", "size"])
    out = {}
    for key, s in (("kiel_de_mil", mil), ("kiel_de_other", total - mil)):
        g = q(s)
        g = g[g["size"] == 3]["sum"]  # nur vollständige Quartale
        g.index = g.index.to_timestamp()
        out[key] = g
    return out


def gta(path: Path) -> dict[str, pd.Series]:
    d = pd.read_csv(path, low_memory=False, usecols=["GTA Evaluation", "Implementing Jurisdictions", "Affected Jurisdictions", "Date Implemented"])
    d = d[d["GTA Evaluation"].isin(["Red", "Amber"]) & d["Affected Jurisdictions"].fillna("").str.split(", ").apply(lambda l: "Germany" in l)]
    year = pd.to_datetime(d["Date Implemented"], errors="coerce").dt.year
    last = pd.Timestamp.today().year - 1  # nur abgeschlossene Jahre
    d = d.assign(year=year)[(year >= 2009) & (year <= last)]
    who = d["Implementing Jurisdictions"].fillna("")
    out = {}
    for key, mask in (("gta_de_chn", who == "China"), ("gta_de_usa", who == "United States of America"),
                      ("gta_de_other", ~who.isin(["China", "United States of America"]))):
        s = d[mask].groupby("year").size().reindex(range(2009, last + 1), fill_value=0).astype(float)
        out[key] = _years(s)
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("leiden", "sipri", "cow", "kiel", "gta"):
        print("Aufruf: python -m monitor.geopolitik leiden|sipri|cow|kiel|gta <datei>")
        return 2
    static = Path("data/static")
    digits = {"leiden": 0, "sipri": 3, "cow": 3, "kiel": 3, "gta": 0}[argv[0]]
    for key, s in globals()[argv[0]](Path(argv[1])).items():
        _write(static / f"{key}.csv", s, digits)
        print(f"{key}: {len(s)} Werte bis {s.index.max():%Y-%m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
