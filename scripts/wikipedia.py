# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Lecture des pages Wikipédia « Liste de sondages sur l'élection présidentielle
française de … » : tableaux d'hypothèses de premier tour, duels de second tour
et jalons de campagne, dans le format commun à toutes les élections.
"""
import datetime
import json
import re
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup

from common import canonical_name

API = "https://fr.wikipedia.org/w/api.php"

MONTHS = {
    "janvier": 1, "janv": 1, "février": 2, "fevrier": 2, "févr": 2, "fév": 2, "mars": 3,
    "avril": 4, "avr": 4, "mai": 5, "juin": 6, "juillet": 7, "juil": 7, "août": 8, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12,
}
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
DAY_MONTH = re.compile(rf"(\d{{1,2}})\s*(?:er)?\s*({MONTH_RE})\.?(?:\s+(\d{{4}}))?", re.I)
NUMBER = re.compile(r"(<\s*)?(\d+(?:[.,]\d+)?)")
MONTH_YEAR = re.compile(rf"({MONTH_RE})\.?\s+(\d{{4}})", re.I)


def download(page, raw_path):
    """Page Wikipédia rendue (HTML) via l'API, conservée telle quelle dans raw_path."""
    params = {"action": "parse", "page": page, "prop": "text|revid", "format": "json", "formatversion": "2"}
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": "dapreslessondages/1.0 (+https://dapreslessondages.fr)"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(data, ensure_ascii=False))
    return data


def expand_grid(table):
    """Développe rowspan/colspan : renvoie une grille de cellules (bs4 Tag)."""
    grid, pending = [], {}  # pending[col] = (cell, remaining_rows)
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["th", "td"], recursive=False)
        it = iter(cells)
        while True:
            if col in pending:
                cell, left = pending[col]
                row.append(cell)
                if left > 1:
                    pending[col] = (cell, left - 1)
                else:
                    del pending[col]
                col += 1
                continue
            cell = next(it, None)
            if cell is None:
                break
            rowspan = int(re.sub(r"\D", "", cell.get("rowspan", "1")) or 1)
            colspan = int(re.sub(r"\D", "", cell.get("colspan", "1")) or 1)
            for _ in range(colspan):
                row.append(cell)
                if rowspan > 1:
                    pending[col] = (cell, rowspan - 1)
                col += 1
        # Cellules restantes portées par un rowspan au-delà de la dernière cellule
        while col in pending:
            cell, left = pending[col]
            row.append(cell)
            if left > 1:
                pending[col] = (cell, left - 1)
            else:
                del pending[col]
            col += 1
        grid.append(row)
    return grid


def clean(cell):
    """Copie de la cellule sans appels de notes."""
    cell = BeautifulSoup(str(cell), "html.parser")
    for sup in cell.select("sup.reference, sup"):
        sup.decompose()
    return cell


def parse_value_cell(cell, default_name):
    """
    Une cellule de score peut contenir plusieurs entrées séparées par <hr>,
    chacune « valeur » et éventuellement un nom (<small>) qui remplace le
    candidat de la colonne. Renvoie [(nom, valeur)].
    """
    cell = clean(cell)
    parts = re.split(r"<hr\s*/?>", str(cell))
    entries = []
    for part in parts:
        frag = BeautifulSoup(part, "html.parser")
        name = None
        small = frag.find("small")
        if small is not None:
            link = small.find("a")
            name = link.get("title") if link is not None else small.get_text(" ", strip=True)
            name = re.sub(r"\s*\(.*?\)\s*$", "", name or "").strip() or None
            small.decompose()
        text = frag.get_text(" ", strip=True).replace("\xa0", " ")
        m = NUMBER.search(text)
        if not m:
            continue  # « — » : candidat non testé
        value = float(m.group(2).replace(",", "."))
        if m.group(1):  # « <1 » -> moitié du seuil
            value = value / 2
        entries.append((name or default_name, value))
    return entries


def parse_dates(text, context_year, context_month=None):
    text = text.replace("\xa0", " ")
    found = DAY_MONTH.findall(text)
    month_only = MONTH_YEAR.fullmatch(text.strip())
    if not found and month_only:
        # « février 1981 » : enquête datée au mois, on retient le milieu du mois
        month, year = MONTHS[month_only.group(1).lower()], int(month_only.group(2))
        return datetime.date(year, month, 1).isoformat(), datetime.date(year, month, 15).isoformat()
    if not found:
        days = re.findall(r"(\d{1,2})(?:er)?", text)
        if not days or context_month is None or context_year is None:
            return None
        try:
            return (datetime.date(context_year, context_month, int(days[0])).isoformat(),
                    datetime.date(context_year, context_month, int(days[-1])).isoformat())
        except ValueError:
            return None
    d2, m2, y2 = found[-1]
    end_month = MONTHS[m2.lower().rstrip(".")]
    end_year = int(y2) if y2 else context_year
    # Jour de début : premier nombre du texte, mois du début si présent
    start = re.match(r"\s*(?:du\s+|le\s+)?(\d{1,2})\s*(?:er)?\s*(?:(" + MONTH_RE + r")\.?)?(?:\s+(\d{4}))?", text, re.I)
    d1 = int(start.group(1)) if start else int(d2)
    start_month = MONTHS[start.group(2).lower().rstrip(".")] if start and start.group(2) else end_month
    start_year = int(start.group(3)) if start and start.group(3) else (
        end_year - 1 if start_month > end_month else end_year)
    try:
        return (datetime.date(start_year, start_month, d1).isoformat(),
                datetime.date(end_year, end_month, int(d2)).isoformat())
    except ValueError:
        return None


def parse_sample(cell):
    text = clean(cell).get_text(" ", strip=True).replace("\xa0", " ")
    m = re.search(r"\d[\d  ]*", text)
    return int(re.sub(r"\D", "", m.group(0))) if m else None


def pollster(cell):
    cell = clean(cell)
    link = cell.find("a", class_="external") or cell.find("a")
    name = cell.get_text(" ", strip=True)
    href = link.get("href") if link is not None else None
    return name, href


def header_columns(grid):
    """Nom de chaque colonne d'après la ligne d'en-tête contenant les candidats."""
    columns = None
    for row in grid:
        if not all(c.name == "th" for c in row):
            break
        names = []
        for cell in row:
            text = clean(cell).get_text(" ", strip=True)
            link = clean(cell).find("a", title=True)
            low = text.lower()
            if low.startswith("sondeur") or low.startswith("institut"):
                names.append("@sondeur")
            elif low.startswith("date") or low.startswith("dernier jour"):
                names.append("@date")
            elif low.startswith("échantillon"):
                names.append("@echantillon")
            elif low.startswith("autres"):
                names.append("@autres")
            elif low.startswith("candidat"):
                names.append("@generique")  # « Candidat LR » : personne non précisée
            elif link is not None and not link.get("title", "").startswith("Fichier:"):
                names.append(canonical_name(link["title"]))
            else:
                names.append(None)
        if sum(1 for n in names if n and not n.startswith("@")) >= 2:
            columns = names
    return columns


def parse_table(table, context_year, context_month=None):
    grid = expand_grid(table)
    columns = header_columns(grid)
    if columns is None or "@date" not in columns:
        return [], ["table sans en-tête reconnu"]
    rows, problems = [], []
    for row in grid:
        if not row or row[0].name != "td" or len(row) < len(columns):
            continue
        cells = dict()
        for name, cell in zip(columns, row):
            cells.setdefault(name, cell)
        institute, href = pollster(cells["@sondeur"])
        if not institute:
            continue  # ligne de couleurs
        date_text = clean(cells["@date"]).get_text(" ", strip=True)
        dates = parse_dates(date_text, context_year, context_month)
        if dates is None:
            problems.append(f"date illisible: {institute} {date_text!r}")
            continue
        scores, generic, seen = {}, False, set()
        for name, cell in zip(columns, row):
            if name is None or name in ("@sondeur", "@date", "@echantillon"):
                continue
            if id(cell) in seen:  # cellule fusionnée sur plusieurs colonnes : une seule fois
                continue
            seen.add(id(cell))
            default = None if name in ("@autres", "@generique") else name
            for cand, value in parse_value_cell(cell, default):
                if cand is None and name == "@generique":
                    generic = True
                cand = "Autres" if cand is None else canonical_name(cand)
                scores[cand] = scores.get(cand, 0) + value
        if generic:
            problems.append(f"hypothèse à candidat générique ignorée : {institute} {date_text}")
            continue
        if len([c for c in scores if c != "Autres"]) < 2:
            continue
        rows.append({
            "sondeur": institute,
            "debut": dates[0],
            "fin": dates[1],
            "echantillon": parse_sample(cells["@echantillon"]) if "@echantillon" in cells else None,
            "source": href,
            "scores": scores,
        })
    return rows, problems


def parse_events(table):
    """Lignes « jalon » d'une seule cellule : « X officialise sa candidature (19 septembre 2026). »"""
    events = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) != 1 or int(re.sub(r"\D", "", cells[0].get("colspan", "1")) or 1) < 5:
            continue
        text = " ".join(clean(cells[0]).get_text(" ", strip=True).split())
        text = re.sub(r"\s+([,.)])", r"\1", text).replace("( ", "(")
        m = re.search(r"\(([^()]*\d{4})\s*\)\s*\.?$", text)
        dates = parse_dates(m.group(1), None) if m else None
        if dates is None:
            continue
        label = re.sub(r"\b([dlDL])' ", r"\1'", text[:m.start()].strip().rstrip("."))
        events.append({"date": dates[1], "texte": label})
    return events


def section_year(heading_text, fallback):
    years = re.findall(r"(20\d\d)", heading_text)
    return int(years[-1]) if years else fallback


# « Sondages concernant le premier tour », ou simplement « Premier tour » (page 2012),
# mais pas « Effectués après le premier tour »
ROUND_HEADING = re.compile(
    r"^(?:sondages?\s+(?:concernant|sur|pour)\s+(?:le\s+)?)?(premier|second|deuxième)\s+tour$", re.I)


def caption_context(table, year):
    """« Mars 2017 », « Sondages de 2015 » : mois et année des dates abrégées du tableau."""
    cap = table.find("caption")
    if cap is None:
        return year, None
    text = cap.get_text(" ", strip=True).lower()
    years = re.findall(r"(19\d\d|20\d\d)", text)
    month = next((MONTHS[m] for m in sorted(MONTHS, key=len, reverse=True) if re.search(rf"\b{m}\b", text)), None)
    return (int(years[-1]) if years else year), month


def parse_page(data, default_year, skip_headings=("Autres",)):
    """
    Tous les tableaux d'une page « Liste de sondages sur l'élection présidentielle » :
    renvoie (premier tour, second tour, jalons, problèmes).
    """
    soup = BeautifulSoup(data["parse"]["text"], "html.parser")
    first, second, problems, events = [], [], [], []
    round_kind, year, heading, excluded = None, default_year, "", False
    for el in soup.find_all(["h2", "h3", "h4", "h5", "table"]):
        if el.name != "table":
            # Pages « Liste de sondages… » : le tour est dans le titre de niveau 2.
            # Articles d'élection : « Sondages » (niveau 2) puis « Sondages concernant
            # le premier tour » (niveau 3). Les reports de voix ne sont pas des duels.
            text = el.get_text(" ", strip=True)
            m = ROUND_HEADING.search(text.strip())
            if m:
                round_kind = "first" if m.group(1).lower() == "premier" else "second"
            elif el.name == "h2":
                round_kind = None
            excluded = "report" in text.lower()
            year = section_year(text, year)
            heading = text
            continue
        if "wikitable" not in el.get("class", []) or round_kind is None or excluded:
            continue
        if round_kind == "first" and heading.strip() in skip_headings:
            continue  # scénarios atypiques (candidats génériques, etc.)
        if round_kind == "first":
            for ev in parse_events(el):
                if ev not in events:
                    events.append(ev)
        table_year, table_month = caption_context(el, year)
        rows, probs = parse_table(el, table_year, table_month)
        problems += [f"[{heading}] {p}" for p in probs]
        for r in rows:
            r["section"] = heading
        (first if round_kind == "first" else second).extend(rows)

    for r in first + second:
        total = sum(r["scores"].values())
        r["total_brut"] = round(total, 2)
        if not 90 <= total <= 110:
            problems.append(f"total {total:.1f} % : {r['sondeur']} {r['fin']} {r.get('section')}")
    second = [r for r in second if len(r["scores"]) == 2]
    return (sorted(first, key=lambda r: r["fin"]), sorted(second, key=lambda r: r["fin"]),
            sorted(events, key=lambda e: e["date"]), problems)
