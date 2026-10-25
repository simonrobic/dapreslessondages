# Licences des données

| Fichiers | Source | Licence |
|---|---|---|
| `polls/1981.json` à `polls/2017.json`, `raw/sondages/` | [depuis1958/sondages](https://github.com/depuis1958/sondages), Victor Poughon et contributeurs | [CC BY-SA 3.0 FR](https://creativecommons.org/licenses/by-sa/3.0/fr/) |
| `polls/1965.json` à `polls/1974.json` ; dans `polls/1981.json` à `polls/2017.json`, les sondages antérieurs au début du dépôt d'origine ; `raw/wikipedia-*.json` | Wikipédia : articles « Élection présidentielle française de … » (1965 à 1995) et pages « Liste de sondages sur l'élection présidentielle française de … » (2002 à 2027), contributeurs de Wikipédia | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr) |
| `polls/2022.json`, `raw/nsppolls/` | [NSPPolls](https://github.com/nsppolls/nsppolls), contributeurs de NSPPolls | MIT (texte complet dans [raw/nsppolls/LICENCE.md](raw/nsppolls/LICENCE.md)), avec la demande de créditer NSPPolls et de faire un lien vers le projet |
| `polls/2027.json`, `raw/wikipedia-2027.json` | [Wikipédia, « Liste de sondages sur l'élection présidentielle française de 2027 »](https://fr.wikipedia.org/wiki/Liste_de_sondages_sur_l%27%C3%A9lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027), contributeurs de Wikipédia | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr) |
| `resultats.json` | Conseil constitutionnel, résultats officiels | données publiques |
| `preoccupations/eurobarometre-france.json` | Eurobaromètre standard, Commission européenne, via [data.europa.eu](https://data.europa.eu) (tableaux par pays, colonne France, regroupés en thèmes) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.fr) |
| `programmes/codage.json`, `programmes/professions-de-foi.json` | Classement par thème des professions de foi des élus, établi par D’après les sondages ; les textes eux-mêmes ne sont pas redistribués (seuls leurs premiers mots, pour vérification), ils restent la propriété de leurs auteurs | CC BY-SA 4.0 pour le classement |
| `programmes/codage-candidats-2027.json`, `programmes/candidats-2027.json` | Classement par thème des textes programmatiques des candidats 2027, publiés sur leurs sites officiels et ceux de leurs partis ; mêmes règles : seuls les premiers mots de chaque passage sont repris, les textes restent la propriété de leurs auteurs | CC BY-SA 4.0 pour le classement |

## Modifications apportées

Les données ont été **extraites et mises en forme** par D’après les sondages :
conversion au format commun (une entrée par hypothèse de sondage), noms des
candidats harmonisés, valeurs « < 1 » converties en 0,5, dates abrégées
complétées, sondages hors période écartés. Seule correction de fond : deux duels
de 1988 du dépôt d'origine, dont les colonnes étaient inversées.

Les auteurs des pages Wikipédia sont listés dans l'historique de chaque page
(lien « Afficher l'historique », par exemple
<https://fr.wikipedia.org/w/index.php?title=Liste_de_sondages_sur_l%27%C3%A9lection_pr%C3%A9sidentielle_fran%C3%A7aise_de_2027&action=history>).

Les fichiers dérivés (conversions au format commun, corrections, exports CSV et
JSON de `site/donnees/`) sont distribués sous la même licence que leur source :
CC BY-SA pour les données issues du dépôt d'origine et de Wikipédia, MIT pour
celles issues de NSPPolls.
