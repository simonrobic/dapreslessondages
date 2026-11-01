#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Contrôle : les sondages d'intentions de vote de la présidentielle déposés à la
Commission des sondages (notices « Pres IV ») sont-ils tous dans nos données ?

Une notice est couverte si son numéro apparaît dans la source d'un sondage de
data/polls/2027.json (Wikipédia ou ajout), ou si elle figure dans
« notices_deja_reprises » de data/polls/2027-ajouts.json (même sondage repris
par Wikipédia sous un autre lien).

    .venv/bin/python scripts/notices.py           # liste les notices manquantes
    .venv/bin/python scripts/notices.py --json    # idem, en JSON (avec l'adresse du PDF)
    .venv/bin/python scripts/notices.py --github  # avertissements pour GitHub Actions
"""
import argparse
import json
import re
import urllib.request

from bs4 import BeautifulSoup

from common import ROOT
from fetch_2027 import ADDITIONS, OUT, notice_number

SITE = "https://www.commission-des-sondages.fr"
LIST = SITE + "/notices/"
UA = {"User-Agent": "dapreslessondages/1.0 (+https://dapreslessondages.fr)"}
FIRST = 10200  # notices antérieures : avant la page Wikipédia actuelle, déjà contrôlées


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.geturl(), r.read()


def voting_intention_notices():
    """(numéro, libellé, lien) des notices d'intentions de vote à la présidentielle."""
    _, html = fetch(LIST)
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=re.compile(r"fichiers/add/\d+")):
        text = " ".join(a.get_text(" ").split())
        m = re.match(r"(\d{5}) Pres IV (.*)", text)
        if m and int(m.group(1)) >= FIRST:
            out.append((int(m.group(1)), m.group(2), SITE + a["href"]))
    return sorted(out)


def covered():
    data = json.loads(OUT.read_text())
    known = {notice_number(r.get("source")) for r in data["premier_tour"] + data["second_tour"]}
    additions = json.loads(ADDITIONS.read_text())
    known |= {s["notice"] for s in additions["sondages"]}
    known |= {int(n) for n in additions.get("notices_deja_reprises", {})}
    return known - {None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--github", action="store_true")
    args = ap.parse_args()
    notices = voting_intention_notices()
    known = covered()
    missing = []
    for number, label, link in notices:
        if number in known:
            continue
        pdf, _ = fetch(link)  # le lien de la liste redirige vers le PDF de la notice
        missing.append({"notice": number, "libelle": label, "pdf": pdf})
    if args.json:
        print(json.dumps(missing, ensure_ascii=False, indent=1))
    elif args.github:
        for m in missing:
            print(f"::warning::Notice {m['notice']} ({m['libelle']}) absente des données : {m['pdf']}")
    else:
        print(f"{len(notices)} notices d'intentions de vote depuis la n° {FIRST}, {len(missing)} absente(s) des données")
        for m in missing:
            print(f"  {m['notice']} · {m['libelle']} · {m['pdf']}")


if __name__ == "__main__":
    main()
