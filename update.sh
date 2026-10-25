#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
# Récupère les derniers sondages 2027 et régénère le site.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { uv venv --python 3.13 -q && uv pip install -q -r pyproject.toml; }
.venv/bin/python scripts/fetch_2027.py
.venv/bin/python scripts/eurobarometer.py >/dev/null || echo "Eurobaromètre : mise à jour impossible, données précédentes conservées"
.venv/bin/python scripts/build.py "$@"
