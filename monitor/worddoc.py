"""Die ganze Seite als Word-Datei zum Bearbeiten mit Änderungsverfolgung und Kommentaren.

Reihenfolge und Texte folgen der Seite, aufgeklappte Teile eingeschlossen. Grafiken stehen als Platzhalter.
Vor jedem bearbeitbaren Text steht eine graue Kennung in doppelten eckigen Klammern, etwa [[chart.cpi.caption]].
Sie zeigt, woher der Text stammt (monitor.yaml, Katalog oder automatisch erzeugter Satz), und erlaubt es,
eine bearbeitete Fassung der richtigen Stelle zuzuordnen. Kennungen bitte nicht ändern.
"""
from __future__ import annotations

from html.parser import HTMLParser
from importlib import resources
from pathlib import Path

PARTS = {"konjunktur": ("Teil I Konjunktur", "Wie läuft die Wirtschaft gerade? Monats- und Quartalszahlen zu Produktion, Preisen, Arbeit, Nachfrage und Stimmung."),
         "struktur": ("Teil II Struktur", "Was bestimmt das Wachstum auf längere Sicht? Jahreszahlen zu Potenzial, Produktivität, Investitionen, Zuwanderung, Steuern und Staatsfinanzen."),
         "service": ("Termine", "")}
GREY = (0x7F, 0x7F, 0x7F)


class _Quellen(HTMLParser):
    """Absätze, Überschriften und Listenpunkte aus dem Abschnitt „Quellen und Hinweise“ der Vorlage."""

    def __init__(self):
        super().__init__()
        self.on, self.depth, self.cur, self.items = False, 0, None, []

    def handle_starttag(self, tag, attrs):
        if tag == "section" and dict(attrs).get("id") == "quellen":
            self.on = True
        if self.on and tag in ("h2", "summary", "p", "li"):
            self.cur = [tag, ""]

    def handle_endtag(self, tag):
        if self.on and self.cur and tag == self.cur[0]:
            if self.cur[1].strip():
                self.items.append((self.cur[0], " ".join(self.cur[1].split())))
            self.cur = None
        if tag == "section" and self.on:
            self.on = False

    def handle_data(self, data):
        if self.cur is not None:
            self.cur[1] += data


def write_page_docx(payload: dict, out: Path) -> str:
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Pt, RGBColor

    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(11)

    def tag(p, key):
        r = p.add_run(f"[[{key}]] ")
        r.font.size, r.font.color.rgb = Pt(7), RGBColor(*GREY)

    def para(text, key=None, style=None, italic=False, size=None, grey=False):
        p = doc.add_paragraph(style=style)
        if key:
            tag(p, key)
        r = p.add_run(text)
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if grey:
            r.font.color.rgb = RGBColor(*GREY)
        return p

    def head(text, level, key=None):
        h = doc.add_heading(level=level)
        if key:
            tag(h, key)
        h.add_run(text)
        return h

    date = payload["generated_at"][:10]
    head("Konjunkturmonitor", 0)
    para(f"Stand {date[8:10]}.{date[5:7]}.{date[:4]}. Datei zum Bearbeiten: Änderungen bitte mit „Änderungen nachverfolgen“, Anmerkungen als Kommentar. "
         "Graue Kennungen [[…]] nicht ändern; sie ordnen jeden Text seiner Quelle zu: site, part und topic sowie chart.….ask, title und caption stehen in monitor.yaml "
         "oder im Katalog; question.….answer und chart.….texts sind automatisch aus den Daten erzeugt, Änderungen dort betreffen die Satzbausteine im Code.",
         italic=True, size=9, grey=True)
    if payload.get("overview"):
        para(payload["overview"], "overview")

    # Kennzahlen der Startseite
    rows = payload.get("start") or []
    if rows:
        head("Kennzahlen", 2)
        t = doc.add_table(rows=1, cols=6)
        t.style = "Light List"
        for i, h in enumerate(["Kennzahl", "Stand", "Wert", "Δ Vorperiode", "Δ Vorjahr", "Δ 3 Monate"]):
            t.rows[0].cells[i].text = h
        fmt = lambda v, d=1: "" if v is None else f"{v:+.{d}f}".replace(".", ",")
        for r in rows:
            c = t.add_row().cells
            d = int(r.get("decimals", 1))
            c[0].text, c[1].text = f"{r['label']} ({r.get('unit', '')})", r.get("period", "")
            c[2].text = f"{r['value']:.{d}f}".replace(".", ",")
            cd = int(r.get("change_decimals", 1))
            for k, key in ((3, "prev"), (4, "yoy"), (5, "m3")):
                c[k].text = fmt(r.get(key), cd) + (" " + r.get("change_unit", "") if r.get(key) is not None else "")

    cur = None
    for tp in payload["topics"]:
        q = tp.get("question")
        if not q and not tp["charts"]:
            continue
        part = tp.get("part", "konjunktur")
        if part != cur:
            cur = part
            p = doc.add_paragraph()
            p.add_run().add_break(WD_BREAK.PAGE)
            head(PARTS[part][0], 1, f"part.{part}.title")
            if PARTS[part][1]:
                para(PARTS[part][1], f"part.{part}.text")
        head(q["ask"] if q else (tp.get("ask") or tp["title"]), 1, f"topic.{tp['id']}.ask")
        lead = tp["charts"][0] if tp["charts"] else None
        ans = []
        if q:
            ans = [q["answer"]["head"], *q["answer"]["more"]]
        if lead and not (q and q.get("series") in [s.get("id") for s in (lead.get("series") or []) if isinstance(s, dict)]):
            ans += lead.get("texts") or []
        if ans:
            para(" ".join(ans), f"question.{tp['id']}.answer")
        if q and q.get("explain"):
            para(q["explain"], f"question.{tp['id']}.explain", italic=True)
        for i, c in enumerate(tp["charts"]):
            if i == 1:
                head(f"Weitere Abbildungen ({len(tp['charts']) - 1})", 3)
            cid = c["chart"]
            if i and c.get("ask"):
                head(c["ask"], 3, f"chart.{cid}.ask")
            if i and c.get("texts"):
                para(" ".join(c["texts"]), f"chart.{cid}.texts")
            kind = "Tab." if c.get("type") in ("heat", "calendar") else "Abb."
            h = head(f"{kind} {c['no']} {c.get('title', '')}", 4, f"chart.{cid}.title")
            meta = [x for x in (c.get("adjustment"),) if x]
            nu = c.get("next_update")
            if nu:
                meta.append(f"Neue Daten{', dann für ' + nu['period'] + ',' if nu.get('period') else ''} am {nu['date'][8:10]}.{nu['date'][5:7]}.{nu['date'][:4]}")
            if meta:
                para(" · ".join(meta), size=9, grey=True)
            if c.get("unit"):
                para(c["unit"], f"chart.{cid}.unit", size=9)
            para(f"[Grafik {kind} {c['no']}: {c.get('title', '')}]", size=9, grey=True)
            if c.get("caption"):
                para(c["caption"], f"chart.{cid}.caption", italic=True)
            for k, n in enumerate(c.get("notes") or []):
                para(f"{k + 1} {n['text']}", f"note.{cid}.{n['date']}", size=10)
            src = ", ".join(c.get("sources") or [])
            if src:
                para("Quelle: " + src, size=9, grey=True)

    # Quellen und Hinweise aus der Vorlage
    tpl = resources.files("monitor").joinpath("templates/index.html").read_text(encoding="utf-8")
    qp = _Quellen()
    qp.feed(tpl)
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    for k, (t, text) in enumerate(qp.items):
        key = f"static.quellen.{k + 1}"
        if t == "h2":
            head(text, 1, key)
        elif t == "summary":
            head(text, 3, key)
        elif t == "li":
            para(text, key, style="List Bullet")
        else:
            para(text, key)

    (out / "dl").mkdir(parents=True, exist_ok=True)
    name = f"Konjunkturmonitor ({date}) Seite zum Bearbeiten.docx"
    doc.save(out / "dl" / name)
    return "dl/" + name
