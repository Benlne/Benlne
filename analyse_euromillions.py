#!/usr/bin/env python3
"""Analyse probabiliste des tirages EuroMillions.

Deux choses distinctes sont produites :

1. Les probabilites THEORIQUES, calculees exactement par combinatoire.
   Elles ne dependent d'aucun historique : le tirage est uniforme et sans memoire.
2. Les frequences OBSERVEES sur la fenetre d'historique fournie, avec un test
   du khi-deux qui dit si l'ecart a l'uniforme est significatif ou du simple bruit.

Usage :
    python3 analyse_euromillions.py [chemin_csv] [--md rapport.md]

Le CSV attendu a pour colonnes : date,n1,n2,n3,n4,n5,s1,s2
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import math
import random
import sys
from dataclasses import dataclass

N_BOULES, K_BOULES = 50, 5
N_ETOILES, K_ETOILES = 12, 2

C = math.comb


# --------------------------------------------------------------------------
# Probabilites theoriques
# --------------------------------------------------------------------------

COMBINAISONS_TOTALES = C(N_BOULES, K_BOULES) * C(N_ETOILES, K_ETOILES)


def proba_rang(bons_numeros: int, bonnes_etoiles: int) -> float:
    """Probabilite d'obtenir exactement `bons_numeros` boules et `bonnes_etoiles`
    etoiles avec une grille simple."""
    p_num = (
        C(K_BOULES, bons_numeros)
        * C(N_BOULES - K_BOULES, K_BOULES - bons_numeros)
        / C(N_BOULES, K_BOULES)
    )
    p_eto = (
        C(K_ETOILES, bonnes_etoiles)
        * C(N_ETOILES - K_ETOILES, K_ETOILES - bonnes_etoiles)
        / C(N_ETOILES, K_ETOILES)
    )
    return p_num * p_eto


# Les 13 rangs de gain officiels, du rang 1 (jackpot) au rang 13.
RANGS = [
    (5, 2), (5, 1), (5, 0), (4, 2), (4, 1), (4, 0),
    (3, 2), (2, 2), (3, 1), (3, 0), (1, 2), (2, 1), (2, 0),
]


def table_des_rangs() -> list[tuple[int, int, int, float]]:
    """Retourne [(rang, boules, etoiles, probabilite)] pour les 13 rangs gagnants."""
    return [(i + 1, b, e, proba_rang(b, e)) for i, (b, e) in enumerate(RANGS)]


def proba_gain_quelconque() -> float:
    return sum(p for _, _, _, p in table_des_rangs())


# --------------------------------------------------------------------------
# Fonctions statistiques (sans dependance externe)
# --------------------------------------------------------------------------


def _gamma_p_serie(a: float, x: float) -> float:
    """Fonction gamma incomplete reguliere P(a, x), developpement en serie."""
    somme = terme = 1.0 / a
    for n in range(1, 1000):
        terme *= x / (a + n)
        somme += terme
        if abs(terme) < abs(somme) * 1e-15:
            break
    return somme * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_fraction(a: float, x: float) -> float:
    """Fonction gamma incomplete reguliere Q(a, x), fraction continue (Lentz)."""
    minuscule = 1e-300
    b = x + 1.0 - a
    c = 1.0 / minuscule
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < minuscule:
            d = minuscule
        c = b + an / c
        if abs(c) < minuscule:
            c = minuscule
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def p_valeur_khi2(khi2: float, ddl: int) -> float:
    """P(X >= khi2) pour une loi du khi-deux a `ddl` degres de liberte."""
    a, x = ddl / 2.0, khi2 / 2.0
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_p_serie(a, x)
    return _gamma_q_fraction(a, x)


# --------------------------------------------------------------------------
# Chargement et analyse de l'historique
# --------------------------------------------------------------------------


@dataclass
class Tirage:
    date: dt.date
    boules: tuple[int, ...]
    etoiles: tuple[int, ...]


def charger(chemin: str, annees: float | None = None) -> list[Tirage]:
    tirages = []
    with open(chemin, newline="", encoding="utf-8") as f:
        for ligne in csv.DictReader(f):
            tirages.append(
                Tirage(
                    date=dt.date.fromisoformat(ligne["date"]),
                    boules=tuple(sorted(int(ligne[f"n{i}"]) for i in range(1, 6))),
                    etoiles=tuple(sorted(int(ligne[f"s{i}"]) for i in range(1, 3))),
                )
            )
    tirages.sort(key=lambda t: t.date)
    if annees is not None and tirages:
        fin = tirages[-1].date
        debut = fin - dt.timedelta(days=round(365.2425 * annees))
        tirages = [t for t in tirages if t.date > debut]
    return tirages


@dataclass
class TestUniformite:
    khi2: float
    ddl: int
    p_valeur: float
    attendu: float


def test_uniformite(compte: dict[int, int], n_faces: int, n_tirages: int, k: int) -> TestUniformite:
    attendu = n_tirages * k / n_faces
    khi2 = sum((compte.get(i, 0) - attendu) ** 2 / attendu for i in range(1, n_faces + 1))
    ddl = n_faces - 1
    return TestUniformite(khi2, ddl, p_valeur_khi2(khi2, ddl), attendu)


def compter(tirages: list[Tirage], champ: str) -> collections.Counter:
    c = collections.Counter()
    for t in tirages:
        c.update(getattr(t, champ))
    return c


def ecarts_actuels(tirages: list[Tirage], champ: str, n_faces: int) -> dict[int, int]:
    """Nombre de tirages ecoules depuis la derniere sortie de chaque numero."""
    dernier = {i: None for i in range(1, n_faces + 1)}
    for rang, t in enumerate(tirages):
        for v in getattr(t, champ):
            dernier[v] = rang
    total = len(tirages)
    return {i: (total - 1 - r if r is not None else total) for i, r in dernier.items()}


def etendue_attendue(n_tirages: int, n_faces: int, k: int, simulations: int = 20000,
                     graine: int = 20260906) -> tuple[float, float, float, float]:
    """Distribution simulee du min et du max des frequences sous hypothese d'uniformite.

    Retourne (min_5e_centile, min_median, max_median, max_95e_centile) : la plage
    dans laquelle le numero le moins sorti et le plus sorti tombent naturellement
    quand le tirage est parfaitement equitable.
    """
    rng = random.Random(graine)
    faces = list(range(1, n_faces + 1))
    mins, maxs = [], []
    for _ in range(simulations):
        compte = [0] * (n_faces + 1)
        for _ in range(n_tirages):
            for v in rng.sample(faces, k):
                compte[v] += 1
        mins.append(min(compte[1:]))
        maxs.append(max(compte[1:]))
    mins.sort()
    maxs.sort()
    q = lambda tab, p: tab[int(p * (len(tab) - 1))]
    return q(mins, 0.05), q(mins, 0.5), q(maxs, 0.5), q(maxs, 0.95)


def profil_grilles(tirages: list[Tirage]) -> dict[str, object]:
    """Caracteristiques de forme des grilles tirees (utiles pour choisir une grille
    peu populaire, pas pour predire les numeros)."""
    sommes = [sum(t.boules) for t in tirages]
    pairs = collections.Counter(sum(1 for b in t.boules if b % 2 == 0) for t in tirages)
    bas = collections.Counter(sum(1 for b in t.boules if b <= 25) for t in tirages)
    consecutifs = sum(
        1 for t in tirages if any(b + 1 in t.boules for b in t.boules)
    )
    dizaines = collections.Counter(
        len({min((b - 1) // 10, 4) for b in t.boules}) for t in tirages
    )
    repetes = 0
    for precedent, courant in zip(tirages, tirages[1:]):
        repetes += len(set(precedent.boules) & set(courant.boules))
    return {
        "somme_min": min(sommes),
        "somme_max": max(sommes),
        "somme_moyenne": sum(sommes) / len(sommes),
        "somme_mediane": sorted(sommes)[len(sommes) // 2],
        "part_somme_centrale": sum(1 for s in sommes if 100 <= s <= 175) / len(sommes),
        "pairs": pairs,
        "bas": bas,
        "part_consecutifs": consecutifs / len(tirages),
        "dizaines": dizaines,
        "repetition_moyenne": repetes / (len(tirages) - 1),
        "grilles_deja_sorties": len(tirages) - len({t.boules for t in tirages}),
    }


# --------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------


def formate_1_sur(p: float) -> str:
    return "1 sur " + f"{1 / p:,.0f}".replace(",", "\u202f")


def rapport(tirages: list[Tirage]) -> str:
    n = len(tirages)
    debut, fin = tirages[0].date, tirages[-1].date
    boules = compter(tirages, "boules")
    etoiles = compter(tirages, "etoiles")
    t_boules = test_uniformite(boules, N_BOULES, n, K_BOULES)
    t_etoiles = test_uniformite(etoiles, N_ETOILES, n, K_ETOILES)
    ec_boules = ecarts_actuels(tirages, "boules", N_BOULES)
    ec_etoiles = ecarts_actuels(tirages, "etoiles", N_ETOILES)
    sim_b = etendue_attendue(n, N_BOULES, K_BOULES)
    sim_e = etendue_attendue(n, N_ETOILES, K_ETOILES)
    profil = profil_grilles(tirages)

    L = []
    a = L.append
    a("# EuroMillions — probabilités théoriques et fréquences observées\n")
    a(f"Fenêtre analysée : **{debut:%d/%m/%Y} → {fin:%d/%m/%Y}**, "
      f"**{n} tirages** ({n * K_BOULES} boules et {n * K_ETOILES} étoiles tirées).\n")

    a("## 1. Les probabilités réelles (calcul exact, indépendant de l'historique)\n")
    esp = lambda v: f"{v:,}".replace(",", "\u202f")
    a(f"Grilles possibles : C(50,5) × C(12,2) = {esp(C(N_BOULES, K_BOULES))} × "
      f"{C(N_ETOILES, K_ETOILES)} = **{esp(COMBINAISONS_TOTALES)}**.\n")
    a("| Rang | Bons numéros | Bonnes étoiles | Probabilité | Soit |")
    a("|---:|:---:|:---:|---:|:---|")
    for rang, b, e, p in table_des_rangs():
        a(f"| {rang} | {b} | {e} | {p:.3e} | {formate_1_sur(p)} |")
    pg = proba_gain_quelconque()
    a(f"\nProbabilité de gagner **quelque chose** avec une grille : {pg:.4f} "
      f"({formate_1_sur(pg)}), soit environ {pg * 100:.1f} % des grilles.\n")

    a("## 2. Fréquences observées — boules (1 à 50)\n")
    a(f"Espérance sous l'hypothèse d'équité : **{t_boules.attendu:.1f} sorties** par numéro.\n")
    a("| # | Sorties | Écart / attendu | Écart actuel (tirages) |")
    a("|---:|---:|---:|---:|")
    for num in range(1, N_BOULES + 1):
        c = boules.get(num, 0)
        a(f"| {num} | {c} | {c - t_boules.attendu:+.1f} | {ec_boules[num]} |")

    top = boules.most_common()
    a("\n**Les 10 plus sortis :** " + ", ".join(f"{v} ({c})" for v, c in top[:10]))
    a("\n**Les 10 moins sortis :** " + ", ".join(f"{v} ({c})" for v, c in reversed(top[-10:])))
    a(f"\n\nTest du khi-deux d'uniformité : χ² = {t_boules.khi2:.1f} pour "
      f"{t_boules.ddl} ddl, **p = {t_boules.p_valeur:.3f}**.")
    a(f"\nSous tirage parfaitement équitable, le numéro le moins sorti tombe typiquement "
      f"vers {sim_b[1]:.0f} sorties (5e centile {sim_b[0]:.0f}) et le plus sorti vers "
      f"{sim_b[2]:.0f} (95e centile {sim_b[3]:.0f}) — observé ici : "
      f"{top[-1][1]} et {top[0][1]}.\n")

    a("## 3. Fréquences observées — étoiles (1 à 12)\n")
    a(f"Espérance sous l'hypothèse d'équité : **{t_etoiles.attendu:.1f} sorties** par étoile.\n")
    a("| ★ | Sorties | Écart / attendu | Écart actuel (tirages) |")
    a("|---:|---:|---:|---:|")
    for num in range(1, N_ETOILES + 1):
        c = etoiles.get(num, 0)
        a(f"| {num} | {c} | {c - t_etoiles.attendu:+.1f} | {ec_etoiles[num]} |")
    tope = etoiles.most_common()
    a(f"\nTest du khi-deux d'uniformité : χ² = {t_etoiles.khi2:.1f} pour "
      f"{t_etoiles.ddl} ddl, **p = {t_etoiles.p_valeur:.3f}**.")
    a(f"\nPlage attendue sous équité : min ≈ {sim_e[1]:.0f}, max ≈ {sim_e[2]:.0f} "
      f"— observé : {tope[-1][1]} et {tope[0][1]}.\n")

    a("## 4. Forme des grilles tirées\n")
    a(f"- Somme des 5 boules : min {profil['somme_min']}, max {profil['somme_max']}, "
      f"moyenne {profil['somme_moyenne']:.1f}, médiane {profil['somme_mediane']} "
      f"— {profil['part_somme_centrale'] * 100:.0f} % des tirages entre 100 et 175.")
    a("- Nombre de boules paires par tirage : "
      + ", ".join(f"{k} → {v} tirages ({v / n * 100:.0f} %)"
                  for k, v in sorted(profil["pairs"].items())))
    a("- Nombre de boules ≤ 25 par tirage : "
      + ", ".join(f"{k} → {v} tirages ({v / n * 100:.0f} %)"
                  for k, v in sorted(profil["bas"].items())))
    a(f"- Au moins deux boules consécutives : {profil['part_consecutifs'] * 100:.0f} % des tirages.")
    a(f"- Boules reprises d'un tirage au suivant : {profil['repetition_moyenne']:.2f} en moyenne.")
    a(f"- Grilles de 5 boules déjà sorties deux fois dans la fenêtre : "
      f"{profil['grilles_deja_sorties']}.\n")

    a("## 5. Lecture\n")
    seuil = 0.05
    verdict_b = ("compatible avec un tirage équitable" if t_boules.p_valeur > seuil
                 else "s'écarte significativement de l'uniforme")
    verdict_e = ("compatible avec un tirage équitable" if t_etoiles.p_valeur > seuil
                 else "s'écarte significativement de l'uniforme")
    a(f"- Boules : distribution **{verdict_b}** (p = {t_boules.p_valeur:.3f}).")
    a(f"- Étoiles : distribution **{verdict_e}** (p = {t_etoiles.p_valeur:.3f}).")
    a("- Les écarts de fréquence visibles au tableau sont l'amplitude normale du hasard "
      "sur un échantillon de cette taille : ils ne se prolongent pas au tirage suivant.")
    a("- La seule quantité qu'un joueur contrôle est le **partage du gain** : jouer une "
      "grille de forme rare (somme extrême, numéros > 31, pas de suite arithmétique) "
      "ne change pas la probabilité de gagner, mais réduit le nombre de gagnants "
      "avec qui partager.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", default="data/euromillions_4ans.csv",
                    help="historique des tirages (defaut : data/euromillions_4ans.csv)")
    ap.add_argument("--annees", type=float, default=None,
                    help="ne garder que les N dernieres annees du fichier")
    ap.add_argument("--md", metavar="FICHIER", help="ecrire le rapport Markdown ici")
    args = ap.parse_args()

    tirages = charger(args.csv, args.annees)
    if not tirages:
        print("Aucun tirage charge.", file=sys.stderr)
        return 1
    texte = rapport(tirages)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(texte + "\n")
        print(f"Rapport ecrit dans {args.md} ({len(tirages)} tirages).")
    else:
        print(texte)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
