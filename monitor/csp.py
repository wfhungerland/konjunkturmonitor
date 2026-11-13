"""Content-Security-Policy für die veröffentlichte Seite: Der Browser führt nur Skripte aus, die zur Seite gehören.

Trägt in jede HTML-Datei unter site/ ein Meta-Element ein. Erlaubt sind Dateien vom eigenen Server und genau die Skripte,
die beim Bau in der Seite stehen (per SHA-256 benannt). Eingeschleuster Code läuft damit nicht, und Daten können nur an den
eigenen Server und an den Formulardienst gehen. Läuft im Workflow nach den Vorschaubildern, weil diese die Seite noch ändern:

    python -m monitor.csp site

Lokal gebaute Seiten bleiben ohne diese Regel, damit sie sich als Datei öffnen lassen (file:// kennt keinen eigenen Server).
GitHub Pages erlaubt keine eigenen Kopfzeilen; deshalb das Meta-Element. Einbetten in fremde Seiten bleibt möglich.
"""
from __future__ import annotations

import base64
import hashlib
import re
import sys
from pathlib import Path

FORM = "https://formspree.io"  # Feedback-Formular (site.feedback)
MARK = '<meta http-equiv="Content-Security-Policy"'
INLINE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
OLD = re.compile(re.escape(MARK) + r"[^>]*>\n?")
HEAD = re.compile(r"<meta charset=[^>]*>\n?", re.I)


def policy(html: str) -> str:
    hashes = sorted({"'sha256-" + base64.b64encode(hashlib.sha256(m.encode("utf-8")).digest()).decode() + "'" for m in INLINE.findall(html)})
    return "; ".join([
        "default-src 'none'",
        "script-src 'self' " + " ".join(hashes) if hashes else "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",  # Diagramme setzen Formate direkt an den Elementen
        "img-src 'self' data: blob:",        # PNG-Download und Vorschaubilder entstehen im Browser
        "font-src 'self'",
        f"connect-src 'self' {FORM}",
        f"form-action 'self' {FORM}",
        "base-uri 'none'",
    ])


def apply(html: str) -> str:
    html = OLD.sub("", html)
    tag = f'{MARK} content="{policy(html)}">\n'
    if not HEAD.search(html):
        raise ValueError("kein <meta charset> gefunden")
    return HEAD.sub(lambda m: m.group(0) + tag, html, count=1)


def main(site: Path) -> int:
    n = 0
    for p in sorted(site.rglob("*.html")):
        p.write_text(apply(p.read_text(encoding="utf-8")), encoding="utf-8")
        n += 1
    return n


if __name__ == "__main__":
    print(f"Content-Security-Policy in {main(Path(sys.argv[1] if len(sys.argv) > 1 else 'site'))} Seiten eingetragen")
