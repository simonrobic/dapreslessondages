#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Score d'alignement provisoire des candidats 2027 : leurs textes programmatiques
officiels, découpés et classés par thème avec les mêmes règles que les
professions de foi des élus (scripts/programmes.py).

Règle de sélection : les textes programmatiques mis en avant sur le site
officiel du candidat ou de son parti, tels qu'en ligne le jour de la collecte.
Les sites tiers (agrégateurs, « fiches programme ») sont exclus.

    .venv/bin/python scripts/candidats_2027.py segments   # découpe et affiche les passages
    .venv/bin/python scripts/candidats_2027.py parts      # applique le codage

Un document est lu dans data/raw/candidats-2027/<fichier>.pdf s'il existe,
sinon <fichier>.html.
"""
import json
import re
import subprocess
import sys

from bs4 import BeautifulSoup

from common import ROOT
from programmes import LONG, excerpt, segments

RAW = ROOT / "data" / "raw" / "candidats-2027"
OUT = ROOT / "data" / "programmes"
COLLECTE = "2026-10-24"  # date de consultation des sites, sauf « collecte » propre à un candidat

CANDIDATES = [
    {"candidat": "Marine Le Pen", "documents": [
        {"fichier": "le-pen_22-mesures", "titre": "« 22 mesures pour 2022 », programme présidentiel de 2022 toujours présenté "
                                                  "comme le programme du Rassemblement national",
         "url": "https://rassemblementnational.fr/22-mesures"}],
     "remarque": "Aucun programme 2027 publié : le texte retenu est celui de 2022, toujours mis en avant par le RN."},
    {"candidat": "Édouard Philippe", "documents": [
        {"fichier": "philippe_manifeste", "titre": "Le Manifeste d'Horizons", "url": "https://horizonsleparti.fr/le-manifeste/"},
        {"fichier": "philippe_narcotrafic", "titre": "Le plan d'Édouard Philippe contre le narcotrafic",
         "url": "https://horizonsleparti.fr/le-plan-dedouard-philippe-contre-le-narcotrafic/"}],
     "remarque": "Pas de programme complet publié : le manifeste du parti et le seul plan thématique en ligne, "
                 "consacré au narcotrafic, qui pèse donc lourd dans sa répartition."},
    {"candidat": "Gabriel Attal", "documents": [
        {"fichier": f"attal_{k}", "titre": f"« Mes chantiers capitaux » : {t}", "url": f"https://attalpresident.fr/programme/{k}"}
        for k, t in (("education", "École"), ("travail-salaires", "Travail et salaires"), ("frontieres", "Frontières"),
                     ("intelligence-artificielle", "Intelligence artificielle"), ("dette-de-letat", "Dette de l'État"),
                     ("dette-ecologique", "Dette écologique"))],
     "remarque": "Programme publié par thèmes sur le site de campagne."},
    {"candidat": "Raphaël Glucksmann", "documents": [
        {"fichier": "glucksmann_site", "titre": "Site de campagne", "url": "https://glucks2027.fr/"},
        {"fichier": "glucksmann_projet", "titre": "Place publique : le projet",
         "url": "https://place-publique.eu/pages/69jA2SKIG5udlNX7wI3dmc/le-projet"},
        {"fichier": "glucksmann_combats", "titre": "Place publique : les combats",
         "url": "https://place-publique.eu/pages/59EfFYTpFlj2lJhQ92PXsy/les-combats"}],
     "remarque": "Pas de programme complet publié : la déclaration du site de campagne et le projet de son parti."},
    {"candidat": "Bruno Retailleau", "documents": [
        {"fichier": "retailleau_propositions", "titre": "Les Républicains : nos propositions",
         "url": "https://republicains.fr/nos-propositions/"}],
     "remarque": "Propositions du parti dont il est le candidat. Elles ne couvrent encore ni la sécurité ni "
                 "l'immigration, au cœur de son discours : le score mesure ce qui est publié, pas tout ce qu'il dit."},
]
NOT_SCORED = [
    {"candidat": "Jean-Luc Mélenchon", "raison": "La 5e édition de L'Avenir en commun paraît le 6 novembre 2026 ; "
                                                 "l'édition 2025 en ligne refuse les téléchargements automatiques.",
     # affiché en tête de section tant que le candidat n'est pas classé
     "a_venir": "la prochaine version de son programme, la 5e édition de L'Avenir en commun, n'est pas encore "
                "publiée (parution annoncée le 6 novembre 2026). Il sera ajouté dès sa sortie."},
    {"candidat": "Éric Zemmour", "raison": "Pas de programme publié : Reconquête mène une consultation en ligne "
                                           "(« Le programme pour la France ») et présente un plan budgétaire de Sarah Knafo."},
    {"candidat": "David Lisnard", "raison": "Aucun texte programmatique trouvé sur un site officiel."},
]

BLOCKS = ["h1", "h2", "h3", "h4", "p", "li", "blockquote"]
NOISE = re.compile(r"^(je fais un don|soutenez|aller sur|découvrir|lire|en savoir plus|partager|télécharger|"
                   r"comprendre la dette|retour|menu|adhérer|militer)\b", re.I)


def main_container(soup):
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg"]):
        t.decompose()
    cands = soup.find_all(["main", "article", "section", "div"])
    return max(cands, key=lambda e: len(e.find_all("p"))) if cands else soup


def doc_segments(name):
    pdf = RAW / f"{name}.pdf"
    if pdf.exists():  # programme publié en PDF : même découpage que les professions de foi
        txt = RAW / f"{name}.txt"
        if not txt.exists():
            subprocess.run(["pdftotext", str(pdf), str(txt)], check=True)
        return segments(txt.read_text(errors="ignore"))
    soup = BeautifulSoup((RAW / f"{name}.html").read_text(errors="ignore"), "html.parser")
    box = main_container(soup)
    out, seen = [], set()
    for el in box.find_all(BLOCKS):
        if el.find(BLOCKS):  # bloc qui en contient d'autres : on lira les enfants
            continue
        t = " ".join(el.get_text(" ").split())
        if len(t.split()) < 3 or NOISE.search(t) or t in seen:
            continue
        seen.add(t)
        words = t.split()
        if len(words) <= LONG:
            out.append(t)
        else:
            out.extend(s for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÝÉ«“])", t) if s.strip())
    return out


def cmd_segments():
    for c in CANDIDATES:
        segs = []
        for d in c["documents"]:
            segs.extend(doc_segments(d["fichier"]))
        key = c["candidat"].split()[-1].lower()
        (RAW / f"{key}-segments.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1))
        print(f"\n===== {c['candidat']} — {len(segs)} passages, {sum(len(s.split()) for s in segs)} mots")
        for i, s in enumerate(segs):
            print(f"[{i}] ({len(s.split())}) {s}")


def cmd_parts():
    from eurobarometer import THEME_LABELS
    from programmes import THEMES_PROGRAMME
    labels = dict(THEME_LABELS, **THEMES_PROGRAMME)
    coding = json.loads((OUT / "codage-candidats-2027.json").read_text())
    result = []
    for c in CANDIDATES:
        key = c["candidat"].split()[-1].lower()
        segs = json.loads((RAW / f"{key}-segments.json").read_text())
        codes = coding["codage"][c["candidat"]]
        assert len(codes) == len(segs), f"{c['candidat']} : {len(codes)} codes pour {len(segs)} passages"
        words, rows = {}, []
        for i, (seg, theme) in enumerate(zip(segs, codes)):
            if theme is None:
                continue
            assert theme in labels, f"{c['candidat']}[{i}] : thème inconnu {theme}"
            n = len(seg.split())
            words[theme] = words.get(theme, 0) + n
            rows.append({"n": i, "debut": excerpt(seg), "mots": n, "theme": theme})
        total = sum(words.values())
        result.append({
            "candidat": c["candidat"], "documents": [{k: d[k] for k in ("titre", "url")} for d in c["documents"]],
            "remarque": c["remarque"], "collecte": c.get("collecte", COLLECTE), "mots": total,
            "parts": {k: round(100 * v / total, 1) for k, v in sorted(words.items(), key=lambda kv: -kv[1])},
            "passages": rows,
        })
    (OUT / "candidats-2027.json").write_text(json.dumps({
        "methode": coding["methode"], "selection": __doc__.split("Règle de sélection : ")[1].split("\n\n")[0],
        "candidats": result, "non_classes": NOT_SCORED,
    }, ensure_ascii=False, indent=1))
    for r in result:
        top = list(r["parts"].items())[:4]
        print(r["candidat"], r["mots"], "mots :", ", ".join(f"{labels[k]} {v:.0f} %" for k, v in top))


if __name__ == "__main__":
    {"segments": cmd_segments, "parts": cmd_parts}[sys.argv[1] if len(sys.argv) > 1 else "segments"]()
