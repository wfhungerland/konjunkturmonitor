#!/usr/bin/env bash
# Installiert den Konjunkturmonitor mit festgelegten, per Prüfsumme geprüften Paketen.
# 1. Fremdpakete aus requirements.txt; pip bricht ab, wenn eine Datei nicht zur Prüfsumme passt.
# 2. konjunkturwolf als fester Git-Commit aus pyproject.toml und der Monitor selbst, beide ohne weitere Paketauflösung.
# 3. pip check meldet, wenn in requirements.in ein Paket fehlt.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install --quiet --require-hashes -r requirements.txt
wolf=$(grep -o 'git+https://github.com/wfhungerland/konjunkturwolf@[0-9a-f]\{40\}' pyproject.toml)
python -m pip install --quiet --no-deps --no-build-isolation "konjunkturwolf @ $wolf"
python -m pip install --quiet --no-deps --no-build-isolation -e .
python -m pip check
