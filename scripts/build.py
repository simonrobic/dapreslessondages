#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Calcule les prévisions et génère le site statique dans site/.

    .venv/bin/python scripts/build.py              # tout
    .venv/bin/python scripts/build.py --quick      # moins de tirages (aperçu rapide)
    .venv/bin/python scripts/build.py --today 2026-10-24
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import random
import shutil
import urllib.parse

from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import ROOT, assign_slots, candidate_meta, date_fr, short_name
import share_image
from pollsters import house_effects, past_accuracy
from model import OTHERS, forecast, timeline, to_date, time_coeff, D, PRIOR, TAU, WINDOW_FIRST, WINDOW_SECOND, SIGNIFICANT

SITE_NAME = "D’après les sondages"
SITE_URL = "https://dapreslessondages.fr/"

# Adresse publique du code de cette version (licence AGPL : le code doit rester
# accessible aux visiteurs). Sur GitHub Actions, c'est l'adresse du dépôt qui
# construit le site ; sinon la variable SOURCE_CODE, à défaut le dépôt public.
SOURCE_CODE = os.environ.get("SOURCE_CODE") or (
    f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}"
    if os.environ.get("GITHUB_REPOSITORY") else "https://github.com/simonrobic/dapreslessondages")

SITE = ROOT / "site"
TEMPLATES = ROOT / "templates"
YEARS = [1965, 1969, 1974, 1981, 1988, 1995, 2002, 2007, 2012, 2017, 2022]
CURRENT = 2027
MAX_SCENARIOS = 30
ACCURACY_YEARS = [2007, 2012, 2017, 2022]  # précision passée des instituts
COMPARE = [2022, 2017, 2012]   # élections comparées « au même stade » sur la page d'accueil
STAGES = [120, 90, 60, 30, 1]  # étapes de la page « Au même stade », en plus d'aujourd'hui
BOOTSTRAP = 2000  # tirages pour la fourchette du score d'alignement des candidats

# Élections sans campagne comparable : 1958 au suffrage indirect, 1969 et 1974 anticipées
ELECTION_1958 = {"annee": 1958, "date_premier_tour": "1958-12-21", "elu": "Charles de Gaulle",
                 "note": "Élu par un collège d'environ 80 000 grands électeurs, avec 78,51 % des voix : "
                         "pas de campagne au suffrage universel, ni de sondage."}
EARLY_ELECTIONS = {
    1969: ("1969-04-28", "Élection anticipée après la démission du général de Gaulle, le 28 avril 1969 : "
                         "à ce stade, elle n'était pas prévue."),
    1974: ("1974-04-02", "Élection anticipée après la mort de Georges Pompidou, le 2 avril 1974 : "
                         "à ce stade, elle n'était pas prévue."),
}

def pct(p, digits=0):
    """Probabilité -> « 83 % », avec « < 1 % » et « > 99 % » aux extrêmes."""
    v = 100 * p
    if 0 < v < 1:
        return "< 1 %"
    if 99 < v < 100:
        return "> 99 %"
    return f"{v:.{digits}f} %".replace(".", ",")


def num(v, digits=1):
    return f"{v:.{digits}f}".replace(".", ",")


def load(year):
    return json.loads((ROOT / "data" / "polls" / f"{year}.json").read_text())


def round_stats(stats):
    out = {}
    for c, s in stats.items():
        out[c] = {k: round(v, 4 if k.startswith("p_") else 2) for k, v in s.items()}
    return out


def election_payload(year, election, as_of, results, n, n_timeline):
    e1 = to_date(election["date_premier_tour"])
    # Élection en cours : tous les scénarios sondés (« Composez votre scénario »)
    fc = forecast(election, as_of, n=n, max_scenarios=1 if results else MAX_SCENARIOS, n_other=n * 2 // 5)
    start = max(to_date(election["premier_tour"][0]["fin"]), e1 - datetime.timedelta(days=200))
    if year == CURRENT:
        start = datetime.date(2025, 1, 5)
    tl = timeline(election, start, as_of, n=n_timeline)

    # Importance de chaque candidat : sert à l'ordre et aux couleurs
    importance, best_share = {}, {}
    for sc in fc["scenarios"]:
        for c, s in sc["stats"].items():
            if c == OTHERS:
                continue
            importance[c] = max(importance.get(c, 0), s["p_victoire"] + s["moyenne"] / 100)
            best_share[c] = max(best_share.get(c, 0), s["moyenne"])
    for pt in tl:
        for c, v in pt["victoire"].items():
            importance[c] = max(importance.get(c, 0), v + pt["premier_tour"][c][1] / 100)
            best_share[c] = max(best_share.get(c, 0), pt["premier_tour"][c][1])
    if results:
        for c, v in results["premier_tour"].items():
            importance[c] = max(importance.get(c, 0), v / 100)
            best_share[c] = max(best_share.get(c, 0), v)
    # Les candidats de la prévision actuelle passent avant ceux qui ne figurent
    # que dans l'historique de la courbe (ils choisissent leur couleur en premier)
    in_forecast = {c for sc in fc["scenarios"] for c in sc["candidats"]}
    ranked = sorted(importance, key=lambda c: (c not in in_forecast, -importance[c]))
    groups = [[c for c in ranked if c in in_forecast], [c for c in ranked if c not in in_forecast]]
    minor = {c for c in ranked if best_share[c] < 5}
    pairs = set()
    for r in election["premier_tour"]:
        names = sorted(r["scores"])
        pairs.update((a, b) for i, a in enumerate(names) for b in names[i + 1:])
    slots = assign_slots(groups, minor, lambda a, b: (min(a, b), max(a, b)) in pairs)
    candidates = {}
    for c in ranked:
        meta = candidate_meta(c, year)
        candidates[c] = {"court": short_name(c), "parti": meta["parti"], "famille": meta["famille"],
                         "ordre": meta["ordre"], "slot": slots[c]}

    # Sondages bruts (points du graphique) : parts en % des exprimés
    polls = []
    for r in election["premier_tour"]:
        if to_date(r["fin"]) < start - datetime.timedelta(days=WINDOW_FIRST) or to_date(r["fin"]) > as_of:
            continue
        total = sum(r["scores"].values())
        polls.append({"d": r["fin"], "i": r["sondeur"],
                      "s": {c: round(100 * v / total, 1) for c, v in r["scores"].items()
                            if c in candidates}})

    scenarios = []
    for sc in fc["scenarios"]:
        scenarios.append({
            "libelle": sc["libelle"],
            "candidats": sc["candidats"],
            "stats": round_stats(sc["stats"]),
            "duels": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
                      for d in sc["duels"] if d["p_duel"] >= 0.005][:6],
            "cle": sc["cle"],
            "questions": [dict(q, p=round(q["p"], 4)) for q in sc["questions"]],
            "n_hypotheses": sc["n_hypotheses"],
            "instituts": sc["instituts"],
            "sondages_retenus": sc["sondages_retenus"],
            "concentration": round(sc["concentration"], 1),
        })

    return {
        "annee": year,
        "passee": results is not None,
        "date_premier_tour": election["date_premier_tour"],
        "date_second_tour": election["date_second_tour"],
        "date_prevision": as_of.isoformat(),
        "jours_avant": (e1 - as_of).days,
        "candidats": candidates,
        "scenarios": scenarios,
        "timeline": tl,
        "sondages": polls,
        "evenements": [e for e in election.get("evenements", []) if start.isoformat() <= e["date"] <= as_of.isoformat()],
        "resultats": results,
        "n_simulations": n,
        "n_sondages": len({(r["sondeur"], r["fin"]) for r in election["premier_tour"]}),
        "n_hypotheses": len(election["premier_tour"]),
        "n_duels": len(election["second_tour"]),
        "source": election.get("source"),
        "licence": election.get("licence"),
        "sources": election.get("sources") or [{"url": election.get("source"), "licence": election.get("licence")}],
        "wiki": wiki_attribution(election),
    }


def stage_snapshot(year, election, results, days_before, n):
    """Ce que donnait le modèle à J-days_before, et ce qui s'est passé ensuite."""
    e1 = to_date(election["date_premier_tour"])
    as_of = e1 - datetime.timedelta(days=days_before)
    early = EARLY_ELECTIONS.get(year)
    if early and as_of.isoformat() < early[0]:
        return {"date": as_of.isoformat(), "absence": early[1]}
    fc = forecast(election, as_of, n=n, max_scenarios=1)
    if not fc["scenarios"]:
        return {"date": as_of.isoformat(), "absence": "Aucun sondage publié à ce stade de la campagne."}
    sc = fc["scenarios"][0]
    fav = sc["candidats"][0]
    elected = max(results["second_tour"], key=results["second_tour"].get)
    first_round = sorted(results["premier_tour"], key=lambda c: -results["premier_tour"][c])
    if fav == elected:
        issue = "gagne"
    elif fav not in results["premier_tour"]:
        issue = "absent"
    elif fav in results["second_tour"]:
        issue = "battu"
    else:
        issue = "elimine"
    return {
        "date": as_of.isoformat(),
        "favori": fav, "p_favori": round(sc["stats"][fav]["p_victoire"], 4),
        "p_elu": round(sc["stats"][elected]["p_victoire"], 4) if elected in sc["stats"] else None,
        "issue": issue,
        "rang_favori": first_round.index(fav) + 1 if fav in first_round else None,
        "n_hypotheses": sc["n_hypotheses"], "instituts": sc["instituts"],
    }


def stage_curve(election, days_from, names, n_timeline):
    """Chances de victoire de quelques candidats, chaque semaine jusqu'à la veille du vote."""
    e1 = to_date(election["date_premier_tour"])
    tl = timeline(election, e1 - datetime.timedelta(days=days_from), e1 - datetime.timedelta(days=1), n=n_timeline)
    return {"j": [(e1 - to_date(pt["date"])).days for pt in tl],
            "series": {c: [pt["victoire"].get(c) for pt in tl] for c in names}}


def same_stage_entries(past, results, days_now, n, n_timeline):
    """Toutes les élections depuis 1958, à aujourd'hui et aux étapes STAGES."""
    stages = sorted({days_now, *[st for st in STAGES if abs(st - days_now) > 10]}, reverse=True)
    entries = [dict(ELECTION_1958, indirect=True,
                    candidats={ELECTION_1958["elu"]: {"court": short_name(ELECTION_1958["elu"]),
                                                      "slot": candidate_meta(ELECTION_1958["elu"])["slot"]}})]
    for year in YEARS:
        election, payload = past[year]
        res = results[str(year)]
        elected = max(res["second_tour"], key=res["second_tour"].get)
        snaps = {st: stage_snapshot(year, election, res, st, n) for st in stages}
        names = [elected] + [sn["favori"] for sn in snaps.values() if "favori" in sn]
        names = list(dict.fromkeys(names))
        meta = {c: {"court": payload["candidats"].get(c, {}).get("court", short_name(c)),
                    "slot": payload["candidats"].get(c, {}).get("slot", candidate_meta(c)["slot"])} for c in names}
        entries.append({
            "annee": year,
            "date_premier_tour": election["date_premier_tour"],
            "elu": elected,
            "candidats": meta,
            "etapes": snaps,
            "courbe": stage_curve(election, max(days_now + 35, 200), names, n_timeline),
        })
    return stages, entries


def poll_of_the_week(election, payload, as_of, week_polls, n):
    """
    Pour chaque sondage de la semaine, la prévision recalculée sans lui (mêmes
    tirages aléatoires) ; on retient celui dont le retrait la change le plus.
    """
    main = payload["scenarios"][0]
    key = set(main["cle"])
    base = forecast(election, as_of, n=n, max_scenarios=MAX_SCENARIOS)
    base_sc = next((sc for sc in base["scenarios"] if set(sc["cle"]) == key), None)
    if base_sc is None:
        return None
    best = None
    for poll in week_polls:
        fc = forecast(election, as_of, n=n, max_scenarios=MAX_SCENARIOS, exclude={poll})
        sc = next((x for x in fc["scenarios"] if set(x["cle"]) == key), None)
        if sc is None:
            continue
        diffs = {c: base_sc["stats"][c]["p_victoire"] - sc["stats"][c]["p_victoire"] for c in key}
        top = max(diffs, key=lambda c: abs(diffs[c]))
        if best is None or abs(diffs[top]) > abs(best["effet"]):
            rows = [r for r in election["premier_tour"] if (r["sondeur"], r["fin"]) == poll
                    and set(r["scores"]) >= key]
            hyp = rows[0] if rows else None
            best = {
                "sondeur": poll[0], "fin": poll[1], "candidat": top, "effet": round(diffs[top], 4),
                "avec": round(base_sc["stats"][top]["p_victoire"], 4),
                "sans": round(sc["stats"][top]["p_victoire"], 4),
                "source": hyp.get("source") if hyp else None,
                "hypothese": None if hyp is None else sorted(
                    ((c, v) for c, v in hyp["scores"].items() if c in key), key=lambda cv: -cv[1]),
            }
    return best


def weekly_changes(election, payload, as_of, n_poll=150_000):
    """Ce qui a changé depuis la prévision de la semaine dernière."""
    tl = payload["timeline"]
    if len(tl) < 2:
        return None
    before = tl[-2]
    sc = payload["scenarios"][0]
    since = to_date(before["date"])
    rows = []
    for c in sc["candidats"][:5]:
        now_p, now_s = sc["stats"][c]["p_victoire"], sc["stats"][c]["moyenne"]
        was_p = before["victoire"].get(c)
        was_s = before["premier_tour"].get(c, [None, None])[1]
        rows.append({"nom": c, "p": now_p, "dp": None if was_p is None else now_p - was_p,
                     "s": now_s, "ds": None if was_s is None else now_s - was_s})
    polls = {}
    for r in election["premier_tour"] + election["second_tour"]:
        if since < to_date(r["fin"]) <= as_of:
            polls.setdefault((r["sondeur"], r["fin"]), r.get("source"))
    events = [e for e in election.get("evenements", []) if since.isoformat() < e["date"] <= as_of.isoformat()]
    return {
        "sondage_semaine": poll_of_the_week(election, payload, as_of, list(polls), n_poll),
        "depuis": since.isoformat(),
        "candidats": rows,
        "sondages": [{"sondeur": k[0], "fin": k[1], "source": v} for k, v in sorted(polls.items(), key=lambda kv: kv[0][1], reverse=True)],
        "evenements": events,
        "scenario_change": set(before["victoire"]) != {c for c in sc["stats"] if c != OTHERS},
    }


def delta(v, unit_scale=100, threshold=0.5, digits=0):
    """« +2 pts », « −0,6 pt », « = » : écart en points, signe typographique."""
    if v is None:
        return "nouveau"
    x = v * unit_scale
    if abs(x) < threshold:
        return "="
    txt = f"{abs(x):.{digits}f}".replace(".", ",")
    return f"{'+' if x > 0 else '−'}{txt} pt{'s' if abs(x) >= 2 else ''}"


def wiki_attribution(election):
    """Lien vers la page Wikipédia source et vers son historique (liste des auteurs)."""
    for src in election.get("sources") or [{"url": election.get("source")}]:
        url = src.get("url") or ""
        if "wikipedia.org/wiki/" in url:
            title = url.split("/wiki/", 1)[1]
            return {"url": url, "historique": "https://fr.wikipedia.org/w/index.php?"
                    + urllib.parse.urlencode({"title": title, "action": "history"})}
    return None


def signed(v, digits=1):
    """« +1,4 », « −0,8 », « 0,0 » (signe typographique)."""
    txt = f"{abs(v):.{digits}f}".replace(".", ",")
    return txt if round(v, digits) == 0 else ("+" if v > 0 else "−") + txt


def concerns_payload(stages, days_now, results, slots):
    """
    Page « Préoccupations » : à chaque stade de la campagne, la dernière vague
    de l'Eurobaromètre publiée, et la place des mêmes thèmes dans la profession
    de foi du futur élu.
    """
    eb = json.loads((ROOT / "data" / "preoccupations" / "eurobarometre-france.json").read_text())
    pf = json.loads((ROOT / "data" / "programmes" / "professions-de-foi.json").read_text())
    labels = pf["themes"]
    eb_keys = [t["cle"] for t in eb["themes"]]
    waves = sorted(eb["vagues"], key=lambda w: w["date"])
    docs = {d["annee"]: d for d in pf["documents"]}
    elections = json.loads((ROOT / "data" / "resultats.json").read_text())

    def wave_at(day):
        """Dernière vague dont le terrain était terminé à cette date (au plus un an avant)."""
        best = None
        for w in waves:
            end = to_date(w["date"])
            if end <= day and (day - end).days <= 365:
                best = w
        return best

    def programme_shares(parts):
        thematic = {k: v for k, v in parts.items() if k != "general"}
        total = sum(thematic.values())
        return {k: round(100 * v / total, 1) for k, v in thematic.items()}

    def alignment(concerns, prog):
        """
        Score d'alignement : les préoccupations ramenées à 100 (chaque Français en
        cite deux) et les propositions hors généralités, aussi sur 100 ; le score
        est la part commune aux deux répartitions, thème par thème.
        """
        total = sum(concerns.values())
        top3 = sorted(concerns, key=lambda k: -concerns[k])[:3]
        return {"alignement": round(sum(min(100 * v / total, prog.get(k, 0)) for k, v in concerns.items())),
                "top3": top3, "part_top3": round(sum(prog.get(k, 0) for k in top3))}

    cards = []
    years = sorted([int(y) for y in elections] + [CURRENT, 1958], reverse=True)
    for year in years:
        if year == 1958:
            cards.append({"annee": 1958, "elu": ELECTION_1958["elu"], "note": ELECTION_1958["note"], "etapes": {}})
            continue
        e1 = to_date(load(year)["date_premier_tour"]) if year != 1958 else None
        res = results.get(str(year))
        elected = max(res["second_tour"], key=res["second_tour"].get) if res else None
        doc = docs.get(year)
        prog = programme_shares(doc["parts"]) if doc else None
        card = {"annee": year, "elu": elected, "courante": year == CURRENT, "etapes": {}}
        if doc:
            card["programme"] = {"parts": prog, "parts_texte": doc["parts"], "mots": doc["mots"],
                                 "source": doc["source"], "passages": doc["passages"]}
        for st in stages:
            day = e1 - datetime.timedelta(days=st)
            w = wave_at(min(day, datetime.date.today()))
            if w is None:
                card["etapes"][st] = {"date": day.isoformat(),
                                      "absence": "Pas de mesure ouverte et comparable des préoccupations des Français "
                                                 "à cette date (l'Eurobaromètre ne pose la question que depuis 2003)."}
                continue
            concerns = {k: w["themes"][k] for k in eb_keys if k in w["themes"]}
            snap = {"date": day.isoformat(), "vague": w["vague"], "terrain": w["terrain"],
                    "preoccupations": concerns}
            if prog:
                snap |= alignment(concerns, prog)
            card["etapes"][st] = snap
        cards.append(card)

    # Résumé par stade : place moyenne des trois premières préoccupations dans le programme de l'élu
    summary = {}
    for st in stages:
        vals = [c["etapes"][st]["part_top3"] for c in cards if st in c["etapes"] and "part_top3" in c["etapes"][st]]
        rec = {c["annee"]: c["etapes"][st]["alignement"] for c in cards
               if st in c["etapes"] and "alignement" in c["etapes"][st]}
        summary[st] = {"n": len(vals), "part_top3": round(sum(vals) / len(vals)) if vals else None,
                       "alignement": round(sum(rec.values()) / len(rec)) if rec else None, "elus": rec}

    # Candidats 2027 : leurs textes programmatiques face à la dernière vague publiée
    cand = json.loads((ROOT / "data" / "programmes" / "candidats-2027.json").read_text())
    latest = wave_at(datetime.date.today())
    now = {k: latest["themes"][k] for k in eb_keys if k in latest["themes"]}
    rng = random.Random(CURRENT)
    candidates = []
    for c in cand["candidats"]:
        prog = programme_shares(c["parts"])
        # Sensibilité : on retire et double des passages au hasard (bootstrap) pour voir
        # combien le score tient à quelques passages. Ce tirage tire le score vers le
        # bas (une répartition plus heurtée recoupe moins) : on n'en garde que l'écart.
        draws = []
        for _ in range(BOOTSTRAP):
            words = {}
            for r in rng.choices(c["passages"], k=len(c["passages"])):
                words[r["theme"]] = words.get(r["theme"], 0) + r["mots"]
            if any(k != "general" for k in words):
                draws.append(alignment(now, programme_shares(words))["alignement"])
        draws.sort()
        a = alignment(now, prog)
        margin = int((draws[-len(draws) // 10] - draws[len(draws) // 10]) / 2 + 0.5)  # 8 tirages sur 10
        candidates.append({k: c[k] for k in ("candidat", "documents", "remarque", "collecte", "mots", "passages")}
                          | {"court": short_name(c["candidat"]), "slot": slots.get(c["candidat"], 0), "parts": prog,
                             "marge": margin, "fourchette": [max(0, a["alignement"] - margin),
                                                             min(100, a["alignement"] + margin)]} | a)
    candidates.sort(key=lambda c: -c["alignement"])

    series_keys = sorted(eb_keys, key=lambda k: -max(w["themes"].get(k, 0) for w in waves))[:8]
    return {
        "jours_avant": days_now,
        "etapes": stages,
        "themes": labels,
        "series": series_keys,
        "vagues": [{"vague": w["vague"], "date": w["date"], "terrain": w["terrain"],
                    "themes": {k: w["themes"].get(k) for k in eb_keys}} for w in waves],
        "elections": [{"annee": int(y), "date": r["date_premier_tour"]} for y, r in elections.items()
                      if int(y) >= 2005] + [{"annee": CURRENT, "date": load(CURRENT)["date_premier_tour"]}],
        "cartes": cards,
        "resume": summary,
        "candidats": {"vague": latest["vague"], "terrain": latest["terrain"], "date": latest["date"],
                      "preoccupations": now, "liste": candidates, "non_classes": cand["non_classes"],
                      # repère : un programme qui donnerait la même place à chaque thème
                      "parts_egales": alignment(now, {k: 100 / len(now) for k in now})["alignement"],
                      "methode": cand["methode"], "selection": cand["selection"]},
        "methode": pf["methode"],
        "question": eb["question"],
    }


def headline(payload):
    sc = payload["scenarios"][0]
    fav = sc["candidats"][0]
    p = sc["stats"][fav]["p_victoire"]
    return {"nom": fav, "court": payload["candidats"][fav]["court"], "p": p, "p_txt": pct(p)}


def write_open_data(year, election):
    """Export CSV au format du dépôt d'origine (une ligne par hypothèse)."""
    out = SITE / "donnees"
    out.mkdir(parents=True, exist_ok=True)
    for key, name in (("premier_tour", "premier-tour"), ("second_tour", "second-tour")):
        rows = election[key]
        names = sorted({c for r in rows for c in r["scores"]},
                       key=lambda c: (candidate_meta(c)["ordre"], c))
        with open(out / f"presidentielle-{year}-{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sondeur", "source", "date début", "date fin", "échantillon"] + names)
            for r in rows:
                w.writerow([r["sondeur"], r.get("source") or "", r["debut"], r["fin"], r.get("echantillon") or ""]
                           + [("" if c not in r["scores"] else f"{r['scores'][c]:g}") for c in names])


def polls_table(election, candidates):
    """Tableau des sondages 2027 (page Sondages) : candidats dans l'ordre gauche -> droite."""
    counts = {}
    for r in election["premier_tour"]:
        for c in r["scores"]:
            if c != OTHERS:
                counts[c] = counts.get(c, 0) + 1
    names = sorted([c for c, k in counts.items() if k >= 15 or c in candidates],
                   key=lambda c: (candidate_meta(c)["ordre"], c))
    rows = []
    for r in sorted(election["premier_tour"], key=lambda r: r["fin"], reverse=True):
        total = sum(r["scores"].values())
        others = sum(v for c, v in r["scores"].items() if c not in names)
        rows.append({
            "sondeur": r["sondeur"], "source": r.get("source"), "fin": r["fin"], "fin_txt": date_fr(r["fin"]),
            "echantillon": r.get("echantillon"),
            "valeurs": [None if c not in r["scores"] else r["scores"][c] for c in names],
            "autres": others,
            "total": total,
        })
    duels = []
    for r in sorted(election["second_tour"], key=lambda r: r["fin"], reverse=True):
        (a, va), (b, vb) = sorted(r["scores"].items(), key=lambda kv: -kv[1])
        duels.append({"sondeur": r["sondeur"], "source": r.get("source"), "fin_txt": date_fr(r["fin"]),
                      "a": a, "va": va, "b": b, "vb": vb})
    return names, rows, duels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--today", default=None)
    args = ap.parse_args()
    n, n_tl = (40_000, 5_000) if args.quick else (500_000, 30_000)
    today = to_date(args.today) if args.today else datetime.date.today()

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(date_fr=date_fr, pct=pct, num=num, delta=delta, signed=signed,
                       json=lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))

    # Le site est généré à côté, puis mis en place d'un coup : pas de page manquante
    # pendant la génération
    global SITE
    final = SITE
    SITE = ROOT / ".site-tmp"
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    shutil.copytree(TEMPLATES / "assets", SITE / "assets")  # feuille de style, script, polices (OFL)
    # Version des fichiers dans leur adresse : elle change dès que leur contenu change,
    # pour que les navigateurs ne gardent pas une ancienne feuille de style en cache
    assets_v = hashlib.sha1(b"".join((TEMPLATES / "assets" / f).read_bytes()
                                     for f in ("style.css", "charts.js", "consent.js"))).hexdigest()[:10]

    results = json.loads((ROOT / "data" / "resultats.json").read_text())
    nav = [("", "Prévision 2027"), ("meme-stade/", "Au même stade"), ("preoccupations/", "Préoccupations"),
           ("sondages/", "Sondages"), ("historique/", "Historique"),
           ("methodologie/", "Méthodologie"), ("a-propos/", "À propos")]

    pages = []
    # Image de partage commune à toutes les pages (générée avec la prévision du jour)
    og_image = f"{SITE_URL}partage/prevision-{CURRENT}.png?v={today.isoformat()}"

    def render(template, path, depth, **ctx):
        target = SITE / path
        target.parent.mkdir(parents=True, exist_ok=True)
        url = SITE_URL + path.removesuffix("index.html")
        pages.append(url)
        html = env.get_template(template).render(root="../" * depth, nav=nav, built=today.isoformat(), assets_v=assets_v,
                                                 site_name=SITE_NAME, canonical=url, og_image=og_image,
                                                 source_code=SOURCE_CODE, **ctx)
        target.write_text(html)

    # Historique
    (SITE / "donnees").mkdir(parents=True, exist_ok=True)
    record, past = [], {}
    for year in YEARS:
        election = load(year)
        eve = to_date(election["date_premier_tour"]) - datetime.timedelta(days=1)
        res = results[str(year)]
        pl = election_payload(year, election, eve, res, n, n_tl)
        past[year] = (election, pl)
        render("election.html", f"{year}/index.html", 1, p=pl, h=headline(pl), page="historique/")
        (SITE / "donnees" / f"prevision-{year}.json").write_text(json.dumps(pl, ensure_ascii=False))
        sc = pl["scenarios"][0]
        elected = max(res["second_tour"], key=res["second_tour"].get)
        finalists = sorted(res["second_tour"], key=lambda c: -res["second_tour"][c])
        predicted_duo = sc["duels"][0] if sc["duels"] else None
        record.append({
            "annee": year,
            "favori": sc["candidats"][0], "p_favori": sc["stats"][sc["candidats"][0]]["p_victoire"],
            "elu": elected, "p_elu": sc["stats"].get(elected, {}).get("p_victoire", 0.0),
            "favori_elu": sc["candidats"][0] == elected,
            "finalistes": finalists,
            "p_duel_reel": next((d["p_duel"] for d in sc["duels"] if {d["a"], d["b"]} == set(finalists)), 0.0),
            "duel_prevu": predicted_duo,
            "erreur_moyenne": sum(abs(sc["stats"][c]["moyenne"] - v) for c, v in res["premier_tour"].items()
                                  if c in sc["stats"]) / max(1, sum(1 for c in res["premier_tour"] if c in sc["stats"])),
            "candidats": pl["candidats"],
            "n_sondages": pl["n_sondages"],
        })
        print(f"{year} : favori {sc['candidats'][0]} {pct(record[-1]['p_favori'])}, élu {elected} ({pct(record[-1]['p_elu'])})")
    # Élection en cours
    current = load(CURRENT)
    as_of = min(today, to_date(current["date_premier_tour"]) - datetime.timedelta(days=1))
    payload = election_payload(CURRENT, current, as_of, None, n, n_tl)
    stages, stage_entries = same_stage_entries(past, results, payload["jours_avant"], n // 4, n_tl)
    payload["comparaisons"] = [e for y in COMPARE for e in stage_entries if e["annee"] == y]
    payload["semaine"] = weekly_changes(current, payload, as_of)
    share_image.make(payload, SITE_NAME, SITE_URL.split("//", 1)[1].strip("/"), SITE / "partage" / f"prevision-{CURRENT}.png")
    render("election.html", "index.html", 0, p=payload, h=headline(payload), page="")
    write_open_data(CURRENT, current)
    names, rows, duels = polls_table(current, payload["candidats"])
    slots = {c: payload["candidats"].get(c, {}).get("slot", 0) for c in names}
    pollster_stats = {"effets": house_effects(current, as_of),
                      "precision": past_accuracy({y: past[y][0] for y in ACCURACY_YEARS}, results)}
    (SITE / "donnees" / "instituts.json").write_text(json.dumps(pollster_stats, ensure_ascii=False))
    render("sondages.html", "sondages/index.html", 1, p=payload, names=names, rows=rows, duels=duels,
           inst=pollster_stats, accuracy_years=ACCURACY_YEARS,
           slots=slots, short={c: short_name(c) for c in names}, page="sondages/", source=current["source"],
           wiki=wiki_attribution(current),
           revision=current.get("source_revision"), recupere=current.get("recupere_le"))
    (SITE / "donnees" / f"prevision-{CURRENT}.json").write_text(json.dumps(payload, ensure_ascii=False))
    render("widget.html", "widget/index.html", 1, p=payload, h=headline(payload), page="", site_url=SITE_URL)
    render("integrer.html", "integrer/index.html", 1, p=payload, page="integrer/", site_url=SITE_URL)
    print(f"{CURRENT} : {headline(payload)['nom']} {headline(payload)['p_txt']} ({len(payload['timeline'])} semaines)")

    render("historique.html", "historique/index.html", 1, record=record, page="historique/")
    stage_payload = {"jours_avant": payload["jours_avant"], "etapes": stages, "elections": stage_entries,
                     "actuel": {"nom": headline(payload)["nom"], "p": headline(payload)["p"]}}
    render("meme-stade.html", "meme-stade/index.html", 1, page="meme-stade/", sp=stage_payload,
           h=headline(payload), p=payload)
    (SITE / "donnees" / "meme-stade.json").write_text(json.dumps(stage_payload, ensure_ascii=False))
    concerns = concerns_payload(stages, payload["jours_avant"], results,
                                {c: v["slot"] for c, v in payload["candidats"].items()})
    render("preoccupations.html", "preoccupations/index.html", 1, page="preoccupations/", pp=concerns)
    (SITE / "donnees" / "preoccupations.json").write_text(json.dumps(
        {k: v for k, v in concerns.items() if k != "cartes"} | {"cartes": [
            {k: v for k, v in c.items() if k != "programme"} | (
                {"programme": {k2: v2 for k2, v2 in c["programme"].items() if k2 != "passages"}} if "programme" in c else {})
            for c in concerns["cartes"]]}, ensure_ascii=False))
    render("methodologie.html", "methodologie/index.html", 1, page="methodologie/",
           params={"D": D, "PRIOR": PRIOR, "TAU": TAU, "WINDOW_FIRST": WINDOW_FIRST, "WINDOW_SECOND": WINDOW_SECOND,
                   "SIGNIFICANT": SIGNIFICANT},
           decay=[(d, time_coeff(d)) for d in (0, 30, 60, 90, 130, 180, 270, 365)])
    render("apropos.html", "a-propos/index.html", 1, page="a-propos/")
    # Licences des fichiers téléchargeables, à côté des fichiers
    licence_txt = (ROOT / "data" / "LICENCE.md").read_text() + "\n\n---\n\n" + (
        ROOT / "data" / "raw" / "nsppolls" / "LICENCE.md").read_text()
    (SITE / "donnees" / "LICENCES.md").write_text(licence_txt)
    files = sorted((f.name, f"{max(1, round(f.stat().st_size / 1024))} Ko")
                   for f in (SITE / "donnees").iterdir() if f.suffix in (".csv", ".json", ".md"))
    render("donnees.html", "donnees/index.html", 1, page="donnees/", files=files)

    # Domaine (GitHub Pages), référencement
    domain = SITE_URL.split("//", 1)[1].strip("/")
    (SITE / "CNAME").write_text(domain + "\n")
    (SITE / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{today.isoformat()}</lastmod></url>\n"
                  for u in pages if not u.endswith("/widget/"))  # module : non indexé
        + "</urlset>\n")
    if SOURCE_CODE is None:
        print("  ! AGPL : adresse du code source non renseignée (variable SOURCE_CODE) — "
              "à définir avant la mise en ligne ; automatique sur GitHub Actions.")
    old = ROOT / ".site-old"
    if old.exists():
        shutil.rmtree(old)
    if final.exists():
        os.replace(final, old)
    os.replace(SITE, final)
    shutil.rmtree(old, ignore_errors=True)
    SITE = final
    print("site généré dans", SITE.relative_to(ROOT))


if __name__ == "__main__":
    main()
