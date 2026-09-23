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

    # 4. Ce que contient chaque dossier : types de contenu et annees
    python3 inventaire.py carte nas-homes --profondeur 2
    python3 inventaire.py carte nas-homes --categorie documents

    # 5. Doublons. --rapide compare taille et nom sans lire le contenu ;
    #    sans lui, le contenu est verifie, ce qui est sur mais lent en reseau.
    python3 inventaire.py doublons --rapide

Les index sont des fichiers TSV dans ~/Inventaire, lisibles avec n'importe quel
tableur. Rien n'est jamais supprime par ce script.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import signal
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

    # Un partage SMB non monte laisse souvent un dossier vide a sa place : un
    # index vide passerait ensuite pour une reference valide dans `manquants`.
    if fichiers == 0:
        os.remove(chemin_index)
        print(f"Aucun fichier sous {racine} : partage non monté ? Index non écrit.",
              file=sys.stderr)
        return 1

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


CATEGORIES = {
    "documents": {"pdf", "doc", "docx", "odt", "rtf", "txt", "md", "pages", "xls", "xlsx",
                  "ods", "csv", "numbers", "ppt", "pptx", "odp", "key", "epub", "tex"},
    "photos": {"jpg", "jpeg", "png", "heic", "heif", "gif", "tif", "tiff", "bmp", "webp",
               "raw", "dng", "cr2", "cr3", "nef", "arw", "orf", "rw2", "psd"},
    "videos": {"mp4", "mov", "m4v", "avi", "mkv", "mts", "m2ts", "3gp", "wmv", "mpg",
               "mpeg", "vob"},
    "musique": {"mp3", "flac", "m4a", "aac", "wav", "aif", "aiff", "ogg", "wma", "alac"},
    "archives": {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "dmg", "iso", "img"},
}
COLONNES = [*CATEGORIES, "autre"]


def categorie(chemin: str) -> str:
    ext = os.path.splitext(chemin)[1][1:].lower()
    for nom, extensions in CATEGORIES.items():
        if ext in extensions:
            return nom
    return "autre"


def carte(source: str, sous: str | None, profondeur: int, filtre: str | None,
          limite: int) -> int:
    """Ce que contient chaque dossier : volume par type de contenu et années couvertes.

    `dossiers` dit combien pese un dossier ; `carte` dit ce qu'il y a dedans, ce
    qui suffit a reperer ou vivent les documents, les photos, les archives.
    """
    lignes = [l for l in charger() if l[3] == source]
    if not lignes:
        print(f"Aucun index nommé « {source} ». Voir : inventaire.py liste", file=sys.stderr)
        return 1
    if sous:
        prefixe = sous.rstrip("/") + "/"
        lignes = [l for l in lignes if l[2].startswith(prefixe)]
    else:
        prefixe = os.path.commonpath([l[2] for l in lignes]).rstrip("/") + "/"
    if filtre:
        lignes = [l for l in lignes if categorie(l[2]) == filtre]
    if not lignes:
        print(f"Rien à cartographier dans « {source} » avec ces critères.", file=sys.stderr)
        return 1

    groupes: dict[str, dict] = {}
    for taille, mtime, chemin, _ in lignes:
        parties = chemin[len(prefixe):].split("/")
        # Un fichier pose plus haut que la profondeur demandee reste a son niveau.
        nom = "/".join(parties[:min(profondeur, len(parties) - 1)]) or "(fichiers à la racine)"
        g = groupes.setdefault(nom, {"total": 0, "fichiers": 0, "annees": [9999, 0],
                                     **{c: 0 for c in COLONNES}})
        g["total"] += taille
        g["fichiers"] += 1
        g[categorie(chemin)] += taille
        annee = time.localtime(mtime).tm_year
        g["annees"] = [min(g["annees"][0], annee), max(g["annees"][1], annee)]

    total = sum(g["total"] for g in groupes.values())
    titre = prefixe.rstrip("/") + (f" — {filtre} seulement" if filtre else "")
    print(f"{titre} — {humain(total)}, {len(lignes)} fichiers\n")
    print(f"{'volume':>10} {'fichiers':>8} " + " ".join(f"{c:>10}" for c in COLONNES)
          + f" {'années':>11}  dossier")
    for nom, g in sorted(groupes.items(), key=lambda kv: -kv[1]["total"])[:limite]:
        volumes = " ".join(f"{humain(g[c]) if g[c] else '·':>10}" for c in COLONNES)
        a, b = g["annees"]
        annees = str(a) if a == b else f"{a}-{b}"
        print(f"{humain(g['total']):>10} {g['fichiers']:>8} {volumes} {annees:>11}  {nom}")
    if len(groupes) > limite:
        print(f"… et {len(groupes) - limite} autres dossiers.")
    print("\nAnnées : date de dernière modification, pas de création — une copie la conserve,")
    print("une réécriture non. Type déduit de l'extension.")
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

    # Une reference nommee mais inexistante doit ARRETER le programme. Sinon elle
    # est silencieusement traitee comme vide, la comparaison est amputee, et un
    # fichier passe pour absent — ou pire, on croit avoir compare a une sauvegarde
    # qui n'a jamais ete indexee avant d'effacer un disque.
    disponibles = {l[3] for l in lignes}
    introuvables = [r for r in references if r not in disponibles]
    if introuvables:
        print(f"Références inexistantes : {', '.join(introuvables)}", file=sys.stderr)
        print(f"Index disponibles : {', '.join(sorted(disponibles))}", file=sys.stderr)
        print("Comparer à une référence vide donnerait un résultat faux. Arrêt.",
              file=sys.stderr)
        return 1

    connues = {cle(l[0], l[2]) for l in lignes if l[3] in references}

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


def recouvrements(profondeur: int, filtre: str | None, taille_mini: int, limite: int,
                  sources: list[str] | None = None) -> int:
    """Quels dossiers contiennent les memes fichiers, et pour quel volume.

    C'est la vue qui sert au menage : elle ne dit pas « ce fichier existe deux
    fois » mais « ces deux dossiers se recouvrent de 40 Go », ce qui designe
    directement le dossier a examiner. Comparaison par taille et nom.
    """
    tout = [l for l in charger() if sources is None or l[3] in sources]
    lignes = [l for l in tout if l[0] >= taille_mini
              and (filtre is None or categorie(l[2]) == filtre)]
    if not lignes:
        print("Aucun fichier retenu avec ces critères.", file=sys.stderr)
        return 1

    # La profondeur se compte depuis la racine du partage entier, pas depuis
    # l'ancetre commun des seuls fichiers retenus par le filtre.
    par_source: dict[str, list[str]] = defaultdict(list)
    for l in tout:
        par_source[l[3]].append(os.path.dirname(l[2]))
    racines = {s: os.path.commonpath(d).rstrip("/") + "/" for s, d in par_source.items()}

    def dossier(chemin: str, source: str) -> str:
        parties = chemin[len(racines[source]):].split("/")[:-1][:profondeur]
        return f"[{source}] {racines[source]}{'/'.join(parties)}".rstrip("/")

    par_cle: dict[tuple[int, str], list[tuple[int, int, str, str]]] = defaultdict(list)
    for l in lignes:
        par_cle[cle(l[0], l[2])].append(l)

    paires: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for groupe in par_cle.values():
        if len(groupe) < 2:
            continue
        noms = sorted(dossier(l[2], l[3]) for l in groupe)
        vues = set()
        for i in range(len(noms)):
            for j in range(i + 1, len(noms)):
                if (noms[i], noms[j]) in vues:
                    continue
                vues.add((noms[i], noms[j]))
                p = paires[(noms[i], noms[j])]
                p[0] += groupe[0][0]
                p[1] += 1

    if not paires:
        print("Aucun recouvrement.")
        return 0
    titre = f"{filtre} seulement, " if filtre else ""
    print(f"Recouvrements entre dossiers — {titre}profondeur {profondeur}, "
          f"fichiers ≥ {humain(taille_mini)}\n")
    for (a, b), (volume, n) in sorted(paires.items(), key=lambda kv: -kv[1][0])[:limite]:
        if a == b:
            print(f"{humain(volume):>10} {n:>7} fichiers en double À L'INTÉRIEUR de\n"
                  f"{'':>19}{a}\n")
        else:
            print(f"{humain(volume):>10} {n:>7} fichiers communs à\n{'':>19}{a}\n{'':>19}{b}\n")
    if len(paires) > limite:
        print(f"… et {len(paires) - limite} autres paires.")
    print("Comparaison par taille et nom. Rien n'est supprimé : c'est une carte, pas un tri.")
    return 0


def doublons(taille_mini: int, rapide: bool, filtre: str | None = None) -> int:
    lignes = [l for l in charger() if l[0] >= taille_mini
              and (filtre is None or categorie(l[2]) == filtre)]
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
    # Sans cela, un « | head » ferme le tuyau et Python affiche une trace
    # BrokenPipeError alarmante pour ce qui est le comportement normal d'un
    # filtre Unix.
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass  # SIGPIPE n'existe pas partout (Windows)

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

    p = sous.add_parser("carte", help="type de contenu et années de chaque dossier")
    p.add_argument("source", help="index à cartographier, ex. nas-homes")
    p.add_argument("--sous", help="ne cartographier que ce chemin")
    p.add_argument("--profondeur", type=int, default=1, help="niveaux de dossiers regroupés")
    p.add_argument("--categorie", choices=COLONNES, help="ne garder qu'un type de contenu")
    p.add_argument("--limite", type=int, default=40, help="dossiers affichés")

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
    p.add_argument("--categorie", choices=COLONNES, help="ne garder qu'un type de contenu")
    p.add_argument("--taille-mini", type=int, default=TAILLE_MINI_DOUBLON,
                   help="ignorer les fichiers plus petits (octets)")

    p = sous.add_parser("recouvrements", help="dossiers qui contiennent les mêmes fichiers")
    p.add_argument("--profondeur", type=int, default=3, help="niveaux de dossiers comparés")
    p.add_argument("--categorie", choices=COLONNES, help="ne garder qu'un type de contenu")
    p.add_argument("--taille-mini", type=int, default=100_000,
                   help="ignorer les fichiers plus petits (octets)")
    p.add_argument("--limite", type=int, default=30, help="paires affichées")
    p.add_argument("--sources", nargs="+", help="index à comparer (défaut : tous)")

    args = ap.parse_args()
    if args.commande == "recouvrements":
        return recouvrements(args.profondeur, args.categorie, args.taille_mini, args.limite,
                             args.sources)
    if args.commande == "scan":
        return scan(args.racine, args.nom)
    if args.commande == "liste":
        return liste()
    if args.commande == "dossiers":
        return dossiers(args.source, args.sous, args.limite)
    if args.commande == "carte":
        return carte(args.source, args.sous, args.profondeur, args.categorie, args.limite)
    if args.commande == "chercher":
        return chercher(args.motif)
    if args.commande == "manquants":
        return manquants(args.source, args.reference, args.racine,
                         args.liste_rsync, args.taille_mini, args.exclure)
    return doublons(args.taille_mini, args.rapide, args.categorie)


if __name__ == "__main__":
    raise SystemExit(main())
