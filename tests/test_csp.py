"""Content-Security-Policy: nur die Skripte der Seite sind erlaubt."""
import base64
import hashlib

from monitor.csp import apply

PAGE = '<html><head>\n<meta charset="utf-8">\n<title>x</title></head><body><script>const A = 1;</script><script src="plotly.min.js"></script></body></html>'


def test_policy_names_exactly_the_inline_scripts():
    out = apply(PAGE)
    h = base64.b64encode(hashlib.sha256(b"const A = 1;").digest()).decode()
    assert f"script-src 'self' 'sha256-{h}';" in out and "'unsafe-inline'; img-src" in out  # unsafe-inline nur für Formate
    assert "default-src 'none'" in out and "connect-src 'self' https://formspree.io" in out
    assert out.index("Content-Security-Policy") < out.index("<script>")
    assert apply(out) == out                                           # erneuter Lauf ändert nichts
    assert apply(out.replace("A = 1", "A = 2")) != out                 # geändertes Skript, andere Prüfsumme
    assert "script-src 'self';" in apply(PAGE.replace("<script>const A = 1;</script>", ""))
