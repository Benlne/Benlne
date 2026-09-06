#!/usr/bin/env python3
"""Verifie une grille EuroMillions contre le resultat d'un tirage.

Usage :
    python3 verifier.py --tirage 11,12,19,27,46 --etoiles 4,12
    python3 verifier.py --tirage ... --etoiles ... --grille 39,40,43,46,50 --mes-etoiles 10,11

Sans --grille, la grille jouee enregistree dans ma_grille.json est utilisee.
"""

from __future__ import annotations

import argparse
import json
import os

from analyse_euromillions import RANGS, proba_rang

ICI = os.path.dirname(os.path.abspath(__file__))
GRILLE_ENREGISTREE = os.path.join(ICI, "ma_grille.json")


def rang_officiel(bons: int, bonnes: int) -> int | None:
    """Numero de rang (1 a 13), ou None si la combinaison n'est pas gagnante."""
    couple = (bons, bonnes)
    return RANGS.index(couple) + 1 if couple in RANGS else None


def liste(texte: str) -> tuple[int, ...]:
    return tuple(sorted(int(x) for x in texte.replace(" ", "").split(",")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tirage", required=True, help="les 5 numeros tires, separes par des virgules")
    ap.add_argument("--etoiles", required=True, help="les 2 etoiles tirees")
    ap.add_argument("--grille", help="ma grille (defaut : celle de ma_grille.json)")
    ap.add_argument("--mes-etoiles", help="mes etoiles (defaut : celles de ma_grille.json)")
    args = ap.parse_args()

    if args.grille and args.mes_etoiles:
        mes_boules, mes_etoiles = liste(args.grille), liste(args.mes_etoiles)
        origine = "ligne de commande"
    else:
        with open(GRILLE_ENREGISTREE, encoding="utf-8") as f:
            enr = json.load(f)
        mes_boules = tuple(enr["boules"])
        mes_etoiles = tuple(enr["etoiles"])
        origine = f"{os.path.basename(GRILLE_ENREGISTREE)} (tirage du {enr['tirage']})"

    tirage, etoiles = liste(args.tirage), liste(args.etoiles)
    for nom, valeurs, attendu, borne in (
        ("tirage", tirage, 5, 50), ("etoiles", etoiles, 2, 12),
        ("grille", mes_boules, 5, 50), ("mes etoiles", mes_etoiles, 2, 12),
    ):
        if len(valeurs) != attendu or not all(1 <= v <= borne for v in valeurs):
            raise SystemExit(f"Erreur : '{nom}' doit contenir {attendu} valeurs "
                             f"distinctes entre 1 et {borne} (recu : {valeurs}).")

    boules_ok = sorted(set(mes_boules) & set(tirage))
    etoiles_ok = sorted(set(mes_etoiles) & set(etoiles))

    print(f"Grille jouee ({origine}) : "
          f"{' - '.join(f'{n:02d}' for n in mes_boules)} + etoiles {', '.join(map(str, mes_etoiles))}")
    print(f"Tirage                   : "
          f"{' - '.join(f'{n:02d}' for n in tirage)} + etoiles {', '.join(map(str, etoiles))}")
    print()
    print(f"Numeros trouves : {len(boules_ok)} " + (f"({boules_ok})" if boules_ok else ""))
    print(f"Etoiles trouvees : {len(etoiles_ok)} " + (f"({etoiles_ok})" if etoiles_ok else ""))
    print()

    rang = rang_officiel(len(boules_ok), len(etoiles_ok))
    if rang is None:
        print("=> GRILLE PERDANTE : aucun rang de gain atteint.")
    else:
        p = proba_rang(len(boules_ok), len(etoiles_ok))
        print(f"=> GAGNANT AU RANG {rang} "
              f"({len(boules_ok)} numeros + {len(etoiles_ok)} etoile(s))")
        print(f"   Probabilite de ce rang : 1 sur {1 / p:,.0f}".replace(",", " "))
        if rang == 1:
            print("   JACKPOT.")
    print("\nRappel : le code My Million est tire separement et se verifie sur "
          "l'appli FDJ — il n'a aucun lien avec les numeros de la grille.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
