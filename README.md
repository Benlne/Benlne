# Analyse probabiliste EuroMillions

Analyse des tirages EuroMillions sur les **4 dernières années** (06/09/2022 → 04/09/2026,
**418 tirages**), sans dépendance externe (Python 3 standard uniquement).

Le rapport complet est dans **[RESULTATS.md](RESULTATS.md)**.

## Ce que fait le script

| Bloc | Contenu |
|---|---|
| Probabilités théoriques | Les 13 rangs de gain calculés exactement par combinatoire — indépendants de l'historique |
| Fréquences observées | Nombre de sorties de chaque boule (1–50) et étoile (1–12), écart à l'espérance, écart actuel |
| Test du khi-deux | Implémenté à la main (gamma incomplète régulière) : l'écart à l'uniforme est-il significatif ? |
| Simulation Monte-Carlo | Plage dans laquelle le numéro le moins / le plus sorti tombe naturellement sous tirage équitable |
| Forme des grilles | Somme, parité, répartition haut/bas, consécutifs, reprises d'un tirage au suivant |

## Résultat principal

Sur les 418 tirages de la fenêtre :

- **Boules** : χ² = 61,9 (49 ddl), **p = 0,103**
- **Étoiles** : χ² = 7,4 (11 ddl), **p = 0,769**

Aucune des deux distributions ne s'écarte significativement de l'uniforme. Le 35 (57 sorties)
et le 22 (25 sorties) encadrent l'amplitude que le hasard produit spontanément sur un
échantillon de cette taille (min attendu ≈ 29, max attendu ≈ 56 sous tirage parfaitement
équitable). Ces fréquences **ne portent aucune information sur le tirage suivant** : chaque
tirage est indépendant, la probabilité d'une grille donnée reste 1 sur 139 838 160.

La seule variable qu'un joueur contrôle réellement est le **partage du gain** : jouer une
grille de forme peu populaire (numéros > 31, somme éloignée de 130, pas de suite ni de motif
de grille) ne change pas la probabilité de gagner, mais réduit le nombre de gagnants avec qui
partager un éventuel jackpot.

## Utilisation

```bash
# Rapport sur la fenêtre 4 ans fournie
python3 analyse_euromillions.py data/euromillions_4ans.csv --md RESULTATS.md

# Sur un autre historique, en ne gardant que les N dernières années
python3 analyse_euromillions.py mon_historique.csv --annees 10
```

Format CSV attendu :

```
date,n1,n2,n3,n4,n5,s1,s2
2026-09-04,11,12,19,27,46,4,12
```

## Données

`data/euromillions_4ans.csv` — 418 tirages (209 mardis, 209 vendredis), extraits de
l'archive publique [daowa89/lottery-archive](https://github.com/daowa89/lottery-archive)
(source amont : win2day.at). Contrôles passés : aucune date dupliquée, aucun doublon de
numéro dans un tirage, boules dans 1–50, étoiles dans 1–12. Le dernier tirage de la fenêtre
(04/09/2026 : 11-12-19-27-46 ★4-12) a été recoupé avec les résultats publiés.

L'historique complet depuis 2004 est récupérable ainsi :

```bash
curl -O https://raw.githubusercontent.com/daowa89/lottery-archive/main/eu/euromillions/results.csv
python3 analyse_euromillions.py results.csv --annees 4
```

> Le format actuel (5 numéros sur 50 + 2 étoiles sur 12) date de septembre 2016. Une analyse
> sur un historique plus long doit être coupée à cette date, sinon les fréquences des étoiles
> 11 et 12 sont mécaniquement sous-estimées.

## Choisir une grille : `choix_grille.py`

Aucune grille n'a plus de chances de sortir qu'une autre. Le seul levier réel est le
**partage du gain** : les joueurs ne cochent pas au hasard, donc certaines grilles sont
jouées par des milliers de personnes et d'autres par presque personne.

`choix_grille.py` énumère les 2 118 760 combinaisons de 5 boules, leur attribue un score
de popularité estimée et tire au sort une grille parmi les moins populaires :

| Critère | Effet |
|---|---|
| Numéro ≤ 31 (jour de naissance) | +3 — le biais le plus massif |
| Numéro ≤ 12 (mois) | +1 supplémentaire |
| Porte-bonheur (3, 7, 9, 11, 13, 17, 21, 23, 27) | +2 |
| Numéro « chaud » des 4 dernières années | +1,5 — les tableaux de fréquences sont publics |
| 4+ numéros alignés sur le bulletin (8 colonnes, mise en page FDJ) | +3 par numéro excédentaire |
| Suite arithmétique complète | +8 |
| Paire de numéros consécutifs | **−1,5** — les joueurs les évitent |
| 1 ou 50 (bords du bulletin) | −0,5 |

```bash
python3 choix_grille.py --grilles 5
```

237 grilles atteignent le score minimal : à l'intérieur de cet ensemble le choix est
arbitraire, le script y tire au sort (entropie système par défaut, `--graine` pour
reproduire).

> Les poids viennent de régularités documentées du comportement des joueurs, pas de
> données de mises réelles — la FDJ ne publie pas la répartition des grilles jouées.
> C'est une estimation, et elle ne change **pas** la probabilité de gagner : l'espérance
> de gain reste négative.

## Rentabilité : `rentabilite.py`

Répond à « à partir de combien de grilles suis-je sûr de rembourser ma mise ? ».
Réponse : aucun nombre. Le script le montre de trois façons — espérance par grille,
probabilité de bénéfice en fonction du nombre de grilles, et coût de la couverture
intégrale des 139 838 160 combinaisons.

```bash
python3 rentabilite.py --jackpot 98e6
```

Résultat central : l'espérance est de **48,6 % de la mise**, mais le résultat **médian**
est de **−82 %**. L'écart vient du jackpot, qui tire la moyenne vers le haut sans jamais
tomber. Jouer plus de grilles ne rapproche pas du remboursement : ça rend la perte
moyenne plus certaine.

> Les gains des rangs 2 à 13 sont indicatifs — ces rangs sont pari-mutuel, le montant
> réel dépend du nombre de gagnants à chaque tirage.

## Vérifier un tirage : `verifier.py`

```bash
python3 verifier.py --tirage 11,12,19,27,46 --etoiles 4,12
```

Compare le tirage à la grille enregistrée dans `ma_grille.json` et annonce le rang de
gain atteint (ou l'absence de gain). Une autre grille se teste avec `--grille` et
`--mes-etoiles`.

> `ma_grille.json` ne contient **pas** le code My Million : c'est un identifiant de
> ticket, il n'a rien à faire dans un dépôt.
