# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Modèle de D’après les sondages : agrégation bayésienne des sondages (Dirichlet-multinomiale)
puis simulation Monte-Carlo des deux tours.

Repris du modèle d'origine (2017) :
- a priori uniforme Dir(a, …, a) ;
- seul le dernier sondage de chaque institut compte, et l'ensemble des
  instituts pèse au plus D = 400 répondants « équivalents » le jour du vote
  (les sondages ne sont pas indépendants : en ajouter ne rend pas plus sûr) ;
- ce poids diminue avec l'éloignement du scrutin.

Adapté pour 2027 :
- le coefficient temporel est f(j) = 1 / (1 + (j / 60)^1,5), j = jours avant le
  vote. Il suit de près la droite d'origine (qui s'annulait 130 jours avant)
  sur les trois derniers mois, mais reste positif au-delà : on peut ainsi
  produire une prévision, très incertaine, un an avant l'élection ;
- les hypothèses de candidature sont regroupées automatiquement en
  « scénarios » (ensemble des candidats pesant au moins 4 %) ;
- les petits candidats sont regroupés dans « Autres », qui ne peut pas se
  qualifier pour le second tour ;
- l'a priori est affaibli (a = 0,25 au lieu de 1) : loin du scrutin, quand les
  sondages pèsent peu, un a priori de 1 ramènerait tous les candidats vers la
  même part et gonflerait artificiellement les petits. Le jour du vote, avec
  400 répondants équivalents, la différence est négligeable.
"""
import datetime
from collections import defaultdict

import numpy as np

from common import candidate_meta, short_name

LEFT = {"Extrême gauche", "Communiste", "Gauche radicale", "Socialiste", "Écologiste", "Divers gauche"}
FAR_RIGHT = {"Extrême droite"}

D = 400               # précision équivalente de l'ensemble des sondages le jour du vote
TAU = 60              # jours : poids divisé par deux à 60 jours du scrutin
WINDOW_FIRST = 60     # jours : sondages de 1er tour pris en compte
WINDOW_SECOND = 150   # jours : sondages de second tour pris en compte
SIGNIFICANT = 4.0     # % moyen minimal pour être modélisé individuellement
PRIOR = 0.25          # a priori de Dirichlet, par candidat
OTHERS = "Autres"


def to_date(s):
    return datetime.date.fromisoformat(s)


def time_coeff(days_before):
    return 1.0 / (1.0 + (max(days_before, 0) / TAU) ** 1.5)


def window(rows, as_of, days):
    lo = as_of - datetime.timedelta(days=days)
    return [r for r in rows if lo < to_date(r["fin"]) <= as_of]


def significant_candidates(rows):
    seen = defaultdict(list)
    for r in rows:
        total = sum(r["scores"].values())
        for c, v in r["scores"].items():
            if c != OTHERS:
                seen[c].append(100 * v / total)
    return {c for c, vals in seen.items() if np.mean(vals) >= SIGNIFICANT}


def scenario_key(row, significant):
    return frozenset(c for c in row["scores"] if c in significant)


def latest_per_institute(rows):
    """Dernier sondage de chaque institut ; plusieurs lignes du même sondage sont moyennées."""
    latest = {}
    for r in rows:
        k = r["sondeur"]
        if k not in latest or r["fin"] > latest[k][0]["fin"]:
            latest[k] = [r]
        elif r["fin"] == latest[k][0]["fin"]:
            latest[k].append(r)
    return list(latest.values())


def shares(row, candidates):
    """Parts (somme 1) sur candidates + Autres."""
    total = sum(row["scores"].values())
    p = np.array([row["scores"].get(c, 0.0) for c in candidates]) / total
    return np.append(p, max(0.0, 1 - p.sum()))


def dirichlet_alpha(groups, candidates, election_date, with_others=True):
    """Paramètres a posteriori : a priori + somme des parts pondérées (f · D / n_instituts)."""
    k = len(candidates) + (1 if with_others else 0)
    alpha = np.full(k, PRIOR)
    n = len(groups)
    for group in groups:
        p = np.mean([shares(r, candidates) for r in group], axis=0)
        if not with_others:
            p = p[:-1] / p[:-1].sum()
        f = time_coeff((election_date - to_date(group[0]["fin"])).days)
        alpha += (f * D / n) * p
    return alpha


class Duels:
    """Modèles de second tour (lois bêta) pour chaque paire de candidats."""

    def __init__(self, rows, as_of, election_date):
        self.models = {}
        by_pair = defaultdict(list)
        for r in window(rows, as_of, WINDOW_SECOND):
            by_pair[frozenset(r["scores"])].append(r)
        for pair, prs in by_pair.items():
            a, b = sorted(pair)
            groups = latest_per_institute(prs)
            alpha = dirichlet_alpha(groups, [a, b], election_date, with_others=False)
            self.models[pair] = {
                "a": a, "b": b, "alpha": alpha,
                "sondages": [g[0] for g in groups],
            }

    def get(self, x, y):
        m = self.models.get(frozenset((x, y)))
        if m is None:
            return None
        return m["alpha"] if m["a"] == x else m["alpha"][::-1]


def describe_scenarios(keys):
    """Libellé de chaque scénario par rapport au plus sondé (le premier)."""
    if not keys:
        return []
    ref = keys[0]
    labels = ["Scénario le plus sondé"]
    for k in keys[1:]:
        added = sorted((short_name(c) for c in k - ref))
        removed = sorted((short_name(c) for c in ref - k))
        parts = []
        if added:
            parts.append("avec " + join_fr(added))
        if removed:
            parts.append("sans " + join_fr(removed))
        label = ", ".join(parts) or "même liste"
        labels.append(label[:1].upper() + label[1:])
    return labels


def join_fr(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " et " + names[-1]


def find_scenarios(first_rows, as_of, max_scenarios=4):
    rows = window(first_rows, as_of, WINDOW_FIRST)
    if not rows:
        return []
    significant = significant_candidates(rows)
    by_key = defaultdict(list)
    for r in rows:
        key = scenario_key(r, significant)
        if len(key) >= 2:
            by_key[key].append(r)
    ranked = sorted(
        by_key.items(),
        key=lambda kv: (len({r["sondeur"] for r in kv[1]}), len(kv[1]), max(r["fin"] for r in kv[1])),
        reverse=True,
    )
    return ranked[:max_scenarios]


def simulate(candidates, alpha, duels, n, rng):
    """Tire n élections. Renvoie les statistiques par candidat et par duel."""
    m = len(candidates)
    theta = rng.dirichlet(alpha, size=n)[:, :m]  # « Autres » ne peut pas se qualifier
    order = np.argsort(-theta, axis=1)
    first, second = order[:, 0], order[:, 1]
    rows = np.arange(n)
    winner = np.full(n, -1)
    majority = theta[rows, first] > 0.5
    winner[majority] = first[majority]

    lo, hi = np.minimum(first, second), np.maximum(first, second)
    pair_code = lo * m + hi
    winner_share = np.where(majority, theta[rows, first], np.nan)
    duo_stats = []
    for code in np.unique(pair_code[~majority]):
        i, j = divmod(int(code), m)
        mask = (pair_code == code) & ~majority
        ab = duels.get(candidates[i], candidates[j])
        polled = ab is not None
        if ab is None:
            ab = np.array([1.0, 1.0])
        p = rng.beta(ab[0], ab[1], size=mask.sum())
        winner[mask] = np.where(p > 0.5, i, j)
        winner_share[mask] = np.maximum(p, 1 - p)
        duo_stats.append({
            "a": candidates[i], "b": candidates[j],
            "p_duel": float(mask.mean()),
            "p_a_gagne": float((p > 0.5).mean()),
            "a_moyenne": float(100 * ab[0] / ab.sum()),
            "a_q05": float(100 * np.quantile(p, 0.05)),
            "a_q95": float(100 * np.quantile(p, 0.95)),
            "sonde": polled,
        })
    duo_stats.sort(key=lambda d: -d["p_duel"])

    q = np.quantile(theta, [0.05, 0.5, 0.95], axis=0) * 100
    stats = {}
    for k, c in enumerate(candidates):
        stats[c] = {
            "moyenne": float(100 * alpha[k] / alpha.sum()),
            "q05": float(q[0, k]), "q50": float(q[1, k]), "q95": float(q[2, k]),
            "p_premier": float((first == k).mean()),
            "p_qualifie": float(((first == k) | (second == k)).mean()),
            "p_victoire": float((winner == k).mean()),
        }
    stats[OTHERS] = {"moyenne": float(100 * alpha[-1] / alpha.sum())}
    questions = fun_questions(candidates, stats, theta, first, second, winner, winner_share)
    return stats, duo_stats, questions


def fun_questions(candidates, stats, theta, first, second, winner, winner_share):
    """Petites questions tirées des mêmes simulations que la prévision."""
    fam = [candidate_meta(c)["famille"] for c in candidates]
    is_left = np.array([f in LEFT for f in fam])
    is_far_right = np.array([f in FAR_RIGHT for f in fam])
    by_mean = sorted(range(len(candidates)), key=lambda k: -stats[candidates[k]]["moyenne"])
    name = lambda k: short_name(candidates[k])
    out = []

    if is_left.any():
        p = float((~is_left[first] & ~is_left[second]).mean())
        out.append({"id": "sans-gauche", "question": "Un second tour sans candidat de gauche ?", "p": p,
                    "detail": "Aucun candidat de gauche, d'extrême gauche ou écologiste parmi les deux finalistes."})
    if is_far_right.any():
        p = float((~is_far_right[first] & ~is_far_right[second]).mean())
        out.append({"id": "sans-ed", "question": "Un second tour sans l'extrême droite ?", "p": p,
                    "detail": "Aucun candidat d'extrême droite parmi les deux finalistes."})
    top = by_mean[0]
    threshold = 5 * round(stats[candidates[top]]["moyenne"] / 5)
    out.append({"id": "seuil", "question": f"{name(top)} au-dessus de {threshold} % au premier tour ?",
                "p": float((theta[:, top] > threshold / 100).mean()),
                "detail": f"Score attendu : {stats[candidates[top]]['moyenne']:.1f} %.".replace(".", ",", 1)})
    out.append({"id": "renversement", "question": "Le candidat arrivé en tête du premier tour battu au second ?",
                "p": float(((winner != first) & (winner >= 0)).mean()),
                "detail": "C'est arrivé en 1974, 1981 et 1995."})
    gap = np.sort(theta, axis=1)[:, ::-1]
    out.append({"id": "photo-finish", "question": "Moins d'un point entre le 2e et le 3e du premier tour ?",
                "p": float((gap[:, 1] - gap[:, 2] < 0.01).mean()),
                "detail": "Une qualification pour le second tour jouée à moins d'un point."})
    out.append({"id": "large", "question": "Un président élu avec plus de 55 % des voix ?",
                "p": float((winner_share > 0.55).mean()),
                "detail": "Au second tour, en suffrages exprimés."})
    if len(by_mean) >= 3:
        a, b = by_mean[1], by_mean[2]
        out.append({"id": "duel-seconds", "question": f"{name(a)} devant {name(b)} au premier tour ?",
                    "p": float((theta[:, a] > theta[:, b]).mean()),
                    "detail": "Les deux candidats qui suivent le favori dans les intentions de vote."})
    return out


def forecast(election, as_of, n=200_000, seed=1958, max_scenarios=4, n_other=None, exclude=()):
    """Prévision complète à la date as_of : un bloc par scénario de candidatures."""
    e1, e2 = to_date(election["date_premier_tour"]), to_date(election["date_second_tour"])
    rng = np.random.default_rng(seed)
    if exclude:  # sondages retirés (« sondage de la semaine »), repérés par (institut, fin d'enquête)
        keep = lambda r: (r["sondeur"], r["fin"]) not in exclude
        election = dict(election, premier_tour=[r for r in election["premier_tour"] if keep(r)],
                        second_tour=[r for r in election["second_tour"] if keep(r)])
    duels = Duels(election["second_tour"], as_of, e2)
    ranked = find_scenarios(election["premier_tour"], as_of, max_scenarios)
    labels = describe_scenarios([k for k, _ in ranked]) if ranked else []
    scenarios = []
    for idx, ((key, rows), label) in enumerate(zip(ranked, labels)):
        groups = latest_per_institute(rows)
        candidates = sorted(key)
        alpha = dirichlet_alpha(groups, candidates, e1)
        stats, duos, questions = simulate(candidates, alpha, duels, n if idx == 0 or not n_other else n_other, rng)
        scenarios.append({
            "libelle": label,
            "cle": candidates,
            "questions": questions,
            "candidats": sorted(candidates, key=lambda c: -stats[c]["p_victoire"]),
            "stats": stats,
            "duels": duos,
            "n_hypotheses": len(rows),
            "instituts": sorted({r["sondeur"] for r in rows}),
            "sondages_retenus": [
                {"sondeur": g[0]["sondeur"], "fin": g[0]["fin"], "source": g[0].get("source"),
                 "lignes": len(g), "poids": round(time_coeff((e1 - to_date(g[0]["fin"])).days), 3)}
                for g in sorted(groups, key=lambda g: g[0]["fin"], reverse=True)
            ],
            "concentration": float(alpha.sum()),
        })
    return {
        "date": as_of.isoformat(),
        "jours_avant_premier_tour": (e1 - as_of).days,
        "scenarios": scenarios,
        "duels_sondes": [
            {"a": m["a"], "b": m["b"], "a_moyenne": float(100 * m["alpha"][0] / m["alpha"].sum()),
             "n_instituts": len(m["sondages"]), "dernier": max(r["fin"] for r in m["sondages"])}
            for m in duels.models.values()
        ],
    }


def timeline(election, start, end, step_days=7, n=20_000):
    """Évolution de la prévision du scénario principal, une date par semaine."""
    points = []
    day = end
    dates = []
    while day >= start:
        dates.append(day)
        day -= datetime.timedelta(days=step_days)
    for d in reversed(dates):
        fc = forecast(election, d, n=n, max_scenarios=1)
        if not fc["scenarios"]:
            continue
        sc = fc["scenarios"][0]
        points.append({
            "date": d.isoformat(),
            "victoire": {c: round(s["p_victoire"], 4) for c, s in sc["stats"].items() if c != OTHERS},
            "qualifie": {c: round(s["p_qualifie"], 4) for c, s in sc["stats"].items() if c != OTHERS},
            "premier_tour": {c: [round(s["q05"], 2), round(s["moyenne"], 2), round(s["q95"], 2)]
                             for c, s in sc["stats"].items() if c != OTHERS},
        })
    return points
