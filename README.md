# D’après les sondages

Modèle probabiliste de l'élection présidentielle française, à partir de tous les
sondages publiés : [dapreslessondages.fr](https://dapreslessondages.fr).

D’après les sondages est la suite de **Depuis 1958**, créé en 2017 par
**Victor Poughon** ([victorpoughon.fr](https://victorpoughon.fr),
[github.com/victorpoughon](https://github.com/victorpoughon)). Il en reprend la
méthode bayésienne et l'historique des sondages depuis 1981, ajoute la
prévision 2027 et conserve les licences d'origine (voir [NOTICE.md](NOTICE.md)).

## Ce que publie le site

- **Prévision 2027** : chances de victoire, de qualification et scores attendus
  de chaque candidat, selon le scénario de candidatures, et leur évolution.
- **Au même stade de la campagne** : ce que le même modèle donnait, à la même
  distance du vote, à chaque présidentielle depuis 1958, et qui a gagné.
- **Préoccupations des Français** : ce qui inquiétait les Français à chaque
  stade (Eurobaromètre), comparé aux professions de foi des élus, et un score
  d'alignement provisoire pour les candidats 2027.
- **Sondages**, **historique** du modèle depuis 1965 et **méthodologie**.

## Reproduire les calculs

```sh
uv venv --python 3.13 && uv pip install -r pyproject.toml
.venv/bin/python scripts/build.py
```

Le site est généré, entièrement statique, dans `site/`.

## Organisation

| Chemin | Rôle |
|---|---|
| `scripts/wikipedia.py` | Lecture des tableaux de sondages Wikipédia (hypothèses de 1er tour, duels, jalons de campagne) |
| `scripts/fetch_2027.py` | Télécharge et convertit les sondages 2027 |
| `scripts/import_history.py` | Convertit l'historique 1965–2022 (dépôt d'origine, NSPPolls, Wikipédia) et écrit les résultats officiels |
| `scripts/share_image.py` | Image de partage du jour (Open Graph, 1200 × 630) |
| `scripts/eurobarometer.py` | Préoccupations des Français : Eurobaromètre standard 2005–2025, colonne France, thèmes stables |
| `scripts/programmes.py` | Professions de foi des élus (1965–2022) : téléchargement, découpage en passages, parts par thème |
| `scripts/candidats_2027.py` | Textes programmatiques des candidats 2027 (sites officiels) : découpage en passages, parts par thème, pour le score d'alignement provisoire |
| `scripts/model.py` | Modèle : Dirichlet-multinomial, poids du temps, scénarios, Monte-Carlo des deux tours |
| `scripts/build.py` | Calcule les prévisions et génère les pages |
| `scripts/common.py` | Noms des candidats, familles politiques, couleurs |
| `templates/` | Gabarits HTML (Jinja2), feuille de style et graphiques (JS sans dépendance) |
| `data/polls/<année>.json` | Sondages au format commun (une entrée par hypothèse) |
| `data/resultats.json` | Résultats officiels 1965–2022 (Conseil constitutionnel) |
| `data/raw/` | Sources brutes : dépôt `depuis1958/sondages`, NSPPolls, page Wikipédia |

## Ce qui change par rapport à 2017

- Poids du temps `1 / (1 + (j/60)^1,5)` au lieu d'une droite nulle à 130 jours :
  une prévision est possible un an avant le vote.
- A priori de Dirichlet de 0,25 au lieu de 1, pour ne pas gonfler les petits
  candidats loin du scrutin.
- Regroupement automatique des hypothèses de candidatures en scénarios.
- Fenêtres de 60 jours (1er tour) et 150 jours (2d tour).
- Correction de deux duels de 1988 dont les colonnes étaient inversées dans le
  dépôt d'origine.

## Licences

Les licences du projet d'origine sont conservées (détail dans [NOTICE.md](NOTICE.md)) :

- **code** : [GNU AGPL v3](LICENSE) ou toute version ultérieure ;
- **textes et graphiques du site** : [CC BY-NC 3.0 FR](https://creativecommons.org/licenses/by-nc/3.0/fr/) ;
- **données** : licence de leur source, voir [data/LICENCE.md](data/LICENCE.md)
  (CC BY-SA 3.0 FR pour l'historique d'origine, MIT pour NSPPolls, CC BY-SA 4.0
  pour Wikipédia).

L'AGPL demande que le code reste accessible aux visiteurs du site : chaque page
renvoie à ce dépôt. Si vous publiez votre propre version, indiquez l'adresse de
votre code dans la variable d'environnement `SOURCE_CODE`.

L'historique Git de ce dépôt commence par les commits de Victor Poughon sur le
code de Depuis 1958 (avril 2017, repris de la copie archivée
[cljoly/depuis1958](https://github.com/cljoly/depuis1958)) : la relance s'inscrit
à leur suite.
