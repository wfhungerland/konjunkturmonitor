"""Abkürzungen: in Sätzen ausgeschrieben, in Achsen, Kacheln und Köpfen kurz mit Erklärung beim Darauftippen.

`spell` schreibt Abkürzungen in den automatischen Sätzen aus („ggü.“ wird „gegenüber dem“, „BIP“ wird
„Bruttoinlandsprodukt“). Es läuft nach der Satzprüfung, damit deren Muster unverändert greifen.
`GLOSSAR` geht an die Seite: dort erklärt sie Kurzformen in Achsen, Kacheln und Köpfen.
"""
from __future__ import annotations

import re

# Kurzform: Erklärung beim Darauftippen (deutsche Seite); englische Fassung in GLOSSARY_EN
GLOSSAR = {
    "BIP": "Bruttoinlandsprodukt: Wert aller in Deutschland hergestellten Waren und Dienstleistungen",
    "VPI": "Verbraucherpreisindex: Preise eines festen Warenkorbs der privaten Haushalte",
    "HVPI": "Harmonisierter Verbraucherpreisindex: EU-weit vergleichbar berechnete Verbraucherpreise",
    "ALQ": "Arbeitslosenquote",
    "ESI": "Economic Sentiment Indicator: Stimmungsindikator der EU-Kommission",
    "TTF": "Title Transfer Facility: niederländischer Handelspunkt, Leitpreis für Erdgas in Europa",
    "MWh": "Megawattstunde: 1 000 Kilowattstunden",
    "MMBtu": "Million British Thermal Units: US-Energiemaß, rund 0,29 Megawattstunden",
    "ggü.": "gegenüber",
    "Pp": "Prozentpunkte: Abstand zwischen zwei Prozentwerten",
    "Mrd.": "Milliarden",
    "Pkt.": "Punkte",
    "Mio.": "Millionen",
    "Tsd.": "Tausend",
    "EZB": "Europäische Zentralbank",
    "€STR": "Euro Short-Term Rate: Tageszins unter Banken im Euroraum",
    "AMECO": "Datenbank der EU-Kommission",
    "IWF": "Internationaler Währungsfonds",
    "KSB": "Kalender- und saisonbereinigt",
    "SB": "saisonbereinigt",
}
GLOSSARY_EN = {
    "GDP": "Gross domestic product: value of all goods and services produced",
    "CPI": "Consumer price index: prices of a fixed basket of household goods and services",
    "HICP": "Harmonised index of consumer prices: consumer prices computed alike across the EU",
    "ESI": "Economic Sentiment Indicator of the European Commission",
    "TTF": "Title Transfer Facility: Dutch trading hub, benchmark price for gas in Europe",
    "MWh": "Megawatt hour: 1,000 kilowatt hours",
    "MMBtu": "Million British thermal units, about 0.29 megawatt hours",
    "pp": "Percentage points: distance between two percentages",
    "ECB": "European Central Bank",
    "€STR": "Euro short-term rate: overnight rate between banks in the euro area",
    "IMF": "International Monetary Fund",
}

# Beträge im britischen Stil: Währungszeichen vor der Zahl, „€141,1 Mrd.“; geschütztes Leerzeichen vor „Mrd.“,
# damit nichts umbricht. US-Dollar als $, Pfund als £; Yuan und Franken bleiben ausgeschrieben.
_NBSP = "\u00a0"
_RULES = [
    (r"([+-]?)(\d[\d.,]*) (?:Milliarden|Mrd\.) (?:€|Euro\b)", r"\1€\2" + _NBSP + "Mrd."),
    (r"([+-]?)(\d[\d.,]*) (?:Millionen|Mio\.) (?:€|Euro\b)", r"\1€\2" + _NBSP + "Mio."),
    (r"([+-]?)(\d[\d.,]*) €", r"\1€\2"),
    (r"(Mrd|Mio)\.\.", r"\1."),  # Satzende: kein doppelter Punkt
    (r"([+-]?)(\d[\d.,]*) US-Dollar\b", r"\1$\2"),
    (r"([+-]?)(\d[\d.,]*) Pfund\b", r"\1£\2"),
    (r"\b([Gg])gü\.\s(?=(?:Vor\w*|Durchschnitt|Mittel)\b)", r"\1egenüber dem "),
    (r"\b([Gg])gü\.\s", r"\1egenüber "),
    (r"\bPreisindex des BIP \(BIP-Deflator\)", "Preisindex des Bruttoinlandsprodukts (Deflator)"),
    (r"\b(ein|das|Das) BIP-Wachstum\b", r"\1 Wirtschaftswachstum"),
    (r"\bBIP-Wachstum", "Wirtschaftswachstum"),
    (r"\bdes (realen |nominalen )?BIP\b(?!-)", r"des \1Bruttoinlandsprodukts"),
    (r"(?<![\w-])BIP\b(?!-)", "Bruttoinlandsprodukt"),
    (r"\(HVPI\)", "(EU-weit harmonisiert gemessen)"),
    (r"\(ESI; ", "(Indikator der EU-Kommission; "),
    (r"\(TTF\)", "(Handelspunkt TTF)"),
    (r"von AMECO, OECD und IWF\b", "von EU-Kommission, OECD und Internationalem Währungsfonds"),
    (r"\bje MWh\b", "je Megawattstunde"),
    (r"\bje MMBtu\b", "je Million British Thermal Units"),
    (r"\b(bei|von|mit|in) ((?:[+-]?[\d.,]+ )?)Pp\b", r"\1 \2Prozentpunkten"),
    (r"(?<![\d,])1 Pp\b", "1 Prozentpunkt"),
    (r"\bPp\b", "Prozentpunkte"),
    (r"(?<= )Mrd\.(?=\s)", "Milliarden"),
    (r"(?<= )Mio\.(?=\s)", "Millionen"),
    (r"(\d{1,3}(?:\.\d{3})+) Tsd\.", lambda m: f"{int(m.group(1).replace('.', '')) / 1000:.2f}".replace(".", ",") + " Millionen"),
    (r"\bTsd\.", "Tausend"),
]
_COMPILED = [(re.compile(a), b) for a, b in _RULES]


def spell(s: str) -> str:
    """Abkürzungen in einem Satz ausschreiben."""
    if not s:
        return s
    for rx, rep in _COMPILED:
        s = rx.sub(rep, s)
    return s
