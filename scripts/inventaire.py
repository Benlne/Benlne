#!/usr/bin/env python3
"""Inventaire des fichiers : savoir ce qui existe, ou, et en combien d'exemplaires.

L'iMac tient l'index de tout ce qui traine sur les machines et sur le NAS. Ce
script produit cet index, puis repond aux deux seules questions qui comptent
vraiment : "ou est ce fichier ?" et "qu'est-ce que j'ai en double ?".

    # 1. Indexer une source (rapide : ne lit pas le contenu des fichiers)
    python3 inventaire.py scan "/Volumes/Macintosh HD/Users" --nom imac-2013

    # 2. Chercher
    python3 inventaire.py chercher "facture" 

    # 3. Ce qui n'existe QUE sur le vieux disque : la liste a copier
    python3 inventaire.py manquants imac-2013 --reference nas imac-actuel \\
        --racine "/Volumes/Macintosh HD/Users" --liste-rsync ~/a-copier.txt

    # 4. Doublons. --rapide compare taille et nom sans lire le contenu ;
    #    sans lui, le contenu est verifie, ce qui est sur mais lent en reseau.
    python3 inventaire.py doublons --rapide

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


def dossiers(source: str, sous: str | None, limite: int) -> int:
    """Poids des sous-dossiers, lu dans l'index — sans retoucher au disque.

    Repond a la meme question que `du -sh dossier/*`, mais instantanement et
    autant de fois qu'on veut : l'index porte deja la taille de chaque fichier.
    """
    lignes = [l for l in charger() if l[3] == source]
    if not lignes:
        print(f"Aucun index nommé « {source} ». Voir : inventaire.py liste", file=sys.stderr)
        return 1

    if sous:
        prefixe = sous.rstrip("/") + "/"
        lignes = [l for l in lignes if l[2].startswith(prefixe)]
        if not lignes:
            print(f"Rien sous {sous} dans l'index « {source} ».", file=sys.stderr)
            return 1
    else:
        prefixe = os.path.commonpath([l[2] for l in lignes]).rstrip("/") + "/"

    enfants: dict[str, list[int]] = defaultdict(list)
    for taille, _, chemin, _ in lignes:
        reste = chemin[len(prefixe):]
        enfants[reste.split("/")[0] if "/" in reste else reste].append(taille)

    total = sum(sum(v) for v in enfants.values())
    print(f"{prefixe.rstrip('/')} — {humain(total)}, {sum(len(v) for v in enfants.values())} fichiers\n")
    print(f"{'volume':>12} {'fichiers':>10}  nom")
    for nom, tailles in sorted(enfants.items(), key=lambda kv: -sum(kv[1]))[:limite]:
        print(f"{humain(sum(tailles)):>12} {len(tailles):>10}  {nom}")
    if len(enfants) > limite:
        print(f"… et {len(enfants) - limite} autres entrées.")
    return 0


def cle(taille: int, chemin: str) -> tuple[int, str]:
    """Identite approchee d'un fichier : sa taille et son nom.

    Deux fichiers de meme taille et de meme nom sont le meme fichier dans
    l'immense majorite des cas, et cette comparaison ne lit aucun contenu — ce
    qui compte quand la reference est un NAS au bout du Wi-Fi.
    """
    return (taille, os.path.basename(chemin).lower())


def manquants(source: str, references: list[str], racine: str | None,
              liste_rsync: str | None, taille_mini: int,
              exclure: list[str] | None = None) -> int:
    lignes = charger()
    sources = [l for l in lignes if l[3] == source]
    if not sources:
        print(f"Aucun index nommé « {source} ». Voir : inventaire.py liste", file=sys.stderr)
        return 1

    connues = {cle(l[0], l[2]) for l in lignes if l[3] in references}
    if not connues:
        print(f"Aucun index parmi {references}. Voir : inventaire.py liste", file=sys.stderr)
        return 1

    absents = [l for l in sources if l[0] >= taille_mini and cle(l[0], l[2]) not in connues]
    volume_total = sum(l[0] for l in sources if l[0] >= taille_mini)
    volume_absent = sum(l[0] for l in absents)

    # Les dossiers ecartes ne sont retires qu'ici, pas du calcul precedent : on
    # veut voir separement ce qui manque ailleurs et ce qu'on renonce a copier.
    volume_ecarte = 0
    if exclure:
        gardes = []
        for l in absents:
            if any(motif in l[2] for motif in exclure):
                volume_ecarte += l[0]
            else:
                gardes.append(l)
        absents = gardes

    print(f"Source     : {source} — {len(sources)} fichiers, {humain(volume_total)} au-dessus du seuil")
    print(f"Références : {', '.join(references)}")
    print(f"\nAbsents des références : {humain(volume_absent)}")
    print(f"Déjà ailleurs          : {humain(volume_total - volume_absent)} — inutile de les copier")
    if exclure:
        print(f"Écartés volontairement : {humain(volume_ecarte)} — {', '.join(exclure)}")
    print(f"\nÀ COPIER               : {len(absents)} fichiers, {humain(sum(l[0] for l in absents))}\n")

    absents.sort(key=lambda l: -l[0])
    for taille, mtime, chemin, _ in absents[:40]:
        date = time.strftime("%Y-%m-%d", time.localtime(mtime))
        print(f"  {humain(taille):>10}  {date}  {chemin}")
    if len(absents) > 40:
        print(f"  … et {len(absents) - 40} autres.")

    if liste_rsync:
        if not racine:
            print("\n--liste-rsync exige --racine (le dossier source du futur rsync).",
                  file=sys.stderr)
            return 1
        prefixe = racine.rstrip("/") + "/"
        hors = 0
        with open(os.path.expanduser(liste_rsync), "w", encoding="utf-8") as f:
            for _, _, chemin, _ in absents:
                if chemin.startswith(prefixe):
                    f.write(chemin[len(prefixe):] + "\n")
                else:
                    hors += 1
        print(f"\nListe écrite : {liste_rsync}")
        if hors:
            print(f"  ({hors} fichiers hors de {racine}, non listés)")
        print("À copier avec :")
        print(f'  bash copie-vers-nas.sh --liste "{liste_rsync}" \\')
        print(f'      "{racine}" "/Volumes/homes/benjamin/Save disque imac"')

    print("\nComparaison par taille et par nom, sans lecture du contenu. Pour lever un")
    print("doute sur un fichier précis, « doublons » vérifie le contenu.")
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


def doublons(taille_mini: int, rapide: bool) -> int:
    lignes = [l for l in charger() if l[0] >= taille_mini]
    if not lignes:
        print("Aucun fichier au-dessus du seuil dans les index.")
        return 1

    if rapide:
        # Sans lecture du contenu : taille et nom suffisent a reperer ce qui a
        # deja ete sauvegarde ailleurs, et evitent de relire des centaines de
        # gigaoctets a travers le reseau.
        par_cle: dict[tuple[int, str], list[tuple[int, int, str, str]]] = defaultdict(list)
        for l in lignes:
            par_cle[cle(l[0], l[2])].append(l)
        groupes = [g for g in par_cle.values() if len(g) > 1]
        if not groupes:
            print("Aucun doublon apparent.")
            return 0
        groupes.sort(key=lambda g: -g[0][0] * (len(g) - 1))
        gaspille = sum(g[0][0] * (len(g) - 1) for g in groupes)
        print(f"{len(groupes)} groupes de doublons apparents — {humain(gaspille)} récupérables")
        print("(comparaison par taille et nom, sans lecture du contenu)\n")
        for g in groupes[:40]:
            print(f"{humain(g[0][0])} × {len(g)} exemplaires :")
            for _, _, chemin, source in g:
                print(f"    [{source}] {chemin}")
            print()
        if len(groupes) > 40:
            print(f"… et {len(groupes) - 40} autres groupes.")
        return 0

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

    p = sous.add_parser("dossiers", help="poids des sous-dossiers, lu dans l'index")
    p.add_argument("source", help="index à explorer, ex. imac-2013")
    p.add_argument("--sous", help="chemin dont on veut les enfants directs")
    p.add_argument("--limite", type=int, default=30, help="entrées affichées")

    p = sous.add_parser("chercher", help="retrouver un fichier par son nom")
    p.add_argument("motif")

    p = sous.add_parser("manquants", help="ce qui n'existe que dans une source")
    p.add_argument("source", help="index à trier, ex. imac-2013")
    p.add_argument("--reference", nargs="+", required=True,
                   help="index où le fichier est déjà en sécurité, ex. nas")
    p.add_argument("--racine", help="dossier source du futur rsync, pour --liste-rsync")
    p.add_argument("--liste-rsync", help="écrire la liste des fichiers à copier ici")
    p.add_argument("--exclure", nargs="+", default=None,
                   help="ne pas copier les chemins contenant ces fragments, ex. /Music/ /Library/")
    p.add_argument("--taille-mini", type=int, default=TAILLE_MINI_DOUBLON,
                   help="ignorer les fichiers plus petits (octets)")

    p = sous.add_parser("doublons", help="fichiers présents en plusieurs exemplaires")
    p.add_argument("--rapide", action="store_true",
                   help="comparer taille et nom sans lire le contenu")
    p.add_argument("--taille-mini", type=int, default=TAILLE_MINI_DOUBLON,
                   help="ignorer les fichiers plus petits (octets)")

    args = ap.parse_args()
    if args.commande == "scan":
        return scan(args.racine, args.nom)
    if args.commande == "liste":
        return liste()
    if args.commande == "dossiers":
        return dossiers(args.source, args.sous, args.limite)
    if args.commande == "chercher":
        return chercher(args.motif)
    if args.commande == "manquants":
        return manquants(args.source, args.reference, args.racine,
                         args.liste_rsync, args.taille_mini, args.exclure)
    return doublons(args.taille_mini, args.rapide)


if __name__ == "__main__":
    raise SystemExit(main())
