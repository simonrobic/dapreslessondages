# SPDX-License-Identifier: AGPL-3.0-or-later
# D’après les sondages — reprend Depuis 1958 de Victor Poughon (2017). Voir NOTICE.md.
"""
Image de partage du jour (1200 × 630, format Open Graph) : le chiffre de la
prévision, les chances des principaux candidats et le rappel « au même stade ».
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from common import date_fr

W, H = 1200, 630
PAD = 64
# Mêmes teintes que la palette du site (mode clair)
SURFACE, INK, INK_2, MUTED, GRID = "#fcfbf9", "#141413", "#474641", "#6b6a64", "#e9e7e1"
SLOTS = ["#a9a8a1", "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# Les polices du site (variables, SIL OFL), avec leur graisse ; polices système en secours
SITE_FONTS = Path(__file__).resolve().parent.parent / "templates" / "assets" / "fonts"
FONTS = {
    "serif-bold": ("source-serif-4-latin.woff2", [600, 60]),
    "sans-bold": ("ibm-plex-sans-latin.woff2", [600]),
    "sans": ("ibm-plex-sans-latin.woff2", [400]),
}
FALLBACK = {
    "serif-bold": ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "sans-bold": ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "sans": ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(kind, size):
    name, axes = FONTS[kind]
    try:
        f = ImageFont.truetype(str(SITE_FONTS / name), size)
        f.set_variation_by_axes(axes)
        return f
    except OSError:
        for path in FALLBACK[kind]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def fit(draw, text, kind, size, max_width):
    """Plus grande taille (≤ size) pour que le texte tienne dans max_width."""
    while size > 12:
        f = font(kind, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return font(kind, size)


def pct(p):
    v = 100 * p
    if 0 < v < 1:
        return "< 1 %"
    if 99 < v < 100:
        return "> 99 %"
    return f"{v:.0f} %"


def make(payload, site_name, site_domain, out_path):
    sc = payload["scenarios"][0]
    names = sc["candidats"]
    fav = names[0]
    meta = payload["candidats"]

    img = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(img)

    # En-tête
    d.text((PAD, PAD - 8), site_name, font=font("serif-bold", 38), fill=INK)
    stage = f"Présidentielle {payload['annee']} · J-{payload['jours_avant']}"
    f_stage = font("sans", 26)
    d.text((W - PAD - d.textlength(stage, font=f_stage), PAD - 2), stage, font=f_stage, fill=MUTED)
    d.line((PAD, PAD + 50, W - PAD, PAD + 50), fill=INK, width=2)

    # Chiffre principal
    big = pct(sc["stats"][fav]["p_victoire"])
    f_big = font("serif-bold", 150)
    top = PAD + 76
    d.text((PAD - 6, top), big, font=f_big, fill=INK)
    x_cap = PAD + d.textlength(big, font=f_big) + 28
    cap_w = W - PAD - x_cap
    d.text((x_cap, top + 22), "de chances de victoire pour", font=font("sans", 30), fill=INK_2)
    d.text((x_cap, top + 62), fav, font=fit(d, fav, "sans-bold", 50, cap_w), fill=INK)
    d.text((x_cap, top + 124), "dans le scénario de candidatures le plus sondé", font=fit(d, "dans le scénario de candidatures le plus sondé", "sans", 26, cap_w), fill=MUTED)

    # Barres : chances des quatre premiers
    y = top + 196
    f_label, f_val = font("sans", 26), font("sans-bold", 26)
    label_w = 230
    bar_max = W - 2 * PAD - label_w - 90
    for c in names[:4]:
        p = sc["stats"][c]["p_victoire"]
        d.text((PAD, y), meta[c]["court"], font=f_label, fill=INK)
        x0 = PAD + label_w
        w = max(4, int(bar_max * p))
        color = SLOTS[meta[c]["slot"]]
        d.rounded_rectangle((x0, y + 4, x0 + w, y + 28), radius=5, fill=color)
        d.rectangle((x0, y + 4, x0 + 6, y + 28), fill=color)  # extrémité carrée côté axe
        d.text((x0 + w + 12, y), pct(p), font=f_val, fill=INK)
        y += 38

    # Rappel « au même stade » : le cas le plus parlant où le favori n'a pas gagné
    misses = [c for c in payload.get("comparaisons", [])
              if c["etapes"].get(payload["jours_avant"], {}).get("issue") not in (None, "gagne")]
    if misses:
        c = max(misses, key=lambda c: c["etapes"][payload["jours_avant"]]["p_favori"])
        snap = c["etapes"][payload["jours_avant"]]
        note = (f"Au même stade en {snap['date'][:4]}, {snap['favori']} était en tête à {pct(snap['p_favori'])}. "
                f"{c['elu']} l'a emporté.")
    else:
        note = "Prévision probabiliste, à partir de tous les sondages publiés."
    d.text((PAD, H - PAD - 50), note, font=fit(d, note, "sans", 26, W - 2 * PAD), fill=INK_2)
    foot = f"{site_domain} · mise à jour le {date_fr(payload['date_prevision'])}"
    d.text((PAD, H - PAD - 12), foot, font=font("sans", 22), fill=MUTED)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, optimize=True)
    return out_path
