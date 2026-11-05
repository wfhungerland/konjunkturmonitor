"""Befehle: run (Daten holen und Seite bauen), build (nur Seite bauen)."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="konjunkturmonitor")
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Daten über die konjunkturwolf-Pipeline holen und die Seite bauen")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--only", nargs="*")
    sub.add_parser("build", help="Seite aus vorhandenen Daten bauen")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    root = Path(args.root).resolve()
    os.chdir(root)
    os.environ.setdefault("KONJUNKTURWOLF_STATIC_DIR", str(root / "data" / "static"))
    if args.cmd == "run":
        from .wetter import update_all

        update_all(root)  # Wetter und Rheinpegel als statische Reihen, vor dem Abruf
        from konjunkturwolf.catalog import load_catalog
        from konjunkturwolf.http import HttpClient
        from konjunkturwolf.pipeline import Paths, run, save

        paths = Paths(root)
        catalog = load_catalog(paths.catalog)
        result = run(catalog, paths, HttpClient(paths.cache, use_cache=not args.no_cache, offline=False), only=args.only)
        save(result, paths)
        logging.info("Daten: %s", ", ".join(f"{k}={v}" for k, v in sorted(result.counts().items())))
    from .build import build_site

    out = build_site(root)
    logging.info("Seite geschrieben: %s", out)
    return 0
