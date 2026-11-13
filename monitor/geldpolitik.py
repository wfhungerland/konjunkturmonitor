"""Geldpolitik: Daten, die nicht über eine SDMX-Schnittstelle kommen, als statische Reihen (data/static/<name>.csv, date,value).

- Anleihekäufe der EZB je Programm (APP: PSPP, CSPP, CBPP3, ABSPP; PEPP öffentlich und privat): Bestände zum Monatsende
  zu fortgeführten Anschaffungskosten, in Mrd. €, aus den CSV-Dateien der EZB-Website.
- Kumulierte Nettokäufe von Staatsanleihen je Land (PSPP und PEPP zusammen), in Mrd. €.
Die Dateien ändern ihren Aufbau selten; ein gestörter Abruf hält den Lauf nicht auf (siehe wetter.update_all).
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger(__name__)

ECB = "https://www.ecb.europa.eu/mopo/pdf/"
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                      "October", "November", "December"], 1)}
QE_COUNTRIES = {"Germany": "de", "France": "fr", "Italy": "it", "Spain": "es"}


def _get(url: str) -> str:
    from .wetter import _get as get
    return get(url)


def _write(static: Path, name: str, rows: list[tuple[date, float]]) -> None:
    rows = sorted(rows)
    if len(rows) < 12:
        raise ValueError(f"{name}: zu wenige Werte ({len(rows)})")
    text = "date,value\n" + "".join(f"{d.isoformat()},{v:.4f}\n" for d, v in rows)
    (static / f"{name}.csv").write_text(text, encoding="utf-8")


def _num(x: str) -> float | None:
    x = (x or "").strip().replace(" ", "").replace(",", "")  # Tausendertrennzeichen in Anführungszeichen, etwa "-9,418"
    if x in ("", "-"):
        return None
    return float(x)


def _monthly_table(text: str) -> list[tuple[date, list[str]]]:
    """Zeilen „Jahr, Monat, Werte …“; das Jahr steht nur in der ersten Zeile eines Jahres."""
    out, year = [], None
    for r in csv.reader(io.StringIO(text)):
        if len(r) < 3:
            continue
        if r[0].strip().isdigit():
            year = int(r[0])
        m = MONTHS.get(r[1].strip())
        if year and m:
            out.append((date(year, m, 1), r[2:]))
    return out


def update_qe_programmes(static: Path) -> None:
    """Bestände je Programm zum Monatsende in Mrd. € (APP: Spalten 9 bis 12 der Werte; PEPP: Spalten 12 bis 17)."""
    app = _monthly_table(_get(ECB + "APP_breakdown_history.csv"))
    for k, name in enumerate(("qe_abspp", "qe_cbpp3", "qe_cspp", "qe_pspp")):
        _write(static, name, [(d, v / 1000) for d, r in app if len(r) > 8 + k and (v := _num(r[8 + k])) is not None])
    pepp = _monthly_table(_get(ECB + "PEPP_breakdown_history.csv"))
    pub = [(d, v / 1000) for d, r in pepp if len(r) > 16 and (v := _num(r[15])) is not None]
    tot = {d: v / 1000 for d, r in pepp if len(r) > 16 and (v := _num(r[16])) is not None}
    _write(static, "qe_pepp_pub", pub)
    _write(static, "qe_pepp_priv", [(d, tot[d] - v) for d, v in pub if d in tot])


def _country_net(text: str) -> dict[str, dict[date, float]]:
    """Erster Block „Net purchases“: Kopfzeile mit Monaten (31/03/2015 oder Mar-20), dann eine Zeile je Land."""
    rows = list(csv.reader(io.StringIO(text)))
    head = next(i for i, r in enumerate(rows) if len(r) > 3 and not r[0].strip() and r[1].strip())
    dates = []
    for x in rows[head][1:]:
        x = x.strip()
        d = None
        for fmt in ("%d/%m/%Y", "%b-%y"):
            try:
                t = datetime.strptime(x, fmt)
                d = date(t.year, t.month, 1)
                break
            except ValueError:
                pass
        dates.append(d)
    out = {}
    for r in rows[head + 1:]:
        if not r or not r[0].strip() or r[0].strip().startswith(("In EUR", "In euro", "Total")):
            break
        out[r[0].strip()] = {d: v for d, x in zip(dates, r[1:]) if d and (v := _num(x)) is not None}
    return out


def update_qe_countries(static: Path) -> None:
    """Kumulierte Nettokäufe von Staatsanleihen je Land, PSPP und PEPP zusammen, in Mrd. €."""
    pspp = _country_net(_get(ECB + "PSPP_breakdown_history.csv"))
    pepp = _country_net(_get(ECB + "PEPP_public_sector_securities_breakdown_history.csv"))
    for land, code in QE_COUNTRIES.items():
        a, b = pspp.get(land, {}), pepp.get(land, {})
        if not a:
            raise ValueError(f"PSPP: {land} fehlt")
        run, rows = 0.0, []
        for d in sorted(set(a) | set(b)):
            run += a.get(d, 0.0) + b.get(d, 0.0)
            rows.append((d, run / 1000))
        _write(static, f"qe_net_{code}", rows)


# Euroraum ohne Kleinstaaten-Sonderfälle: alle Mitglieder 2026 (Bulgarien seit 1. Januar 2026); Eurostat schreibt Griechenland EL, die EZB GR
EURO = {"AT": "Österreich", "BE": "Belgien", "BG": "Bulgarien", "CY": "Zypern", "DE": "Deutschland", "EE": "Estland", "ES": "Spanien",
        "FI": "Finnland", "FR": "Frankreich", "GR": "Griechenland", "HR": "Kroatien", "IE": "Irland", "IT": "Italien", "LT": "Litauen",
        "LU": "Luxemburg", "LV": "Lettland", "MT": "Malta", "NL": "Niederlande", "PT": "Portugal", "SI": "Slowenien", "SK": "Slowakei"}
EURO_EN = {"AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "DE": "Germany", "EE": "Estonia", "ES": "Spain", "FI": "Finland",
           "FR": "France", "GR": "Greece", "HR": "Croatia", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
           "MT": "Malta", "NL": "Netherlands", "PT": "Portugal", "SI": "Slovenia", "SK": "Slovakia"}
EDP_URL = ("https://economy-finance.ec.europa.eu/economic-governance-framework/stability-and-growth-pact/"
           "corrective-arm-excessive-deficit-procedure/excessive-deficit-procedures-overview_en")
EUROSTAT_EDP = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/gov_10dd_edpt1?format=JSON&lang=en&unit=PC_GDP"
                "&sector=S13&na_item=B9&na_item=GD&lastTimePeriod=1&" + "&".join(f"geo={'EL' if g == 'GR' else g}" for g in EURO))
ECB_IRS = "https://data-api.ecb.europa.eu/service/data/IRS/M..L.L40.CI.0000.EUR.N.Z?lastNObservations=1&format=csvdata&detail=dataonly"


def _edp_countries(page: str) -> list[str]:
    """Länder mit laufendem Defizitverfahren: die Namen zwischen „Overview of ongoing“ und „Overview of closed“ auf der Kommissionsseite."""
    import html
    import re
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    x = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "|", t)))
    i, j = x.find("Overview of ongoing excessive deficit procedures"), x.find("Overview of closed excessive deficit procedures")
    if i < 0 or j < i:
        raise ValueError("Kommissionsseite: Abschnitt zu laufenden Defizitverfahren nicht gefunden")
    names = [n.strip() for n in x[i:j].split("|")[1:] if n.strip()]
    return [k for k, v in EURO_EN.items() if v in names or f"The {v}" in names]


def update_tpi(static: Path) -> None:
    """Bedingungen des TPI je Euroland (data/static/tpi.json): Defizit und Schulden in % des BIP (Eurostat, jüngstes Jahr),
    laufendes Defizitverfahren (Kommissionsseite), Renditeabstand zehnjähriger Staatsanleihen zu Deutschland (EZB, jüngster Monat)."""
    import json
    d = json.loads(_get(EUROSTAT_EDP))
    dims, size = d["id"], d["size"]
    idx = {k: d["dimension"][k]["category"]["index"] for k in dims}
    year = next(iter(idx["time"]))
    def val(item: str, geo: str):
        pos = 0
        for k, n in zip(dims, size):
            code = {"na_item": item, "geo": geo}.get(k, next(iter(idx[k])))
            pos = pos * n + idx[k][code]
        return d["value"].get(str(pos))
    yields, month = {}, None
    for r in csv.DictReader(io.StringIO(_get(ECB_IRS))):
        if r["REF_AREA"] in EURO and r.get("OBS_VALUE"):
            yields[r["REF_AREA"]], month = float(r["OBS_VALUE"]), r["TIME_PERIOD"]
    edp = _edp_countries(_get(EDP_URL))
    if not edp and len(yields) < 15:
        raise ValueError("TPI: zu wenige Daten")
    rows = []
    for g, name in EURO.items():
        e = "EL" if g == "GR" else g
        dfc, debt = val("B9", e), val("GD", e)
        sp = round(yields[g] - yields["DE"], 2) if g in yields and "DE" in yields and g != "DE" else None
        rows.append({"geo": g, "name": name, "name_en": EURO_EN[g], "deficit": dfc, "debt": debt, "edp": g in edp, "spread": sp,
                     "yield": yields.get(g)})
    out = {"year": year, "month": month, "edp_url": EDP_URL, "rows": rows,
           "sources": ["Eurostat (gov_10dd_edpt1)", "Europäische Kommission, Übersicht der Defizitverfahren", "EZB (IRS)"]}
    (static / "tpi.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# Zinsstruktur je Land: Renditen von Staatsanleihen nach Restlaufzeit, Monatswerte
BBK_ZST = ("https://api.statistiken.bundesbank.de/rest/data/BBSIS/M.I.ZST.ZI.EUR.S1311.B.A604.{m}.R.A.A._Z._Z.A"
           "?startPeriod=2005-01&detail=dataonly")
DE_MAT = {1: "R01XX", 2: "R02XX", 3: "R03XX", 5: "R05XX", 7: "R07XX", 10: "R10XX", 15: "R15XX", 20: "R20XX", 30: "R30XX"}
ES_CSV = "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/ti_1_3.csv"
ES_MAT = {1: "D_DTES00U7", 3: "D_G0B1F0ZN", 5: "D_G0B1F0ZO", 10: "D_G0B1F0ZP", 15: "D_G0B1F0ZQ"}
IT_ZIP = "https://a2a.bancaditalia.it/infostat/dataservices/export/EN/CSV/DATA/CUBE/BANKITALIA/DIFF/BMK0100"
IT_MAT = {3: "MFN_BMK.M.020.922.0.EUR.203", 5: "MFN_BMK.M.020.922.0.EUR.205", 10: "MFN_BMK.M.020.922.0.EUR.210", 30: "MFN_BMK.M.020.922.0.EUR.230"}
ES_MONTHS = {m: i for i, m in enumerate(["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"], 1)}


def _bytes(url: str, accept: str = "") -> bytes:
    import time
    import urllib.request
    for k in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Konjunkturmonitor/1.0", **({"Accept": accept} if accept else {})})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception:
            if k == 3:
                raise
            time.sleep(5 * (k + 1))
    return b""


def _curve_de() -> dict[int, dict[date, float]]:
    out = {}
    for y, m in DE_MAT.items():
        rows = list(csv.reader(io.StringIO(_bytes(BBK_ZST.format(m=m), "application/vnd.sdmx.data+csv;version=1.0.0").decode("utf-8-sig")), delimiter=";"))
        rows = [r for r in rows if r]
        h = rows[0]
        it, iv = h.index("TIME_PERIOD"), h.index("OBS_VALUE")
        out[y] = {date(int(r[it][:4]), int(r[it][5:7]), 1): float(r[iv]) for r in rows[1:] if len(r) > iv and r[iv] not in ("", ".")}
    return out


def _curve_es() -> dict[int, dict[date, float]]:
    """Tageswerte des Sekundärmarkts (Banco de España, Tabelle 1.3) zu Monatsmitteln."""
    rows = list(csv.reader(io.StringIO(_bytes(ES_CSV).decode("latin-1"))))
    col = {c: i for i, c in enumerate(rows[0])}
    acc: dict[int, dict[date, list[float]]] = {y: {} for y in ES_MAT}
    for r in rows[6:]:
        p = r[0].split() if r else []
        if len(p) != 3 or p[1] not in ES_MONTHS:
            continue
        d = date(int(p[2]), ES_MONTHS[p[1]], 1)
        if d.year < 2005:
            continue
        for y, code in ES_MAT.items():
            v = r[col[code]] if code in col and col[code] < len(r) else ""
            if v not in ("", "_"):
                acc[y].setdefault(d, []).append(float(v))
    return {y: {d: sum(v) / len(v) for d, v in m.items()} for y, m in acc.items()}


def _curve_it() -> dict[int, dict[date, float]]:
    """Monatsmittel der Renditen von Benchmark-Staatsanleihen (Banca d'Italia, BDS-Tabelle BMK0100), ZIP mit einer CSV."""
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(_bytes(IT_ZIP)))
    text = z.read(z.namelist()[0]).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    col = {c: i for i, c in enumerate(rows[0])}
    out = {}
    for y, code in IT_MAT.items():
        out[y] = {date(int(r[0][:4]), int(r[0][5:7]), 1): float(r[col[code]]) for r in rows[1:]
                  if len(r) > col[code] and r[col[code]] not in ("", "NaN") and int(r[0][:4]) >= 2005}
    return out


def update_curves(static: Path) -> None:
    """Zinskurven je Land (data/static/zinskurven.json): jüngster gemeinsamer Monat und derselbe Monat ein Jahr zuvor;
    dazu je Land der Abstand zehnjähriger zu dreijährigen Renditen als Reihe (curve_slope_<land>.csv)."""
    import json
    out = []
    for code, name, name_en, src, f in (("de", "Deutschland", "Germany", "Deutsche Bundesbank", _curve_de),
                                        ("it", "Italien", "Italy", "Banca d'Italia", _curve_it),
                                        ("es", "Spanien", "Spain", "Banco de España", _curve_es)):
        try:
            c = f()
        except Exception as e:  # ein Land fehlt, die anderen bleiben
            log.warning("Zinskurve %s nicht aktualisiert: %s", name, e)
            continue
        c = {y: m for y, m in c.items() if m}
        if 3 not in c or 10 not in c:
            continue
        last = max(set.intersection(*[set(m) for m in c.values()]))
        ago = date(last.year - 1, last.month, 1)
        mats = sorted(c)
        out.append({"code": code, "name": name, "name_en": name_en, "source": src, "maturities": mats,
                    "now": {"date": last.isoformat(), "values": [round(c[y].get(last), 3) if c[y].get(last) is not None else None for y in mats]},
                    "ago": {"date": ago.isoformat(), "values": [round(c[y][ago], 3) if ago in c[y] else None for y in mats]}})
        _write(static, f"curve_slope_{code}", [(d, c[10][d] - c[3][d]) for d in c[10] if d in c[3]])
    if not out:
        raise ValueError("keine Zinskurve abrufbar")
    (static / "zinskurven.json").write_text(json.dumps({"countries": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def update_all(static: Path) -> None:
    for name, f in (("Anleihekäufe je Programm", update_qe_programmes), ("Anleihekäufe je Land", update_qe_countries), ("TPI-Bedingungen", update_tpi), ("Zinskurven", update_curves)):
        try:
            f(static)
        except Exception as e:  # ein gestörter Abruf hält den Lauf nicht auf
            log.warning("%s nicht aktualisiert: %s", name, e)
