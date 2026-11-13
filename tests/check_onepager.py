"""Prüft eine vom Browser erzeugte Onepager-Datei (DOCX) ohne Zusatzpakete.

Aufruf: python tests/check_onepager.py onepager.docx
Geprüft wird: heiles ZIP, A4, Schrift Arial Narrow, je Abbildung Sachstand-Etikett oder Bewertung und eine Quelle,
mindestens ein Bild, jedes Bild ein PNG, Vektorbilder (SVG) gültig und mit PNG als Ersatzbild, keine internen Kürzel wie „Haushalte-2“ im sichtbaren Text.
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def check(path: str) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            return ["ZIP beschädigt"]
        names = z.namelist()
        doc = ET.fromstring(z.read("word/document.xml"))
        styles = z.read("word/styles.xml").decode("utf-8")
        ET.fromstring(z.read("[Content_Types].xml"))
        ET.fromstring(z.read("word/_rels/document.xml.rels"))
        media = [n for n in names if n.startswith("word/media/")]
        svgs = [n for n in media if n.endswith(".svg")]
        media = [n for n in media if not n.endswith(".svg")]
        for n in media:
            if z.read(n)[:8] != b"\x89PNG\r\n\x1a\n":
                errors.append(f"{n} ist kein PNG")
        for n in svgs:  # Vektorbild: gültiges XML, und das PNG als Ersatzbild liegt daneben
            if not ET.fromstring(z.read(n)).tag.endswith("}svg"):
                errors.append(f"{n} ist kein SVG")
            if n[:-4] + ".png" not in media:
                errors.append(f"{n} hat kein Ersatzbild")
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
        if doc.findall(".//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip").__len__() != len(svgs) or rels.count(".svg") != len(svgs):
            errors.append("Zahl der Vektorbilder und ihrer Verweise weicht ab")
    size = doc.find(f".//{W}pgSz")
    if size is None or (size.get(f"{W}w"), size.get(f"{W}h")) != ("11906", "16838"):
        errors.append("Seitenformat ist nicht A4")
    if 'w:ascii="Arial Narrow"' not in styles:
        errors.append("Standardschrift ist nicht Arial Narrow")
    rows = doc.findall(f".//{W}tr")
    blocks = [r for r in rows if len(r.findall(f"{W}tc")) == 3]
    text = lambda el: "".join(t.text or "" for t in el.iter(f"{W}t"))
    if not blocks:
        errors.append("keine Abbildung im Dokument")
    for r in blocks:
        left, _, right = (text(c) for c in r.findall(f"{W}tc"))
        if not re.search(r"Bewertung|Assessment", left):
            errors.append(f"Bewertung fehlt: {left[:50]}")
        if not re.search(r"(Quelle|Source): \S", right):
            errors.append(f"Quelle fehlt: {left[:50]}")
    if not media:
        errors.append("kein Bild im Dokument")
    if len(media) != len(doc.findall(f".//{W}drawing")):
        errors.append("Zahl der Bilder und der Bildstellen im Text weicht ab")
    short = re.findall(r"\b[A-ZÄÖÜ][a-zäöüß]+-\d{1,2}\b", text(doc))
    if short:
        errors.append(f"internes Kürzel im Text: {short[:3]}")
    print(f"Onepager-Datei: {len(blocks)} Abbildungen, {len(media)} Bilder, davon {len(svgs)} als Vektorgrafik")
    return errors


if __name__ == "__main__":
    errs = check(sys.argv[1])
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)
    print("Onepager-Datei geprüft.")
