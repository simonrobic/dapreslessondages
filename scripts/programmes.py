#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Professions de foi du premier tour des présidents élus, découpées en passages
puis classées par thème (data/programmes/codage.json).

Les textes appartiennent à leurs auteurs : ils sont téléchargés dans
data/raw/professions-de-foi/ (hors dépôt) pour être analysés, et seuls les
premiers mots de chaque passage sont publiés, avec un lien vers l'original.

    .venv/bin/python scripts/programmes.py segments   # télécharge, découpe, affiche les passages
    .venv/bin/python scripts/programmes.py parts      # applique le codage et calcule les parts
"""
import json
import re
import subprocess
import sys
import urllib.request

from common import ROOT

RAW = ROOT / "data" / "raw" / "professions-de-foi"
OUT = ROOT / "data" / "programmes"
UA = {"User-Agent": "dapreslessondages/1.0 (+https://dapreslessondages.fr)"}
ARCHELEC = "https://archive.org/details/{}"
LONG = 120  # mots : au-delà, un paragraphe est découpé en phrases

# Premier tour, président élu. 1965-2012 : archives électorales du CEVIPOF
# (Archelec, Sciences Po), texte reconnu par Internet Archive. 2017 et 2022 :
# documents officiels réunis par France-politique.fr.
DOCS = [
    {"annee": 1965, "candidat": "Charles de Gaulle", "id": "EL033_P_1965_002"},
    {"annee": 1969, "candidat": "Georges Pompidou", "id": "EL053_P_1969_006"},
    {"annee": 1974, "candidat": "Valéry Giscard d'Estaing", "id": "EL084_P_1974_002"},
    {"annee": 1981, "candidat": "François Mitterrand", "id": "EL123_P_1981_010"},
    {"annee": 1988, "candidat": "François Mitterrand", "id": "EL169_P_1988_008"},
    {"annee": 1995, "candidat": "Jacques Chirac", "id": "EL209_P_1995_003"},
    {"annee": 2002, "candidat": "Jacques Chirac", "id": "EL231_P_2002_004", "fichier": "EL231_P_2002_049_djvu.txt"},
    {"annee": 2007, "candidat": "Nicolas Sarkozy", "id": "EL235_P_2007_008"},
    {"annee": 2012, "candidat": "François Hollande", "id": "EL245_P_2012_033"},
    {"annee": 2017, "candidat": "Emmanuel Macron", "pdf": "https://www.france-politique.fr/doc/PR-2017/2017-Macron.pdf"},
    {"annee": 2022, "candidat": "Emmanuel Macron", "pdf": "https://www.france-politique.fr/doc/PR-2022/PR2022-Macron-PROF.pdf"},
]

# Thèmes de l'Eurobaromètre, plus ceux propres aux programmes
THEMES_PROGRAMME = {
    "europe": "Europe",
    "societe": "Société, culture et égalités",
    "general": "Généralités (valeurs, rassemblement, appel au vote)",
}


def source_url(doc):
    return ARCHELEC.format(doc["id"]) if "id" in doc else doc["pdf"]


def raw_text(doc):
    RAW.mkdir(parents=True, exist_ok=True)
    txt = RAW / f"{doc['annee']}.txt"
    if txt.exists():
        return txt.read_text(errors="ignore")
    if "id" in doc:
        name = doc.get("fichier", f"{doc['id']}_djvu.txt")
        url = f"https://archive.org/download/{doc['id']}/{name}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            txt.write_bytes(r.read())
    else:
        pdf = RAW / f"{doc['annee']}.pdf"
        with urllib.request.urlopen(urllib.request.Request(doc["pdf"], headers=UA), timeout=120) as r:
            pdf.write_bytes(r.read())
        subprocess.run(["pdftotext", str(pdf), str(txt)], check=True)
    return txt.read_text(errors="ignore")


def readable(words):
    """Écarte les passages illisibles (OCR d'écriture manuscrite, logos)."""
    ok = [w for w in words if re.fullmatch(r"[A-Za-zÀ-ÿœŒ'’\-]{2,}[.,;:!?»)]*", w)]
    return len(words) >= 6 and len(ok) / len(words) >= 0.7


def segments(text):
    text = text.replace("\r", "").replace("­", "")
    text = re.sub(r"-\n(?=[a-zà-ÿ])", "", text)  # mots coupés en fin de ligne
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    out = []
    for p in paras:
        words = p.split()
        if not readable(words):
            continue
        if len(words) <= LONG:
            out.append(p)
            continue
        # Long paragraphe qui aborde plusieurs sujets : un passage par phrase
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÝÉ«“])", p):
            if out and len(sentence.split()) < 6 and out[-1] is not None:
                out[-1] += " " + sentence
            else:
                out.append(sentence)
    return out


def excerpt(seg, n=8):
    words = seg.split()
    return " ".join(words[:n]) + (" …" if len(words) > n else "")


def cmd_segments():
    for doc in DOCS:
        segs = segments(raw_text(doc))
        (RAW / f"{doc['annee']}-segments.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1))
        print(f"\n===== {doc['annee']} — {doc['candidat']} — {len(segs)} passages, {sum(len(s.split()) for s in segs)} mots")
        for i, s in enumerate(segs):
            print(f"[{i}] ({len(s.split())}) {s}")


def cmd_parts():
    from eurobarometer import THEME_LABELS
    labels = dict(THEME_LABELS, **THEMES_PROGRAMME)
    coding = json.loads((OUT / "codage.json").read_text())
    result = []
    for doc in DOCS:
        segs = json.loads((RAW / f"{doc['annee']}-segments.json").read_text())
        codes = coding["codage"][str(doc["annee"])]
        assert len(codes) == len(segs), f"{doc['annee']} : {len(codes)} codes pour {len(segs)} passages"
        words, rows = {}, []
        for i, (seg, theme) in enumerate(zip(segs, codes)):
            if theme is None:  # passage hors programme (mentions légales, illisible…)
                continue
            assert theme in labels, f"{doc['annee']}[{i}] : thème inconnu {theme}"
            n = len(seg.split())
            words[theme] = words.get(theme, 0) + n
            rows.append({"n": i, "debut": excerpt(seg), "mots": n, "theme": theme})
        total = sum(words.values())
        result.append({
            "annee": doc["annee"], "candidat": doc["candidat"], "source": source_url(doc),
            "mots": total,
            "parts": {k: round(100 * v / total, 1) for k, v in sorted(words.items(), key=lambda kv: -kv[1])},
            "passages": rows,
        })
    (OUT / "professions-de-foi.json").write_text(json.dumps({
        "methode": coding["methode"],
        "themes": labels,
        "documents": result,
    }, ensure_ascii=False, indent=1))
    for r in result:
        top = list(r["parts"].items())[:4]
        print(r["annee"], r["candidat"], r["mots"], "mots :", ", ".join(f"{labels[k]} {v:.0f} %" for k, v in top))


if __name__ == "__main__":
    {"segments": cmd_segments, "parts": cmd_parts}[sys.argv[1] if len(sys.argv) > 1 else "segments"]()
