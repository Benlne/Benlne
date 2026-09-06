#!/usr/bin/env python3
"""Choix d'une grille EuroMillions par minimisation du risque de partage.

Aucune grille n'a plus de chances de sortir qu'une autre : la probabilite est
1 / 139 838 160 pour toutes. En revanche les joueurs ne cochent PAS au hasard, donc
certaines grilles sont jouees par des milliers de personnes et d'autres par presque
personne. A gain egal, une grille peu jouee se partage moins.

Ce script enumere les 2 118 760 combinaisons de 5 boules, leur attribue un score de
popularite estimee, et tire au sort une grille parmi les moins populaires.

Les poids viennent de regularites documentees du comportement des joueurs
(preference pour les dates de naissance, les petits nombres, les numeros
"porte-bonheur", les motifs geometriques sur le bulletin, les numeros "chauds"),
pas de donnees de mises reelles : la FDJ ne publie pas la repartition des grilles
jouees. C'est donc une estimation, pas une mesure.
"""

from __future__ import annotations

import argparse
import itertools
import random

from analyse_euromillions import (
    N_BOULES, K_BOULES, N_ETOILES, K_ETOILES, charger, compter,
)

# Numeros surjoues pour raisons superstitieuses ou culturelles.
PORTE_BONHEUR = {3, 7, 9, 11, 13, 17, 21, 23, 27}

# Le bulletin FDJ presente les 50 numeros en 5 lignes de 10.
ligne = lambda n: (n - 1) // 10
colonne = lambda n: (n - 1) % 10


def score_popularite(grille: tuple[int, ...], chauds: set[int]) -> float:
    """Estimation (basse = grille peu jouee) de la popularite d'une grille."""
    s = 0.0

    # 1. Dates de naissance : le biais le plus massif et le mieux documente.
    #    Les jours 1-31 sont surjoues, les 1-12 (mois) encore davantage.
    s += 3.0 * sum(1 for n in grille if n <= 31)
    s += 1.0 * sum(1 for n in grille if n <= 12)

    # 2. Numeros porte-bonheur.
    s += 2.0 * sum(1 for n in grille if n in PORTE_BONHEUR)

    # 3. Numeros "chauds" : les tableaux de frequences sont publics, les joueurs
    #    qui les suivent convergent sur les memes numeros.
    s += 1.5 * sum(1 for n in grille if n in chauds)

    # 4. Motifs geometriques sur le bulletin : seul un alignement VISIBLE
    #    (4 numeros ou plus sur la meme ligne ou la meme colonne) traduit un
    #    coche par motif. Trois numeros dans la meme dizaine n'est pas un motif,
    #    c'est le cas le plus frequent d'un tirage ordinaire.
    for extraire in (ligne, colonne):
        occurrences = {}
        for n in grille:
            occurrences[extraire(n)] = occurrences.get(extraire(n), 0) + 1
        s += 3.0 * sum(c - 1 for c in occurrences.values() if c >= 4)

    # 5. Suites arithmetiques completes (5, 10, 15, 20, 25...).
    ecarts = {b - a for a, b in zip(grille, grille[1:])}
    if len(ecarts) == 1:
        s += 8.0

    # 6. Grille entierement dans la meme dizaine.
    if len({ligne(n) for n in grille}) == 1:
        s += 4.0

    # 7. Numeros consecutifs : les joueurs les EVITENT (ils les jugent
    #    "impossibles"), donc en jouer une paire rend la grille plus rare.
    if any(n + 1 in grille for n in grille):
        s -= 1.5

    # 8. Le 50 et le 1 sont sous-joues (effet de bord du bulletin) : bonus leger.
    s -= 0.5 * sum(1 for n in grille if n in (1, 50))

    return s


def score_etoiles(paire: tuple[int, int]) -> float:
    s = 0.0
    s += 2.0 * sum(1 for n in paire if n <= 6)       # biais vers les petits nombres
    s += 2.0 * sum(1 for n in paire if n in (3, 7))  # porte-bonheur
    if paire[1] - paire[0] == 1:
        s -= 1.0                                     # paires collees, evitees
    return s


def meilleures(candidats, score, marge=0.0):
    notes = [(score(c), c) for c in candidats]
    mini = min(n for n, _ in notes)
    return [c for n, c in notes if n <= mini + marge]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", default="data/euromillions_4ans.csv")
    ap.add_argument("--grilles", type=int, default=1, help="nombre de grilles a proposer")
    ap.add_argument("--graine", type=int, default=None,
                    help="graine aleatoire (par defaut : vraie entropie systeme)")
    args = ap.parse_args()

    tirages = charger(args.csv)
    chauds = {n for n, _ in compter(tirages, "boules").most_common(10)}
    print(f"Historique : {len(tirages)} tirages | numeros 'chauds' exclus : "
          f"{sorted(chauds)}\n")

    boules = meilleures(itertools.combinations(range(1, N_BOULES + 1), K_BOULES),
                        lambda g: score_popularite(g, chauds))
    etoiles = meilleures(itertools.combinations(range(1, N_ETOILES + 1), K_ETOILES),
                         score_etoiles)
    print(f"Grilles de boules au score minimal : {len(boules)} sur "
          f"{len(list(itertools.combinations(range(1, N_BOULES + 1), K_BOULES))):,}"
          .replace(",", " "))
    print(f"Paires d'etoiles au score minimal : {len(etoiles)} sur 66\n")

    # Le choix a l'interieur de cet ensemble est arbitraire : toutes ces grilles
    # sont equivalentes du point de vue du hasard comme de la popularite. On tire
    # donc au sort, avec l'entropie systeme par defaut.
    rng = random.Random(args.graine) if args.graine is not None else random.SystemRandom()
    for i in range(args.grilles):
        b = rng.choice(boules)
        e = rng.choice(etoiles)
        print(f"Grille {i + 1} : {' - '.join(f'{n:02d}' for n in b)}   "
              f"etoiles {e[0]} et {e[1]}   (somme {sum(b)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
