#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Récupère les sondages de la présidentielle 2027 depuis la page Wikipédia
« Liste de sondages sur l'élection présidentielle française de 2027 »
et les écrit dans data/polls/2027.json (format commun à toutes les élections).

Les sondages publiés mais pas encore repris par Wikipédia sont relevés dans
leur notice officielle (Commission des sondages) et saisis dans
data/polls/2027-ajouts.json ; ils sont ajoutés tant que Wikipédia ne les a pas.

    .venv/bin/python scripts/fetch_2027.py            # télécharge la page
    .venv/bin/python scripts/fetch_2027.py --offline  # réutilise data/raw/wikipedia-2027.json
"""
import argparse
import datetime
import json
import re
import sys

from common import CANDIDATES, ROOT, canonical_name
from model import OTHERS
from pollsters import pollster_name
from wikipedia import download, parse_page

PAGE = "Liste de sondages sur l'élection présidentielle française de 2027"
RAW = ROOT / "data" / "raw" / "wikipedia-2027.json"
OUT = ROOT / "data" / "polls" / "2027.json"
ADDITIONS = ROOT / "data" / "polls" / "2027-ajouts.json"


def notice_number(url):
    """Numéro de notice dans une adresse de la Commission des sondages (…/10339-pres-iv-….pdf)."""
    m = re.search(r"/(\d{4,6})-[a-z]", url or "")
    return int(m.group(1)) if m else None


def merge_additions(first, second):
    """
    Ajoute les sondages relevés dans les notices officielles que Wikipédia n'a
    pas encore. Un sondage déjà sur Wikipédia (même notice, ou même institut et
    mêmes dates) est ignoré : la version de Wikipédia fait foi.
    """
    additions = json.loads(ADDITIONS.read_text())["sondages"]
    on_wiki = {notice_number(r.get("source")) for r in first + second} - {None}
    same_poll = {(pollster_name(r["sondeur"]), r["debut"], r["fin"]) for r in first + second}
    included, covered = [], []
    for s in additions:
        if s["notice"] in on_wiki or (pollster_name(s["sondeur"]), s["debut"], s["fin"]) in same_poll:
            covered.append(s["notice"])
            continue
        base = {"sondeur": s["sondeur"], "debut": s["debut"], "fin": s["fin"], "echantillon": s.get("echantillon"),
                "source": s["notice_url"], "origine": "ajout", "notice": s["notice"]}
        for kind, rows in (("premier_tour", first), ("second_tour", second)):
            for h in s.get(kind, []):
                scores = {canonical_name(c): v for c, v in h["scores"].items()}
                unknown = [c for c in scores if c not in CANDIDATES and c != OTHERS]
                total = sum(scores.values())
                if unknown or not 90 <= total <= 110:
                    raise ValueError(f"{ADDITIONS.name}, notice {s['notice']} : "
                                     + (f"candidat inconnu {unknown} (nom complet attendu)" if unknown
                                        else f"total de {total:g} %"))
                label = f"Ajout, notice n° {s['notice']}" + (f" : {h['hypothese']}" if h.get("hypothese") else "")
                rows.append(base | {"scores": scores, "section": label, "total_brut": round(total, 2)})
        included.append(s["notice"])
    first.sort(key=lambda r: r["fin"])
    second.sort(key=lambda r: r["fin"])
    return included, covered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    data = json.loads(RAW.read_text()) if args.offline else download(PAGE, RAW)
    first, second, events, problems = parse_page(data, 2027)
    included, covered = merge_additions(first, second)

    out = {
        "election": 2027,
        "date_premier_tour": "2027-04-18",
        "date_second_tour": "2027-05-02",
        "source": f"https://fr.wikipedia.org/wiki/{PAGE.replace(' ', '_')}",
        "source_revision": data["parse"].get("revid"),
        "recupere_le": datetime.date.today().isoformat(),
        "licence": "CC BY-SA 4.0 — contributeurs de Wikipédia",
        "ajouts": {"fichier": str(ADDITIONS.relative_to(ROOT)), "inclus": included, "deja_sur_wikipedia": covered},
        "premier_tour": first,
        "second_tour": second,
        "evenements": events,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"premier tour : {len(first)} hypothèses, second tour : {len(second)} duels, "
          f"{len(events)} jalons -> {OUT.relative_to(ROOT)}")
    if included or covered:
        print(f"ajouts : {len(included)} sondage(s) inclus, {len(covered)} déjà sur Wikipédia (ignorés)")
    for p in problems:
        print("  !", p, file=sys.stderr)


if __name__ == "__main__":
    main()
