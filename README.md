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
