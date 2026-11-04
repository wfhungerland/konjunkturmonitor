"""Bildschirmfotos aller Abbildungen der gebauten Seite für die Word-Datei.

Aufruf nach dem Seitenbau: python -m monitor.shots [site]
Braucht Playwright mit Chromium (pip install playwright; playwright install chromium).
Ein anderer Chromium lässt sich über die Umgebungsvariable PW_CHROMIUM angeben.
Schreibt site/img/abb-N.png und baut danach die Word-Datei mit den Bildern neu.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HIDE = ".tools, .src, .fab, header, details.dl, .seg ~ .seg { display: none !important; }"


def take(site: Path) -> int:
    from playwright.sync_api import sync_playwright

    img = site / "img"
    img.mkdir(exist_ok=True)
    n = 0
    with sync_playwright() as p:
        kw = {"executable_path": os.environ["PW_CHROMIUM"]} if os.environ.get("PW_CHROMIUM") else {}
        b = p.chromium.launch(**kw)
        page = b.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1.5)
        page.goto((site / "index.html").resolve().as_uri())
        page.wait_for_timeout(800)
        page.add_style_tag(content=HIDE)
        page.eval_on_selector_all("details.morecharts", "ds => ds.forEach(d => d.open = true)")
        for card in page.query_selector_all(".card"):
            cid = card.get_attribute("id") or ""
            if not cid.startswith("abb-") or card.query_selector(".callist"):
                continue
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(350)
            box = card.query_selector(".cmain")
            if box is None:
                continue
            box.screenshot(path=str(img / f"{cid}.png"))
            n += 1
        b.close()
    return n


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    site = Path(argv[0] if argv else "site")
    n = take(site)
    print(f"{n} Abbildungen fotografiert")
    cache = Path(".cache") / "payload.json"
    if cache.exists():
        from .worddoc import write_page_docx
        payload = json.loads(cache.read_text(encoding="utf-8"))
        print("Word-Datei:", write_page_docx(payload, site))


if __name__ == "__main__":
    main()
