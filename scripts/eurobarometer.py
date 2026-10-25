#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Préoccupations des Français d'après l'Eurobaromètre standard (Commission
européenne, licence CC BY 4.0), question posée deux fois par an depuis 2002 :

    « À votre avis, quels sont les deux problèmes les plus importants auxquels
      doit faire face (NOTRE PAYS) actuellement ? » (2 réponses maximum)

La question figure dans l'Eurobaromètre standard à partir de la vague 59
(printemps 2003) ; les vagues 59 à 62 (2003-2004), publiées sous forme de
tableaux texte, ne sont pas encore lues : la série exploitée commence en 2005.

Les tableaux par pays (« volume A ») sont téléchargés depuis data.europa.eu,
mis en cache dans data/raw/eurobarometre/ (hors dépôt, volumineux), puis la
colonne France est extraite dans data/preoccupations/eurobarometre-france.json.

    .venv/bin/python scripts/eurobarometer.py            # télécharge ce qui manque
    .venv/bin/python scripts/eurobarometer.py --offline  # cache uniquement
"""
import argparse
import datetime
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile

from common import ROOT

API = "https://data.europa.eu/api/hub/search/search"
RAW = ROOT / "data" / "raw" / "eurobarometre"
OUT = ROOT / "data" / "preoccupations" / "eurobarometre-france.json"
UA = {"User-Agent": "dapreslessondages/1.0 (+https://dapreslessondages.fr)"}

QUESTION = re.compile(r"(deux probl[eè]mes les plus importants auxquels doit faire face \(?notre pays"
                      r"|two most important issues facing \(?our country)", re.I)

# Thèmes stables : la liste de l'Eurobaromètre change au fil des vagues
THEMES = [
    ("prix", "Prix et pouvoir d'achat", r"rising prices|inflation|cost of living|hausse des prix|co[uû]t de la vie"),
    ("economie", "Situation économique", r"economic situation|situation [ée]conomique"),
    ("chomage", "Chômage et emploi", r"unemployment|ch[oô]mage"),
    ("insecurite", "Insécurité et délinquance", r"\bcrime\b|ins[ée]curit[ée]|d[ée]linquance"),
    ("terrorisme", "Terrorisme", r"terroris"),
    ("immigration", "Immigration", r"immigration"),
    ("sante", "Santé et protection sociale", r"health|sant[ée]|social security|s[ée]curit[ée] sociale"),
    ("retraites", "Retraites", r"pension|retraite"),
    ("education", "Éducation", r"education|[ée]ducati"),
    ("environnement", "Environnement, climat et énergie", r"environment|climat|energy|[ée]nergie"),
    ("dette_impots", "Dette publique et impôts", r"government debt|dette|taxation|fiscalit|imp[oô]t"),
    ("logement", "Logement", r"housing|logement"),
    ("international", "International et défense", r"international|defence|d[ée]fense|foreign|[ée]trang[eè]re|ukraine|"
                                                  r"middle east|moyen-orient|security and defence"),
    ("democratie", "Démocratie et institutions", r"democra|d[ée]mocrat"),
]
SKIP = re.compile(r"\b(other|autre|none|aucun|don't know|\bdk\b|nsp|ne sait pas|total|base)\b", re.I)
THEME_LABELS = {k: lab for k, lab, _ in THEMES}


def strip(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def theme_of(labels):
    text = " ".join(l for l in labels if l)
    for key, _, pattern in THEMES:
        if re.search(pattern, text, re.I):
            return key
    return None


def catalogue():
    """Toutes les vagues standard depuis la 57 (printemps 2002), avec leurs fichiers."""
    waves, page = {}, 0
    while True:
        url = API + "?" + urllib.parse.urlencode(
            {"q": '"Standard Eurobarometer"', "filter": "dataset", "limit": 100, "page": page})
        res = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))["result"]["results"]
        if not res:
            break
        for r in res:
            title = ((r.get("title") or {}).get("en") or "").strip()
            m = re.match(r"^Standard Eurobarometer (?:STD)?(\d{2,3})\b", title)
            if not m or int(m.group(1)) < 57:
                continue
            waves.setdefault(int(m.group(1)), [
                {"titre": ((d.get("title") or {}).get("en") or "").replace("Link to ", ""),
                 "url": (d.get("access_url") or [None])[0],
                 "licence": (d.get("license") or {}).get("label")}
                for d in r.get("distributions") or []])
        page += 1
    return waves


def pick_file(files):
    """Le volume A (un tableau par pays), à défaut le volume C France."""
    vol_a = [f for f in files if re.search(r"vol(ume)?[ _]?a(?=eb|[ _.\-]|$)", f["titre"], re.I)
             and not re.search(r"_AI\b|_AI\.", f["titre"])]  # « A_AI » : indicateurs annexes
    if vol_a:
        return vol_a[0]
    vol_ap = [f for f in files if re.search(r"vol(ume)?[ _]?ap(?=eb|[ _.\-]|$)", f["titre"], re.I)]
    if vol_ap:
        return vol_ap[0]
    france = [f for f in files if re.search(r"france|cfr\b|cfr\.|_fr\b", f["titre"], re.I)]
    return france[0] if france else None


def download(n, f):
    folder = RAW / f"EB{n}"
    if folder.exists() and any(folder.iterdir()):
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.\-]+", "_", f["titre"]) or f"EB{n}"
    target = folder / name
    with urllib.request.urlopen(urllib.request.Request(f["url"], headers=UA), timeout=300) as r:
        target.write_bytes(r.read())
    if target.suffix.lower() not in (".xlsx", ".xls") and zipfile.is_zipfile(target):  # un .xlsx est aussi un zip
        with zipfile.ZipFile(target) as z:
            z.extractall(folder)
        target.unlink()
    return folder


def sheets(path):
    """Feuilles d'un classeur xls/xlsx, sous forme de listes de lignes."""
    if path.suffix.lower() == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]
    elif path.suffix.lower() == ".xls":
        import xlrd
        book = xlrd.open_workbook(str(path), on_demand=True)
        for name in book.sheet_names():
            sh = book.sheet_by_name(name)
            yield name, [sh.row_values(i) for i in range(sh.nrows)]


def wave_date(n):
    """Date approximative d'une vague standard : printemps (avril) ou automne (novembre), dès la 57 (2002)."""
    year, autumn = 2002 + (n - 57) // 2, (n - 57) % 2 == 1
    return datetime.date(year, 11 if autumn else 4, 15).isoformat()


def fieldwork(rows):
    """Dates de terrain : « 9/10 - 5/11/2025 », « 03-20/11/2011 », « 09-10/2007 », « 04/2006 »."""
    import calendar
    for r in rows[:8]:
        for c in r:
            t = str(c or "")
            if not re.search(r"terrain|fieldwork", t, re.I):
                continue
            try:
                m = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})", t)
                if m:
                    d1, m1, y1, d2, m2, y2 = m.groups()
                    y1 = y1 or (y2 if int(m1) <= int(m2) else str(int(y2) - 1))
                    return (datetime.date(int(y1), int(m1), int(d1)).isoformat(),
                            datetime.date(int(y2), int(m2), int(d2)).isoformat())
                m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})", t)
                if m:
                    d1, d2, mo, y = map(int, m.groups())
                    return datetime.date(y, mo, d1).isoformat(), datetime.date(y, mo, d2).isoformat()
                m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})/(\d{4})", t)
                if m:
                    m1, m2, y = map(int, m.groups())
                    return (datetime.date(y, m1, 1).isoformat(),
                            datetime.date(y, m2, calendar.monthrange(y, m2)[1]).isoformat())
                m = re.search(r"(\d{1,2})/(\d{4})", t)
                if m:
                    mo, y = map(int, m.groups())
                    return (datetime.date(y, mo, 1).isoformat(),
                            datetime.date(y, mo, calendar.monthrange(y, mo)[1]).isoformat())
            except ValueError:
                return None
    return None


def parse_sheet(rows, wave):
    """Colonne France de la question ; pour un tableau à deux vagues, la plus récente."""
    head = " ".join(str(c) for r in rows[:6] for c in r if c)
    if not QUESTION.search(head) or re.search(r"(vous personnellement|you personally|\bthe eu\b|l'ue\b|union europ)", head, re.I):
        return None
    hdr_i = next((i for i, r in enumerate(rows[:15]) if any(str(c or "").split("\n")[0].strip() == "FR" for c in r)), None)
    if hdr_i is None:
        return None
    cols = [k for k, c in enumerate(rows[hdr_i]) if str(c or "").split("\n")[0].strip() == "FR"]
    col = cols[0]
    # Tableau AP (vague précédente | vague courante) : la vague courante est à droite
    sub = rows[hdr_i + 1] if hdr_i + 1 < len(rows) else []
    if col + 1 < len(sub) and re.search(r"EB", str(sub[col] or "")) and re.search(r"EB", str(sub[col + 1] or "")):
        col = col + 1
    items, labels = [], []
    for r in rows[hdr_i + 1:]:
        texts = [str(c).strip() for c in r[:2] if isinstance(c, str) and c.strip() and not c.startswith("=")]
        if texts:
            labels = (labels + texts)[-2:]
        v = r[col] if col < len(r) else None
        if isinstance(v, (int, float)) and 0 <= v <= 1 and labels and not SKIP.search(" ".join(labels)):
            items.append({"libelle": labels[-1], "theme": theme_of(labels), "part": round(100 * float(v), 1)})
            labels = []
    # Une même ligne peut apparaître en pourcentage puis en nombre : on garde la première
    seen, unique = set(), []
    for it in items:
        if it["libelle"] not in seen:
            seen.add(it["libelle"])
            unique.append(it)
    return {"vague": wave, "terrain": fieldwork(rows), "reponses": unique} if unique else None


def parse_wave(n, folder):
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in (".xls", ".xlsx"):
            continue
        try:
            for name, rows in sheets(path):
                if not rows:
                    continue
                res = parse_sheet(rows, n)
                if res:
                    res["fichier"] = path.name
                    return res
        except Exception as exc:  # fichier illisible : on passe au suivant
            print(f"  ! EB{n} {path.name} : {exc}", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    waves = {} if args.offline else catalogue()
    if args.offline:
        waves = {int(p.name[2:]): None for p in RAW.glob("EB*")}
    results, missing = [], []
    for n in sorted(waves):
        try:
            folder = RAW / f"EB{n}" if args.offline else download(n, pick_file(waves[n]) or {"titre": "", "url": None})
        except Exception as exc:
            missing.append((n, f"téléchargement : {exc}"))
            continue
        res = parse_wave(n, folder)
        if res is None:
            missing.append((n, "question introuvable dans le volume A"))
            continue
        themes = {}
        for it in res["reponses"]:
            if it["theme"]:
                themes[it["theme"]] = max(themes.get(it["theme"], 0), it["part"])
        res["themes"] = themes
        res["date"] = res["terrain"][1] if res["terrain"] else wave_date(n)
        res["date_approx"] = res["terrain"] is None
        results.append(res)
        top = sorted(themes.items(), key=lambda kv: -kv[1])[:3]
        print(f"EB{n} {res['terrain']} : " + ", ".join(f"{THEME_LABELS[k]} {v:.0f} %" for k, v in top))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "Eurobaromètre standard, Commission européenne — https://data.europa.eu",
        "licence": "CC BY 4.0",
        "question": "À votre avis, quels sont les deux problèmes les plus importants auxquels doit faire face "
                    "la France actuellement ? (2 réponses maximum)",
        "themes": [{"cle": k, "libelle": lab} for k, lab, _ in THEMES],
        "vagues": results,
        "manquantes": [{"vague": n, "raison": r} for n, r in missing],
    }, ensure_ascii=False, indent=1))
    print(f"{len(results)} vagues extraites, {len(missing)} manquantes -> {OUT.relative_to(ROOT)}")
    for n, r in missing:
        print(f"  ! EB{n} : {r}", file=sys.stderr)


if __name__ == "__main__":
    main()
