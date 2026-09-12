#!/usr/bin/env python3
"""Inventaire des fichiers : savoir ce qui existe, ou, et en combien d'exemplaires.

L'iMac tient l'index de tout ce qui traine sur les machines et sur le NAS. Ce
script produit cet index, puis repond aux deux seules questions qui comptent
vraiment : "ou est ce fichier ?" et "qu'est-ce que j'ai en double ?".

    # 1. Indexer une source (rapide : ne lit pas le contenu des fichiers)
    python3 inventaire.py scan "/Volumes/Macintosh HD/Users" --nom imac-2013

    # 2. Chercher
    python3 inventaire.py chercher "facture" 

    # 3. Trouver les doublons (lit le contenu, donc plus lent)
    python3 inventaire.py doublons

Les index sont des fichiers TSV dans ~/Inventaire, lisibles avec n'importe quel
tableur. Rien n'est jamais supprime par ce script.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from collections import defaultdict

DOSSIER = os.path.expanduser("~/Inventaire")

# Dossiers sans interet pour un inventaire : ils gonflent l'index et ne
# contiennent rien qu'on cherchera un jour.
IGNORES = {
    ".Spotlight-V100", ".fseventsd", ".Trashes", ".DocumentRevisions-V100",
    ".TemporaryItems", "Caches", "node_modules", ".git", ".Trash",
}

TAILLE_MINI_DOUBLON = 1_000_000  # 1 Mo : en dessous, un doublon ne coute rien


def index(nom: str) -> str:
    return os.path.join(DOSSIER, f"{nom}.tsv")


def humain(octets: float) -> str:
    for unite in ("o", "Ko", "Mo", "Go", "To"):
        if octets < 1024 or unite == "To":
            return f"{octets:.1f} {unite}"
        octets /= 1024
    return ""


def scan(racine: str, nom: str) -> int:
    if not os.path.isdir(racine):
        print(f"Racine introuvable : {racine}", file=sys.stderr)
        return 1
    os.makedirs(DOSSIER, exist_ok=True)
    chemin_index = index(nom)

    fichiers = octets = ignores = 0
    debut = time.time()
    with open(chemin_index, "w", encoding="utf-8") as f:
        f.write("taille\tmodifie\tchemin\n")
        for dossier, sous_dossiers, noms in os.walk(racine, onerror=lambda e: None):
            sous_dossiers[:] = [d for d in sous_dossiers if d not in IGNORES]
            for n in noms:
                if n == ".DS_Store":
                    continue
                chemin = os.path.join(dossier, n)
                try:
                    st = os.lstat(chemin)
                except OSError:
                    ignores += 1
                    continue
                if not os.path.isfile(chemin) or os.path.islink(chemin):
                    continue
                f.write(f"{st.st_size}\t{int(st.st_mtime)}\t{chemin}\n")
                fichiers += 1
                octets += st.st_size
                if fichiers % 20000 == 0:
                    print(f"  {fichiers} fichiers, {humain(octets)}…", flush=True)

    print(f"\nIndex écrit : {chemin_index}")
    print(f"  {fichiers} fichiers, {humain(octets)}, en {time.time() - debut:.0f} s")
    if ignores:
        print(f"  {ignores} entrées illisibles ignorées")
    return 0


def charger() -> list[tuple[int, int, str, str]]:
    """Toutes les lignes de tous les index : (taille, mtime, chemin, source)."""
    if not os.path.isdir(DOSSIER):
        return []
    lignes = []
    for fichier in sorted(os.listdir(DOSSIER)):
        if not fichier.endswith(".tsv"):
            continue
        source = fichier[:-4]
        with open(os.path.join(DOSSIER, fichier), encoding="utf-8") as f:
            next(f, None)
            for ligne in f:
                parts = ligne.rstrip("\n").split("\t", 2)
                if len(parts) == 3:
                    lignes.append((int(parts[0]), int(parts[1]), parts[2], source))
    return lignes


def liste() -> int:
    lignes = charger()
    if not lignes:
        print("Aucun index. Commencer par : inventaire.py scan <racine> --nom <étiquette>")
        return 1
    par_source: dict[str, list[int]] = defaultdict(list)
    for taille, _, _, source in lignes:
        par_source[source].append(taille)
    print(f"{'source':<24} {'fichiers':>10} {'volume':>12}")
    for source, tailles in sorted(par_source.items()):
        print(f"{source:<24} {len(tailles):>10} {humain(sum(tailles)):>12}")
    return 0


def chercher(motif: str) -> int:
    motif_bas = motif.lower()
    trouves = [l for l in charger() if motif_bas in os.path.basename(l[2]).lower()]
    if not trouves:
        print(f"Rien qui contienne « {motif} ».")
        return 1
    trouves.sort(key=lambda l: -l[0])
    for taille, mtime, chemin, source in trouves[:200]:
        date = time.strftime("%Y-%m-%d", time.localtime(mtime))
        print(f"[{source}] {humain(taille):>10}  {date}  {chemin}")
    if len(trouves) > 200:
        print(f"… et {len(trouves) - 200} autres.")
    return 0


def empreinte(chemin: str) -> str | None:
    h = hashlib.blake2b(digest_size=16)
    try:
        with open(chemin, "rb") as f:
            for bloc in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloc)
    except OSError:
        return None
    return h.hexdigest()


def doublons(taille_mini: int) -> int:
    lignes = [l for l in charger() if l[0] >= taille_mini]
    if not lignes:
        print("Aucun fichier au-dessus du seuil dans les index.")
        return 1

    # Deux fichiers de tailles differentes ne sont jamais identiques : on ne lit
    # le contenu que des candidats, ce qui evite de hacher tout l'inventaire.
    par_taille: dict[int, list[tuple[int, int, str, str]]] = defaultdict(list)
    for l in lignes:
        par_taille[l[0]].append(l)
    candidats = [l for groupe in par_taille.values() if len(groupe) > 1 for l in groupe]
    print(f"{len(candidats)} fichiers à vérifier (même taille qu'un autre)…")

    par_empreinte: dict[str, list[tuple[int, int, str, str]]] = defaultdict(list)
    illisibles = 0
    for i, l in enumerate(candidats, 1):
        e = empreinte(l[2])
        if e is None:
            illisibles += 1
            continue
        par_empreinte[e].append(l)
        if i % 200 == 0:
            print(f"  {i}/{len(candidats)}…", flush=True)

    groupes = [g for g in par_empreinte.values() if len(g) > 1]
    if not groupes:
        print("\nAucun doublon.")
        return 0

    groupes.sort(key=lambda g: -g[0][0] * (len(g) - 1))
    gaspille = sum(g[0][0] * (len(g) - 1) for g in groupes)
    print(f"\n{len(groupes)} groupes de doublons — {humain(gaspille)} récupérables\n")
    for g in groupes[:40]:
        print(f"{humain(g[0][0])} × {len(g)} exemplaires :")
        for _, _, chemin, source in g:
            print(f"    [{source}] {chemin}")
        print()
    if len(groupes) > 40:
        print(f"… et {len(groupes) - 40} autres groupes.")
    if illisibles:
        print(f"{illisibles} fichiers illisibles (volume démonté ?) ignorés.")
    print("Ce script ne supprime rien : à toi de choisir quel exemplaire garder.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = ap.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("scan", help="indexer une racine")
    p.add_argument("racine")
    p.add_argument("--nom", required=True, help="étiquette de la source, ex. imac-2013")

    sous.add_parser("liste", help="ce qui est indexé")

    p = sous.add_parser("chercher", help="retrouver un fichier par son nom")
    p.add_argument("motif")

    p = sous.add_parser("doublons", help="fichiers présents en plusieurs exemplaires")
    p.add_argument("--taille-mini", type=int, default=TAILLE_MINI_DOUBLON,
                   help="ignorer les fichiers plus petits (octets)")

    args = ap.parse_args()
    if args.commande == "scan":
        return scan(args.racine, args.nom)
    if args.commande == "liste":
        return liste()
    if args.commande == "chercher":
        return chercher(args.motif)
    return doublons(args.taille_mini)


if __name__ == "__main__":
    raise SystemExit(main())
