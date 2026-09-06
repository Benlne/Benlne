#!/usr/bin/env python3
"""A partir de combien de grilles est-on sur de rembourser sa mise ?

Reponse courte : jamais. Ce script le demontre de trois facons.

1. L'esperance de gain par grille est inferieure au prix de la grille. Chaque
   euro mise rapporte structurellement moins d'un euro.
2. La probabilite de finir en benefice DIMINUE quand on joue plus de grilles :
   la loi des grands nombres garantit la convergence vers la perte moyenne, pas
   vers le remboursement.
3. Meme la couverture integrale des 139 838 160 combinaisons — seule facon
   d'etre certain de toucher le jackpot — coute plus cher que le jackpot.

Les gains des rangs 2 a 13 sont indicatifs : ces rangs sont pari-mutuel, le
montant reel depend du nombre de gagnants a chaque tirage.
"""

from __future__ import annotations

import argparse
import math
import random

from analyse_euromillions import proba_rang

PRIX_GRILLE = 2.50
COMBINAISONS = 139_838_160

# Gains moyens indicatifs en France, par (bons numeros, bonnes etoiles).
GAINS = {
    (5, 1): 300_000, (5, 0): 30_000, (4, 2): 2_000, (4, 1): 150, (4, 0): 60,
    (3, 2): 80, (2, 2): 20, (3, 1): 13, (3, 0): 10, (1, 2): 9, (2, 1): 7, (2, 0): 4,
}


def esperance_par_grille(jackpot: float) -> float:
    return proba_rang(5, 2) * jackpot + sum(
        proba_rang(b, e) * gain for (b, e), gain in GAINS.items()
    )


def _poisson(rng: random.Random, lam: float) -> int:
    """Tirage de Poisson : Knuth pour les petites moyennes, approximation
    normale au-dela (ou la methode de Knuth deviendrait trop lente)."""
    if lam <= 0:
        return 0
    if lam < 30:
        seuil, k, produit = math.exp(-lam), 0, rng.random()
        while produit > seuil:
            k += 1
            produit *= rng.random()
        return k
    return max(0, round(rng.gauss(lam, math.sqrt(lam))))


def simule(n_grilles: int, jackpot: float, tirages: int, rng: random.Random) -> list[float]:
    """Retourne le gain net de `tirages` joueurs ayant chacun joue n_grilles."""
    rangs = [((5, 2), jackpot)] + [(k, float(v)) for k, v in GAINS.items()]
    lambdas = [(proba_rang(b, e) * n_grilles, gain) for (b, e), gain in rangs]
    cout = n_grilles * PRIX_GRILLE
    return [
        sum(_poisson(rng, lam) * gain for lam, gain in lambdas) - cout
        for _ in range(tirages)
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jackpot", type=float, default=98e6, help="jackpot en euros")
    ap.add_argument("--simulations", type=int, default=20000)
    ap.add_argument("--graine", type=int, default=20260906)
    args = ap.parse_args()

    rng = random.Random(args.graine)
    esp = esperance_par_grille(args.jackpot)

    print(f"Jackpot retenu : {args.jackpot / 1e6:.0f} M€ | grille a {PRIX_GRILLE:.2f} €\n")
    print(f"1. Espérance de gain par grille : {esp:.3f} € "
          f"soit {esp / PRIX_GRILLE * 100:.1f} % de la mise.")
    print(f"   Perte moyenne garantie : {PRIX_GRILLE - esp:.3f} € par grille jouée.\n")

    print("2. Probabilité de finir en bénéfice selon le nombre de grilles :\n")
    print(f"   {'Grilles':>12} | {'Mise totale':>14} | {'P(bénéfice)':>11} | {'Résultat médian':>16}")
    print("   " + "-" * 62)
    for n in (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000):
        nets = simule(n, args.jackpot, args.simulations, rng)
        nets.sort()
        p_benef = sum(1 for x in nets if x > 0) / len(nets)
        median = nets[len(nets) // 2]
        mise = n * PRIX_GRILLE
        print(f"   {n:>12,} | {mise:>12,.0f} € | {p_benef:>10.2%} | {median:>14,.0f} €"
              .replace(",", " "))

    print(f"\n3. Couverture intégrale des {COMBINAISONS:,} combinaisons :".replace(",", " "))
    cout = COMBINAISONS * PRIX_GRILLE
    print(f"   Coût : {cout / 1e6:,.1f} M€ pour un jackpot de {args.jackpot / 1e6:.0f} M€."
          .replace(",", " "))
    print(f"   Déficit avant même de compter les autres gagnants : "
          f"{(cout - args.jackpot) / 1e6:,.1f} M€.".replace(",", " "))
    n50 = math.log(0.5) / math.log(1 - proba_rang(5, 2))
    print(f"   Pour une seule chance sur deux de toucher le jackpot : "
          f"{n50:,.0f} grilles, soit {n50 * PRIX_GRILLE / 1e6:,.0f} M€."
          .replace(",", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
