# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Les instituts de sondage :
- écart de chaque institut à la moyenne des autres pendant la campagne en cours
  (« effet maison ») ;
- précision passée : écart entre le dernier sondage de chaque institut et le
  résultat officiel du premier tour.
"""
import datetime
import re
import unicodedata
from collections import defaultdict

import numpy as np

from model import OTHERS, significant_candidates, scenario_key, to_date, window

# Un même institut sous plusieurs noms selon les sources et les époques
POLLSTERS = [
    (r"ifop", "Ifop"),
    (r"opinion\s*way", "OpinionWay"),
    (r"harris", "Harris Interactive"),
    (r"ipsos", "Ipsos"),
    (r"elabe", "Elabe"),
    (r"odoxa", "Odoxa"),
    (r"\bbva\b", "BVA"),
    (r"\bcsa\b", "CSA"),
    (r"yougov", "YouGov"),
    (r"cluster\s*17", "Cluster17"),
    (r"verian|kantar|sofres", "Verian (ex-Kantar Sofres)"),
    (r"louis harris", "Harris Interactive"),
]


def pollster_name(raw):
    low = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().lower()
    for pattern, name in POLLSTERS:
        if re.search(pattern, low):
            return name
    return raw.strip()


def shares_pct(row):
    total = sum(row["scores"].values())
    return {c: 100 * v / total for c, v in row["scores"].items()}


def house_effects(election, as_of, days=90, radius=21, min_rows=3, top=6):
    """
    Pour chaque hypothèse d'un institut, écart à la moyenne des hypothèses
    identiques (même scénario) publiées par les autres instituts à ± radius
    jours ; moyenne par institut et par candidat.
    """
    rows = window(election["premier_tour"], as_of, days)
    if not rows:
        return None
    significant = significant_candidates(rows)
    by_key = defaultdict(list)
    for r in rows:
        by_key[scenario_key(r, significant)].append(r)
    diffs = defaultdict(lambda: defaultdict(list))
    for key, group in by_key.items():
        for r in group:
            me = pollster_name(r["sondeur"])
            d0 = to_date(r["fin"])
            others = [o for o in group if pollster_name(o["sondeur"]) != me
                      and abs((to_date(o["fin"]) - d0).days) <= radius]
            if len({pollster_name(o["sondeur"]) for o in others}) < 2:
                continue  # consensus d'au moins deux autres instituts
            mine = shares_pct(r)
            theirs = [shares_pct(o) for o in others]
            for c in key:
                diffs[me][c].append(mine.get(c, 0) - np.mean([t.get(c, 0) for t in theirs]))
    means = defaultdict(list)
    for r in rows:
        for c, v in shares_pct(r).items():
            if c in significant:
                means[c].append(v)
    candidates = sorted(means, key=lambda c: -np.mean(means[c]))[:top]
    table = []
    for inst, per_cand in diffs.items():
        n = max((len(v) for v in per_cand.values()), default=0)
        if n < min_rows:
            continue
        table.append({"institut": inst, "n": n,
                      "ecarts": {c: round(float(np.mean(per_cand[c])), 2) if len(per_cand[c]) >= min_rows else None
                                 for c in candidates}})
    table.sort(key=lambda t: t["institut"])
    return {"depuis": (as_of - datetime.timedelta(days=days)).isoformat(), "candidats": candidates, "instituts": table}


def past_accuracy(elections, results, last_days=10, min_result=5.0):
    """Écart entre le dernier sondage de chaque institut avant le vote et le résultat du 1er tour."""
    out = {}
    for year, election in elections.items():
        res = results[str(year)]["premier_tour"]
        e1 = to_date(election["date_premier_tour"])
        latest = {}
        for r in election["premier_tour"]:
            d = to_date(r["fin"])
            if not (e1 - datetime.timedelta(days=last_days) <= d < e1):
                continue
            if sum(1 for c in res if c in r["scores"]) < len([c for c in res if res[c] >= min_result]):
                continue  # hypothèse sans tous les principaux candidats
            name = pollster_name(r["sondeur"])
            if name not in latest or r["fin"] >= latest[name]["fin"]:
                latest[name] = r
        per = {}
        for name, r in latest.items():
            sh = shares_pct(r)
            major = [c for c in res if res[c] >= min_result]
            err = {c: round(sh.get(c, 0) - res[c], 1) for c in major}
            per[name] = {"fin": r["fin"], "erreur_moyenne": round(float(np.mean([abs(v) for v in err.values()])), 2),
                         "ecarts": err}
        out[year] = {"principaux": sorted([c for c in res if res[c] >= min_result], key=lambda c: -res[c]),
                     "instituts": per}
    return out
