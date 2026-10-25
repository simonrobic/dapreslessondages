# Crédits et licences

## Projet d'origine

**Depuis 1958** a été créé en 2017 par **Victor Poughon**
([victorpoughon.fr](https://victorpoughon.fr), [github.com/victorpoughon](https://github.com/victorpoughon)) :
site de prévision de l'élection présidentielle française, modèle bayésien et
jeu de données des sondages depuis 1981.

- Code du modèle : `github.com/depuis1958/depuis1958` (dépôt d'origine, une copie
  est conservée sur [github.com/cljoly/depuis1958](https://github.com/cljoly/depuis1958)),
  sous licence GNU AGPL v3.
- Sondages : [github.com/depuis1958/sondages](https://github.com/depuis1958/sondages),
  sous licence CC BY-SA 3.0 FR, avec les contributions de Guillaume Rozier
  (rozierguillaume), Labruunt, alexouxou, Mehdi Rejraji (ridem) et niamiot
  pendant la campagne 2017.
- Site (textes, graphiques) : sous licence CC BY-NC 3.0 FR.

**D’après les sondages** ([dapreslessondages.fr](https://dapreslessondages.fr))
reprend la méthode du modèle d'origine (agrégation
Dirichlet-multinomiale, dernier sondage par institut, précision constante de
400 répondants, simulation Monte-Carlo des deux tours) ainsi que ses données, et
garde ses licences.

## Licences de cette version

| Partie | Licence | Fichiers |
|---|---|---|
| Code | [GNU AGPL v3](LICENSE) ou toute version ultérieure | `scripts/`, `templates/assets/charts.js`, `update.sh` |
| Textes et graphiques du site | [CC BY-NC 3.0 FR](https://creativecommons.org/licenses/by-nc/3.0/fr/) | `templates/`, pages générées dans `site/` |
| Données | voir [data/LICENCE.md](data/LICENCE.md) | `data/`, `site/donnees/` |
| Polices Source Serif 4 (Adobe) et IBM Plex Sans (IBM) | [SIL Open Font License 1.1](https://openfontlicense.org), textes dans le dossier | `templates/assets/fonts/` |
