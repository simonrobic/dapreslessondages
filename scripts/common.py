# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""Chemins, noms et métadonnées partagés par les scripts."""
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Orthographes rencontrées dans les sources -> nom de référence
ALIASES = {
    "François Mitterand": "François Mitterrand",
    "Eric Zemmour": "Éric Zemmour",
    "Edouard Philippe": "Édouard Philippe",
    "Edouard Balladur": "Édouard Balladur",
    "Valéry Giscard D'Estaing": "Valéry Giscard d'Estaing",
    "Jean-Luc Melenchon": "Jean-Luc Mélenchon",
    "Valerie Pecresse": "Valérie Pécresse",
    "Valérie Pecresse": "Valérie Pécresse",
    "Segolene Royal": "Ségolène Royal",
    "Raphael Glucksmann": "Raphaël Glucksmann",
    "Francois Hollande": "François Hollande",
    "Francois Fillon": "François Fillon",
    "Francois Bayrou": "François Bayrou",
    "Francois Ruffin": "François Ruffin",
    "Benoit Hamon": "Benoît Hamon",
    "Eric Piolle": "Éric Piolle",
    "Eric Ciotti": "Éric Ciotti",
}

# Famille politique, de la gauche vers la droite : sert à l'ordre d'affichage
# et à la couleur. Les couleurs sont les 8 teintes de la palette catégorielle
# validée (daltonisme, contraste) et évoquent les couleurs usuelles des partis :
# 1 bleu, 2 orange, 3 aqua, 4 jaune, 5 magenta, 6 vert, 7 violet, 8 rouge.
FAMILIES = {
    "extreme-gauche":  {"label": "Extrême gauche",  "slot": 8, "order": 0},
    "communiste":      {"label": "Communiste",      "slot": 8, "order": 1},
    "gauche-radicale": {"label": "Gauche radicale", "slot": 8, "order": 2},
    "socialiste":      {"label": "Socialiste",      "slot": 5, "order": 3},
    "divers-gauche":   {"label": "Divers gauche",   "slot": 5, "order": 4},
    "ecologiste":      {"label": "Écologiste",      "slot": 6, "order": 5},
    "centre":          {"label": "Centre",          "slot": 4, "order": 6},
    "centre-droit":    {"label": "Centre droit",    "slot": 3, "order": 7},
    "droite":          {"label": "Droite",          "slot": 1, "order": 8},
    "souverainiste":   {"label": "Souverainiste",   "slot": 2, "order": 9},
    "extreme-droite":  {"label": "Extrême droite",  "slot": 7, "order": 10},
    "autre":           {"label": "Autre",           "slot": 0, "order": 11},
}
# Deux candidats d'une même famille dans la même élection : couleur dédiée
SLOT_OVERRIDES = {"Éric Zemmour": 2, "Sarah Knafo": 2, "Bruno Mégret": 2, "Marion Maréchal": 2}
FALLBACK_SLOTS = [6, 2, 3, 4, 5, 1, 7, 8]

CANDIDATES = {
    # Extrême gauche
    "Arlette Laguiller": ("LO", "extreme-gauche"),
    "Nathalie Arthaud": ("LO", "extreme-gauche"),
    "Daniel Gluckstein": ("PT", "extreme-gauche"),
    "Gérard Schivardi": ("PT", "extreme-gauche"),
    "Olivier Besancenot": ("LCR", "extreme-gauche"),
    "Philippe Poutou": ("NPA", "extreme-gauche"),
    "Pierre Boussel": ("MPPT", "extreme-gauche"),
    "Pierre Juquin": ("DVG", "extreme-gauche"),
    "Anasse Kazib": ("RP", "extreme-gauche"),
    # Communistes
    "Georges Marchais": ("PCF", "communiste"),
    "André Lajoinie": ("PCF", "communiste"),
    "Robert Hue": ("PCF", "communiste"),
    "Marie-George Buffet": ("PCF", "communiste"),
    "Fabien Roussel": ("PCF", "communiste"),
    # Gauche radicale
    "Jean-Luc Mélenchon": ("LFI", "gauche-radicale"),
    "François Ruffin": ("Debout !", "gauche-radicale"),
    "José Bové": ("ALT", "gauche-radicale"),
    "Clémentine Autain": ("APRES", "gauche-radicale"),
    # Socialistes et apparentés
    "François Mitterrand": ("PS", "socialiste"),
    "Lionel Jospin": ("PS", "socialiste"),
    "Ségolène Royal": ("PS", "socialiste"),
    "François Hollande": ("PS", "socialiste"),
    "Benoît Hamon": ("PS", "socialiste"),
    "Anne Hidalgo": ("PS", "socialiste"),
    "Olivier Faure": ("PS", "socialiste"),
    "Raphaël Glucksmann": ("PP", "socialiste"),
    "Bernard Cazeneuve": ("LND", "socialiste"),
    "Manuel Valls": ("PS", "socialiste"),
    "Vincent Peillon": ("PS", "socialiste"),
    "Sylvia Pinel": ("PRG", "divers-gauche"),
    "Karim Bouamrane": ("PS", "socialiste"),
    "Boris Vallaud": ("PS", "socialiste"),
    "Carole Delga": ("PS", "socialiste"),
    "Jérôme Guedj": ("PS", "socialiste"),
    "Emmanuel Maurel": ("GRS", "gauche-radicale"),
    "Arnaud Montebourg": ("DVG", "divers-gauche"),
    "Michel Crépeau": ("MRG", "divers-gauche"),
    "Christiane Taubira": ("PRG", "divers-gauche"),
    "Jean-Pierre Chevènement": ("MDC", "divers-gauche"),
    "Huguette Bouchardeau": ("PSU", "divers-gauche"),
    # Écologistes
    "Brice Lalonde": ("ECO", "ecologiste"),
    "Antoine Waechter": ("VEC", "ecologiste"),
    "Dominique Voynet": ("VEC", "ecologiste"),
    "Noël Mamère": ("VEC", "ecologiste"),
    "Corinne Lepage": ("CAP21", "ecologiste"),
    "Eva Joly": ("EELV", "ecologiste"),
    "Yannick Jadot": ("EELV", "ecologiste"),
    "Cécile Duflot": ("EELV", "ecologiste"),
    "Nicolas Hulot": ("DIV", "ecologiste"),
    "Michèle Rivasi": ("EELV", "ecologiste"),
    "Marine Tondelier": ("LE", "ecologiste"),
    "Sandrine Rousseau": ("LE", "ecologiste"),
    "Éric Piolle": ("EELV", "ecologiste"),
    "Hélène Thouy": ("PA", "autre"),
    # Centre
    "François Bayrou": ("MoDem", "centre"),
    "Emmanuel Macron": ("EM", "centre"),
    "Gabriel Attal": ("RE", "centre"),
    "Gérald Darmanin": ("RE", "centre"),
    "Bruno Le Maire": ("RE", "centre"),
    "Sébastien Lecornu": ("RE", "centre"),
    "Élisabeth Borne": ("RE", "centre"),
    "Yaël Braun-Pivet": ("RE", "centre"),
    "Jean Castex": ("DVD", "centre-droit"),
    "Raymond Barre": ("UDF", "centre-droit"),
    "Valéry Giscard d'Estaing": ("UDF", "centre-droit"),
    "Édouard Philippe": ("HOR", "centre-droit"),
    "Dominique de Villepin": ("LFE", "centre-droit"),
    "Alain Madelin": ("DL", "centre-droit"),
    "Christine Boutin": ("FRS", "droite"),
    # Droite
    "Jacques Chirac": ("RPR", "droite"),
    "Michel Debré": ("DVD", "droite"),
    "Marie-France Garaud": ("DVD", "droite"),
    "Édouard Balladur": ("RPR", "droite"),
    "Nicolas Sarkozy": ("UMP", "droite"),
    "François Fillon": ("LR", "droite"),
    "Alain Juppé": ("LR", "droite"),
    "Jean-François Copé": ("LR", "droite"),
    "Nathalie Kosciusko-Morizet": ("LR", "droite"),
    "Henri Guaino": ("DVD", "droite"),
    "Rama Yade": ("DVD", "centre-droit"),
    "Valérie Pécresse": ("LR", "droite"),
    "Xavier Bertrand": ("LR", "droite"),
    "Laurent Wauquiez": ("LR", "droite"),
    "Bruno Retailleau": ("LR", "droite"),
    "David Lisnard": ("NE", "droite"),
    "Michel Barnier": ("LR", "droite"),
    "François Baroin": ("LR", "droite"),
    "Rachida Dati": ("LR", "droite"),
    "Éric Ciotti": ("LR", "droite"),
    "Philippe Juvin": ("LR", "droite"),
    "Denis Payre": ("DVD", "droite"),
    "Jean-Frédéric Poisson": ("VIA", "droite"),
    "Charles Pasqua": ("RPF", "souverainiste"),
    "Hervé Morin": ("NC", "centre"),
    "Jean-Christophe Lagarde": ("UDI", "centre"),
    "Frédéric Nihous": ("CPNT", "droite"),
    "Jean Saint-Josse": ("CPNT", "droite"),
    # Souverainistes
    "Philippe de Villiers": ("MPF", "souverainiste"),
    "Nicolas Dupont-Aignan": ("DLF", "souverainiste"),
    "François Asselineau": ("UPR", "souverainiste"),
    "Florian Philippot": ("LP", "souverainiste"),
    "Jean Lassalle": ("RES", "souverainiste"),
    "Jacques Cheminade": ("S&P", "autre"),
    "Natacha Polony": ("DIV", "souverainiste"),
    # Années 1960-1970
    "Charles de Gaulle": ("UNR", "droite"),
    "Georges Pompidou": ("UDR", "droite"),
    "Jacques Chaban-Delmas": ("UDR", "droite"),
    "Jean Royer": ("DVD", "droite"),
    "Edgar Faure": ("RAD", "centre-droit"),
    "Jean Lecanuet": ("CD", "centre"),
    "Alain Poher": ("CD", "centre"),
    "Pierre Marcilhacy": ("CL", "centre-droit"),
    "Gaston Defferre": ("SFIO", "socialiste"),
    "Jacques Duclos": ("PCF", "communiste"),
    "Alain Krivine": ("LC", "extreme-gauche"),
    "Louis Ducatel": ("DIV", "autre"),
    "Marcel Barbu": ("DIV", "autre"),
    "Roger Garaudy": ("DIV", "autre"),
    "Jean-Louis Tixier-Vignancour": ("CT", "extreme-droite"),
    "René Dumont": ("ECO", "ecologiste"),
    "Émile Muller": ("MDSF", "divers-gauche"),
    "Bertrand Renouvin": ("NAR", "autre"),
    "Jean-Claude Sebag": ("MFE", "autre"),
    "Guy Héraud": ("PFE", "autre"),
    # Personnalités testées dans les sondages
    "Michel Rocard": ("PS", "socialiste"),
    "Jacques Delors": ("PS", "socialiste"),
    "Jack Lang": ("PS", "socialiste"),
    "Laurent Fabius": ("PS", "socialiste"),
    "Martine Aubry": ("PS", "socialiste"),
    "Bertrand Delanoë": ("PS", "socialiste"),
    "Dominique Strauss-Kahn": ("PS", "socialiste"),
    "Bernard Tapie": ("MRG", "divers-gauche"),
    "François Léotard": ("UDF", "centre-droit"),
    "Jean-Louis Borloo": ("PR", "centre"),
    "Michèle Alliot-Marie": ("LR", "droite"),
    # Extrême droite
    "Jean-Marie Le Pen": ("FN", "extreme-droite"),
    "Bruno Mégret": ("MNR", "extreme-droite"),
    "Marine Le Pen": ("RN", "extreme-droite"),
    "Jordan Bardella": ("RN", "extreme-droite"),
    "Éric Zemmour": ("REC", "extreme-droite"),
    "Marion Maréchal": ("IDL", "extreme-droite"),
    "Sarah Knafo": ("REC", "extreme-droite"),
}


MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
             "septembre", "octobre", "novembre", "décembre"]


def date_fr(iso):
    import datetime
    d = datetime.date.fromisoformat(iso) if isinstance(iso, str) else iso
    day = "1er" if d.day == 1 else str(d.day)
    return f"{day} {MONTHS_FR[d.month - 1]} {d.year}"


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


_BY_ASCII = {_strip_accents(k).lower(): k for k in CANDIDATES}


_BY_SURNAME = {}
for _full in CANDIDATES:
    _BY_SURNAME.setdefault(_strip_accents(_full.split(" ", 1)[1]).lower(), []).append(_full)
    if " de " in _full:  # « Villepin », « Villiers »
        _BY_SURNAME.setdefault(_strip_accents(_full.split(" de ", 1)[1]).lower(), []).append(_full)


def canonical_name(name):
    name = " ".join(name.replace("\xa0", " ").split())
    name = re.sub(r"\s*\((?:homme|femme) politique[^)]*\)$", "", name)
    name = ALIASES.get(name, name)
    if name in CANDIDATES:
        return name
    key = _strip_accents(name).lower()
    if key in _BY_ASCII:
        return _BY_ASCII[key]
    # Nom de famille seul (cellules « <small>Lisnard</small> » sans lien)
    matches = _BY_SURNAME.get(key, [])
    return matches[0] if len(matches) == 1 else name


# Étiquette différente selon l'élection
PARTY_BY_YEAR = {
    ("François Mitterrand", 1965): "FGDS",
    ("Valéry Giscard d'Estaing", 1974): "RI",
    ("Michel Rocard", 1969): "PSU",
    ("Alain Krivine", 1974): "FCR",
    ("Jacques Chirac", 2002): "RPR",
}


def candidate_meta(name, year=None):
    party, family = CANDIDATES.get(name, ("", "autre"))
    party = PARTY_BY_YEAR.get((name, year), party)
    fam = FAMILIES[family]
    return {"parti": party, "famille": fam["label"], "ordre": fam["order"],
            "slot": SLOT_OVERRIDES.get(name, fam["slot"])}


def assign_slots(groups, minor, together):
    """
    Une teinte par candidat d'importance ; gris (0) pour les autres.
    `groups` : listes de candidats par ordre d'importance, la première étant
    servie en premier (candidats de la prévision actuelle, puis historique).
    Deux candidats jamais testés ensemble (Le Pen / Bardella, Retailleau /
    Wauquiez) sont des alternatives et partagent la teinte de leur famille.
    `together(a, b)` dit s'ils figurent dans une même hypothèse.
    """
    slots = {}

    def rivals(name):
        return {slots[o] for o in slots if slots[o] and together(name, o)}

    for group in groups:
        pending = []
        # 1er passage : chacun prend la teinte de sa famille si aucun rival ne l'a
        for name in group:
            if name in minor:
                slots[name] = 0
                continue
            wanted = candidate_meta(name)["slot"]
            if wanted and wanted not in rivals(name):
                slots[name] = wanted
            else:
                pending.append(name)
        # 2e passage : les autres prennent une teinte libre, par ordre d'importance
        for name in pending:
            taken = rivals(name)
            slots[name] = next((s for s in FALLBACK_SLOTS if s not in taken), 0)
    return slots


SHORT_NAMES = {
    "Valéry Giscard d'Estaing": "Giscard d'Estaing",
    "Dominique de Villepin": "Villepin",
    "Jean-Marie Le Pen": "J.-M. Le Pen",
}


def short_name(name):
    """Nom de famille pour l'affichage compact (« Le Pen », « de Villiers »)."""
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    parts = name.split(" ")
    for i, p in enumerate(parts[1:], start=1):
        if p[:1].islower() or p in ("Le", "La", "Du", "Saint-Josse"):
            return " ".join(parts[i:])
    return parts[-1] if len(parts) > 1 else name
