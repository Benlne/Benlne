# EuroMillions — probabilités théoriques et fréquences observées

Fenêtre analysée : **06/09/2022 → 04/09/2026**, **418 tirages** (2090 boules et 836 étoiles tirées).

## 1. Les probabilités réelles (calcul exact, indépendant de l'historique)

Grilles possibles : C(50,5) × C(12,2) = 2 118 760 × 66 = **139 838 160**.

| Rang | Bons numéros | Bonnes étoiles | Probabilité | Soit |
|---:|:---:|:---:|---:|:---|
| 1 | 5 | 2 | 7.151e-09 | 1 sur 139 838 160 |
| 2 | 5 | 1 | 1.430e-07 | 1 sur 6 991 908 |
| 3 | 5 | 0 | 3.218e-07 | 1 sur 3 107 515 |
| 4 | 4 | 2 | 1.609e-06 | 1 sur 621 503 |
| 5 | 4 | 1 | 3.218e-05 | 1 sur 31 075 |
| 6 | 4 | 0 | 7.241e-05 | 1 sur 13 811 |
| 7 | 3 | 2 | 7.080e-05 | 1 sur 14 125 |
| 8 | 2 | 2 | 1.015e-03 | 1 sur 985 |
| 9 | 3 | 1 | 1.416e-03 | 1 sur 706 |
| 10 | 3 | 0 | 3.186e-03 | 1 sur 314 |
| 11 | 1 | 2 | 5.327e-03 | 1 sur 188 |
| 12 | 2 | 1 | 2.029e-02 | 1 sur 49 |
| 13 | 2 | 0 | 4.566e-02 | 1 sur 22 |

Probabilité de gagner **quelque chose** avec une grille : 0.0771 (1 sur 13), soit environ 7.7 % des grilles.

## 2. Fréquences observées — boules (1 à 50)

Espérance sous l'hypothèse d'équité : **41.8 sorties** par numéro.

| # | Sorties | Écart / attendu | Écart actuel (tirages) |
|---:|---:|---:|---:|
| 1 | 26 | -15.8 | 19 |
| 2 | 42 | +0.2 | 1 |
| 3 | 38 | -3.8 | 5 |
| 4 | 39 | -2.8 | 24 |
| 5 | 36 | -5.8 | 6 |
| 6 | 36 | -5.8 | 20 |
| 7 | 45 | +3.2 | 2 |
| 8 | 51 | +9.2 | 3 |
| 9 | 38 | -3.8 | 5 |
| 10 | 48 | +6.2 | 1 |
| 11 | 38 | -3.8 | 0 |
| 12 | 37 | -4.8 | 0 |
| 13 | 51 | +9.2 | 39 |
| 14 | 44 | +2.2 | 2 |
| 15 | 36 | -5.8 | 4 |
| 16 | 47 | +5.2 | 3 |
| 17 | 44 | +2.2 | 7 |
| 18 | 41 | -0.8 | 23 |
| 19 | 42 | +0.2 | 0 |
| 20 | 40 | -1.8 | 31 |
| 21 | 42 | +0.2 | 14 |
| 22 | 25 | -16.8 | 24 |
| 23 | 46 | +4.2 | 1 |
| 24 | 48 | +6.2 | 10 |
| 25 | 39 | -2.8 | 9 |
| 26 | 38 | -3.8 | 8 |
| 27 | 42 | +0.2 | 0 |
| 28 | 38 | -3.8 | 2 |
| 29 | 52 | +10.2 | 6 |
| 30 | 35 | -6.8 | 3 |
| 31 | 38 | -3.8 | 10 |
| 32 | 33 | -8.8 | 33 |
| 33 | 44 | +2.2 | 16 |
| 34 | 53 | +11.2 | 9 |
| 35 | 57 | +15.2 | 8 |
| 36 | 38 | -3.8 | 12 |
| 37 | 46 | +4.2 | 1 |
| 38 | 27 | -14.8 | 5 |
| 39 | 39 | -2.8 | 6 |
| 40 | 38 | -3.8 | 5 |
| 41 | 46 | +4.2 | 22 |
| 42 | 52 | +10.2 | 2 |
| 43 | 29 | -12.8 | 32 |
| 44 | 51 | +9.2 | 19 |
| 45 | 51 | +9.2 | 2 |
| 46 | 46 | +4.2 | 0 |
| 47 | 51 | +9.2 | 1 |
| 48 | 50 | +8.2 | 3 |
| 49 | 40 | -1.8 | 6 |
| 50 | 37 | -4.8 | 5 |

**Les 10 plus sortis :** 35 (57), 34 (53), 29 (52), 42 (52), 44 (51), 47 (51), 45 (51), 8 (51), 13 (51), 48 (50)

**Les 10 moins sortis :** 22 (25), 1 (26), 38 (27), 43 (29), 32 (33), 30 (35), 6 (36), 5 (36), 15 (36), 50 (37)


Test du khi-deux d'uniformité : χ² = 61.9 pour 49 ddl, **p = 0.103**.

Sous tirage parfaitement équitable, le numéro le moins sorti tombe typiquement vers 29 sorties (5e centile 24) et le plus sorti vers 56 (95e centile 62) — observé ici : 25 et 57.

## 3. Fréquences observées — étoiles (1 à 12)

Espérance sous l'hypothèse d'équité : **69.7 sorties** par étoile.

| ★ | Sorties | Écart / attendu | Écart actuel (tirages) |
|---:|---:|---:|---:|
| 1 | 73 | +3.3 | 7 |
| 2 | 73 | +3.3 | 7 |
| 3 | 73 | +3.3 | 1 |
| 4 | 57 | -12.7 | 0 |
| 5 | 77 | +7.3 | 1 |
| 6 | 71 | +1.3 | 2 |
| 7 | 65 | -4.7 | 22 |
| 8 | 67 | -2.7 | 6 |
| 9 | 75 | +5.3 | 2 |
| 10 | 72 | +2.3 | 5 |
| 11 | 57 | -12.7 | 11 |
| 12 | 76 | +6.3 | 0 |

Test du khi-deux d'uniformité : χ² = 7.4 pour 11 ddl, **p = 0.769**.

Plage attendue sous équité : min ≈ 57, max ≈ 82 — observé : 57 et 77.

## 4. Forme des grilles tirées

- Somme des 5 boules : min 42, max 202, moyenne 130.1, médiane 132 — 76 % des tirages entre 100 et 175.
- Nombre de boules paires par tirage : 0 → 9 tirages (2 %), 1 → 60 tirages (14 %), 2 → 145 tirages (35 %), 3 → 139 tirages (33 %), 4 → 58 tirages (14 %), 5 → 7 tirages (2 %)
- Nombre de boules ≤ 25 par tirage : 0 → 10 tirages (2 %), 1 → 73 tirages (17 %), 2 → 132 tirages (32 %), 3 → 140 tirages (33 %), 4 → 53 tirages (13 %), 5 → 10 tirages (2 %)
- Au moins deux boules consécutives : 38 % des tirages.
- Boules reprises d'un tirage au suivant : 0.47 en moyenne.
- Grilles de 5 boules déjà sorties deux fois dans la fenêtre : 0.

## 5. Lecture

- Boules : distribution **compatible avec un tirage équitable** (p = 0.103).
- Étoiles : distribution **compatible avec un tirage équitable** (p = 0.769).
- Les écarts de fréquence visibles au tableau sont l'amplitude normale du hasard sur un échantillon de cette taille : ils ne se prolongent pas au tirage suivant.
- La seule quantité qu'un joueur contrôle est le **partage du gain** : jouer une grille de forme rare (somme extrême, numéros > 31, pas de suite arithmétique) ne change pas la probabilité de gagner, mais réduit le nombre de gagnants avec qui partager.
