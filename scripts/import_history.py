#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Convertit l'historique des sondages (1981-2022) dans le format commun
data/polls/<année>.json :

- 1981-2017 : dépôt d'origine depuis1958/sondages (CSV, CC BY-SA 3.0 FR),
  copié dans data/raw/sondages ;
- 2022 : compilation NSPPolls (data/raw/nsppolls/presidentielle.json, licence
  MIT), plus complète que les fichiers 2022 du dépôt d'origine ;
- 2017, avant le 1er janvier 2017 : page Wikipédia des sondages 2017
  (data/raw/wikipedia-2017.json, CC BY-SA 4.0). Le dépôt d'origine ne commence
  qu'en janvier 2017 ; ces sondages permettent de comparer 2027 à 2017 au même
  stade de la campagne.

Les résultats officiels (Conseil constitutionnel, % des suffrages exprimés)
sont écrits dans data/resultats.json.
"""
import csv
import datetime
import json
from pathlib import Path

from common import ROOT, canonical_name, date_fr
from wikipedia import download, parse_page

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "polls"

# Sondages Wikipédia : seule source de 1965 à 1974, et complément des années
# suivantes pour la période antérieure au début du dépôt d'origine (qui commence
# entre janvier et mars de l'année de l'élection). Cela permet de comparer les
# campagnes « au même stade », plusieurs mois avant le vote.
LIST_PAGE = "Liste de sondages sur l'élection présidentielle française de {}"
ARTICLE = "Élection présidentielle française de {}"
WIKIPEDIA = {
    1965: ARTICLE, 1969: ARTICLE, 1974: ARTICLE,
    1981: ARTICLE, 1988: ARTICLE, 1995: ARTICLE,
    2002: LIST_PAGE, 2007: LIST_PAGE, 2012: LIST_PAGE, 2017: LIST_PAGE,
}
SINCE_DAYS = 600  # on ne garde que les sondages des ~20 mois précédant le vote

ELECTIONS = {
    1965: ("1965-12-05", "1965-12-19"),
    1969: ("1969-06-01", "1969-06-15"),
    1974: ("1974-05-05", "1974-05-19"),
    1981: ("1981-04-26", "1981-05-10"),
    1988: ("1988-04-24", "1988-05-08"),
    1995: ("1995-04-23", "1995-05-07"),
    2002: ("2002-04-21", "2002-05-05"),
    2007: ("2007-04-22", "2007-05-06"),
    2012: ("2012-04-22", "2012-05-06"),
    2017: ("2017-04-23", "2017-05-07"),
    2022: ("2022-04-10", "2022-04-24"),
    2027: ("2027-04-18", "2027-05-02"),
}

# Résultats officiels, en % des suffrages exprimés
RESULTS = {
    1965: {
        "premier_tour": {"Charles de Gaulle": 44.65, "François Mitterrand": 31.72, "Jean Lecanuet": 15.57,
                         "Jean-Louis Tixier-Vignancour": 5.20, "Pierre Marcilhacy": 1.71, "Marcel Barbu": 1.15},
        "second_tour": {"Charles de Gaulle": 55.20, "François Mitterrand": 44.80},
    },
    1969: {
        "premier_tour": {"Georges Pompidou": 44.47, "Alain Poher": 23.31, "Jacques Duclos": 21.27,
                         "Gaston Defferre": 5.01, "Michel Rocard": 3.61, "Louis Ducatel": 1.27, "Alain Krivine": 1.06},
        "second_tour": {"Georges Pompidou": 58.21, "Alain Poher": 41.79},
    },
    1974: {
        "premier_tour": {"François Mitterrand": 43.25, "Valéry Giscard d'Estaing": 32.60,
                         "Jacques Chaban-Delmas": 15.11, "Jean Royer": 3.17, "Arlette Laguiller": 2.33,
                         "René Dumont": 1.32, "Jean-Marie Le Pen": 0.75, "Émile Muller": 0.69,
                         "Alain Krivine": 0.37, "Bertrand Renouvin": 0.17, "Jean-Claude Sebag": 0.16,
                         "Guy Héraud": 0.08},
        "second_tour": {"Valéry Giscard d'Estaing": 50.81, "François Mitterrand": 49.19},
    },
    1981: {
        "premier_tour": {"Valéry Giscard d'Estaing": 28.32, "François Mitterrand": 25.85, "Jacques Chirac": 18.00,
                         "Georges Marchais": 15.35, "Brice Lalonde": 3.88, "Arlette Laguiller": 2.30,
                         "Michel Crépeau": 2.21, "Michel Debré": 1.66, "Marie-France Garaud": 1.33,
                         "Huguette Bouchardeau": 1.10},
        "second_tour": {"François Mitterrand": 51.76, "Valéry Giscard d'Estaing": 48.24},
    },
    1988: {
        "premier_tour": {"François Mitterrand": 34.10, "Jacques Chirac": 19.96, "Raymond Barre": 16.54,
                         "Jean-Marie Le Pen": 14.38, "André Lajoinie": 6.76, "Antoine Waechter": 3.78,
                         "Pierre Juquin": 2.10, "Arlette Laguiller": 1.99, "Pierre Boussel": 0.38},
        "second_tour": {"François Mitterrand": 54.02, "Jacques Chirac": 45.98},
    },
    1995: {
        "premier_tour": {"Lionel Jospin": 23.30, "Jacques Chirac": 20.84, "Édouard Balladur": 18.58,
                         "Jean-Marie Le Pen": 15.00, "Robert Hue": 8.64, "Arlette Laguiller": 5.30,
                         "Philippe de Villiers": 4.74, "Dominique Voynet": 3.32, "Jacques Cheminade": 0.28},
        "second_tour": {"Jacques Chirac": 52.64, "Lionel Jospin": 47.36},
    },
    2002: {
        "premier_tour": {"Jacques Chirac": 19.88, "Jean-Marie Le Pen": 16.86, "Lionel Jospin": 16.18,
                         "François Bayrou": 6.84, "Arlette Laguiller": 5.72, "Jean-Pierre Chevènement": 5.33,
                         "Noël Mamère": 5.25, "Olivier Besancenot": 4.25, "Jean Saint-Josse": 4.23,
                         "Alain Madelin": 3.91, "Robert Hue": 3.37, "Bruno Mégret": 2.34,
                         "Christiane Taubira": 2.32, "Corinne Lepage": 1.88, "Christine Boutin": 1.19,
                         "Daniel Gluckstein": 0.47},
        "second_tour": {"Jacques Chirac": 82.21, "Jean-Marie Le Pen": 17.79},
    },
    2007: {
        "premier_tour": {"Nicolas Sarkozy": 31.18, "Ségolène Royal": 25.87, "François Bayrou": 18.57,
                         "Jean-Marie Le Pen": 10.44, "Olivier Besancenot": 4.08, "Philippe de Villiers": 2.23,
                         "Marie-George Buffet": 1.93, "Dominique Voynet": 1.57, "Arlette Laguiller": 1.33,
                         "José Bové": 1.32, "Frédéric Nihous": 1.15, "Gérard Schivardi": 0.34},
        "second_tour": {"Nicolas Sarkozy": 53.06, "Ségolène Royal": 46.94},
    },
    2012: {
        "premier_tour": {"François Hollande": 28.63, "Nicolas Sarkozy": 27.18, "Marine Le Pen": 17.90,
                         "Jean-Luc Mélenchon": 11.10, "François Bayrou": 9.13, "Eva Joly": 2.31,
                         "Nicolas Dupont-Aignan": 1.79, "Philippe Poutou": 1.15, "Nathalie Arthaud": 0.56,
                         "Jacques Cheminade": 0.25},
        "second_tour": {"François Hollande": 51.64, "Nicolas Sarkozy": 48.36},
    },
    2017: {
        "premier_tour": {"Emmanuel Macron": 24.01, "Marine Le Pen": 21.30, "François Fillon": 20.01,
                         "Jean-Luc Mélenchon": 19.58, "Benoît Hamon": 6.36, "Nicolas Dupont-Aignan": 4.70,
                         "Jean Lassalle": 1.21, "Philippe Poutou": 1.09, "François Asselineau": 0.92,
                         "Nathalie Arthaud": 0.64, "Jacques Cheminade": 0.18},
        "second_tour": {"Emmanuel Macron": 66.10, "Marine Le Pen": 33.90},
    },
    2022: {
        "premier_tour": {"Emmanuel Macron": 27.85, "Marine Le Pen": 23.15, "Jean-Luc Mélenchon": 21.95,
                         "Éric Zemmour": 7.07, "Valérie Pécresse": 4.78, "Yannick Jadot": 4.63,
                         "Jean Lassalle": 3.13, "Fabien Roussel": 2.28, "Nicolas Dupont-Aignan": 2.06,
                         "Anne Hidalgo": 1.75, "Philippe Poutou": 0.77, "Nathalie Arthaud": 0.56},
        "second_tour": {"Emmanuel Macron": 58.55, "Marine Le Pen": 41.45},
    },
}


# Erreurs relevées dans le dépôt d'origine : en 1988, les colonnes des duels
# sont inversées (Mitterrand était donné gagnant à 54-57 % face à Chirac comme
# face à Barre, et l'a emporté avec 54,02 %). Correction proposée en retour :
# https://github.com/depuis1958/sondages/pull/45 ; si elle est acceptée et que la
# copie de data/raw/sondages est mise à jour, vider cet ensemble.
SWAPPED_COLUMNS = {"1988/second-tour-chirac-mitterand.csv", "1988/second-tour-barre-mitterand.csv"}


def number(text):
    text = (text or "").strip().replace(",", ".")
    return float(text) if text else None


def from_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            fixed = list(rec)[:5]
            scores = {}
            for col, val in rec.items():
                if col in fixed or col is None:
                    continue
                v = number(val)
                if v is not None:
                    scores[canonical_name(col)] = v
            if len(scores) < 2:
                continue
            sample = number(rec.get("échantillon"))
            rows.append({
                "sondeur": rec["sondeur"].strip(),
                "debut": rec["date début"].strip() or rec["date fin"].strip(),
                "fin": rec["date fin"].strip(),
                "echantillon": int(sample) if sample else None,
                "source": (rec.get("source") or "").strip() or None,
                "scores": scores,
            })
    return rows


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        key = (r["sondeur"], r["fin"], tuple(sorted(r["scores"].items())))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return sorted(out, key=lambda r: r["fin"])


def import_depuis1958(year):
    folder = RAW / "sondages" / "presidentielle" / str(year)
    first, second = [], []
    for path in sorted(folder.glob("*.csv")):
        rows = from_csv(path)
        if f"{year}/{path.name}" in SWAPPED_COLUMNS:
            for r in rows:
                (a, va), (b, vb) = r["scores"].items()
                r["scores"] = {a: vb, b: va}
        (first if path.name.startswith("premier-tour") else second).extend(rows)
    return dedupe(first), dedupe([r for r in second if len(r["scores"]) == 2])


def import_nsppolls():
    data = json.loads((RAW / "nsppolls" / "presidentielle.json").read_text())
    first, second = [], []
    for poll in data:
        base = {
            "sondeur": poll["nom_institut"],
            "debut": poll["debut_enquete"],
            "fin": poll["fin_enquete"],
            "echantillon": poll.get("echantillon"),
            "source": poll.get("lien"),
        }
        for tour in poll["tours"]:
            for hyp in tour["hypotheses"]:
                scores = {canonical_name(c["candidat"]): float(c["intentions"])
                          for c in hyp["candidats"] if c.get("candidat") and c.get("intentions") is not None}
                row = dict(base, scores=scores)
                if tour["tour"] == "Premier tour" and len(scores) >= 2:
                    first.append(row)
                elif tour["tour"] != "Premier tour" and len(scores) == 2:
                    second.append(row)
    return dedupe(first), dedupe(second)


def import_wikipedia(year, first_since=None, second_since=None):
    """
    Sondages et jalons Wikipédia. Quand le dépôt d'origine couvre l'élection,
    seuls les sondages antérieurs à son premier sondage sont gardés.
    """
    page = WIKIPEDIA[year].format(year)
    raw = RAW / f"wikipedia-{year}.json"
    data = json.loads(raw.read_text()) if raw.exists() else download(page, raw)
    first, second, events, _ = parse_page(data, year)
    d1 = ELECTIONS[year][0]
    since = (datetime.date.fromisoformat(d1) - datetime.timedelta(days=SINCE_DAYS)).isoformat()
    for r in first + second:
        r.pop("section", None)
    first = [r for r in first if since <= r["fin"] < (first_since or "9999") and r["fin"] < d1]
    second = [r for r in second if since <= r["fin"] < (second_since or "9999") and r["fin"] <= ELECTIONS[year][1]]
    cut = min(x for x in (first_since, second_since) if x) if (first_since or second_since) else None
    source = {"url": f"https://fr.wikipedia.org/wiki/{page.replace(' ', '_')}",
              "licence": "CC BY-SA 4.0 — contributeurs de Wikipédia",
              "periode": f"sondages antérieurs au {date_fr(cut)}" if cut else None,
              "revision": data["parse"].get("revid")}
    return first, second, events, source


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for year, (d1, d2) in ELECTIONS.items():
        if year == 2027:
            continue
        if year == 2022:
            first, second = import_nsppolls()
            source, licence = "https://github.com/nsppolls/nsppolls", "MIT — NSPPolls"
        elif year >= 1981:
            first, second = import_depuis1958(year)
            source, licence = "https://github.com/depuis1958/sondages", "CC BY-SA 3.0 FR — Victor Poughon et contributeurs"
        else:
            first, second, source, licence = [], [], None, None
        sources = [{"url": source, "licence": licence}] if source else []
        events = []
        if year in WIKIPEDIA:
            w_first, w_second, events, w_source = import_wikipedia(
                year, first[0]["fin"] if first else None, second[0]["fin"] if second else None)
            first = dedupe(first + w_first)
            second = dedupe(second + w_second)
            sources.append(w_source)
            if not source:
                source, licence = w_source["url"], w_source["licence"]
        for r in first + second:
            total = sum(r["scores"].values())
            r["total_brut"] = round(total, 2)
        out = {
            "election": year,
            "date_premier_tour": d1,
            "date_second_tour": d2,
            "source": source,
            "licence": licence,
            "sources": sources,
            "premier_tour": first,
            "second_tour": second,
            "evenements": [e for e in events if e["date"] <= d1],
        }
        (OUT / f"{year}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"{year} : {len(first):4d} hypothèses de 1er tour, {len(second):4d} duels")
    results = {str(y): dict(r, date_premier_tour=ELECTIONS[y][0], date_second_tour=ELECTIONS[y][1])
               for y, r in RESULTS.items()}
    (ROOT / "data" / "resultats.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
