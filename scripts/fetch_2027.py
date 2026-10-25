#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Récupère les sondages de la présidentielle 2027 depuis la page Wikipédia
« Liste de sondages sur l'élection présidentielle française de 2027 »
et les écrit dans data/polls/2027.json (format commun à toutes les élections).

    .venv/bin/python scripts/fetch_2027.py            # télécharge la page
    .venv/bin/python scripts/fetch_2027.py --offline  # réutilise data/raw/wikipedia-2027.json
"""
import argparse
import datetime
import json
import sys

from common import ROOT
from wikipedia import download, parse_page

PAGE = "Liste de sondages sur l'élection présidentielle française de 2027"
RAW = ROOT / "data" / "raw" / "wikipedia-2027.json"
OUT = ROOT / "data" / "polls" / "2027.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    data = json.loads(RAW.read_text()) if args.offline else download(PAGE, RAW)
    first, second, events, problems = parse_page(data, 2027)

    out = {
        "election": 2027,
        "date_premier_tour": "2027-04-18",
        "date_second_tour": "2027-05-02",
        "source": f"https://fr.wikipedia.org/wiki/{PAGE.replace(' ', '_')}",
        "source_revision": data["parse"].get("revid"),
        "recupere_le": datetime.date.today().isoformat(),
        "licence": "CC BY-SA 4.0 — contributeurs de Wikipédia",
        "premier_tour": first,
        "second_tour": second,
        "evenements": events,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"premier tour : {len(first)} hypothèses, second tour : {len(second)} duels, "
          f"{len(events)} jalons -> {OUT.relative_to(ROOT)}")
    for p in problems:
        print("  !", p, file=sys.stderr)


if __name__ == "__main__":
    main()
