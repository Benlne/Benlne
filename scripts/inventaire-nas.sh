#!/usr/bin/env bash
# Inventaire complet du NAS en une commande, a lancer dans le Terminal de l'iMac.
#
#   bash scripts/inventaire-nas.sh                   # partages homes, photo, video
#   bash scripts/inventaire-nas.sh homes photo music # ou la liste qu'on veut
#
# Indexe chaque partage monte sous /Volumes, puis ecrit un resume court dans
# ~/Inventaire/carte-nas.txt : c'est ce fichier, et lui seul, qu'on colle a
# Claude pour l'analyse. Lecture seule : rien n'est ecrit sur le NAS.
set -u

NAS="NasDom._smb._tcp.local"
ICI="$(cd "$(dirname "$0")" && pwd)"
INVENTAIRE="${ICI}/inventaire.py"
RESUME="${HOME}/Inventaire/carte-nas.txt"

[ -f "${INVENTAIRE}" ] || { echo "inventaire.py introuvable à côté de ce script : ${INVENTAIRE}" >&2; exit 1; }
[ $# -gt 0 ] && PARTAGES=("$@") || PARTAGES=(homes photo video)

faits=()
for p in "${PARTAGES[@]}"; do
    # Un dossier /Volumes/x peut exister sans que le partage soit monte : seul
    # `mount` fait foi.
    if ! mount | grep -q " on /Volumes/${p} "; then
        echo "✗ ${p} non monté — le monter avec : open smb://${NAS}/${p}  (puis relancer)" >&2
        continue
    fi
    echo "→ indexation de ${p}…"
    python3 "${INVENTAIRE}" scan "/Volumes/${p}" --nom "nas-${p}" && faits+=("${p}")
done

[ ${#faits[@]} -gt 0 ] || { echo "Aucun partage indexé." >&2; exit 1; }

{
    echo "# Carte du NAS — $(date '+%d/%m/%Y %H:%M')"
    echo "# Partages demandés : ${PARTAGES[*]} — indexés : ${faits[*]}"
    echo
    python3 "${INVENTAIRE}" liste
    for p in "${faits[@]}"; do
        echo; echo "=================== nas-${p}"
        python3 "${INVENTAIRE}" carte "nas-${p}" --profondeur 2 --limite 40
        echo; echo "--- documents seulement"
        python3 "${INVENTAIRE}" carte "nas-${p}" --categorie documents --profondeur 3 --limite 30
    done
} > "${RESUME}" 2>&1

echo
echo "Résumé écrit : ${RESUME} ($(wc -l < "${RESUME}" | tr -d ' ') lignes)"
echo "À coller à Claude : pbcopy < \"${RESUME}\""
[ ${#faits[@]} -eq ${#PARTAGES[@]} ] || exit 2
