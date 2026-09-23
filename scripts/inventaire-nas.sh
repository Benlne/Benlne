#!/usr/bin/env bash
# Inventaire du NAS en une commande, a lancer dans le Terminal d'un Mac qui a
# les partages montes (iMac ou MacBook Air).
#
#   bash scripts/inventaire-nas.sh                    # homes, photo, video, music
#   bash scripts/inventaire-nas.sh photo music        # ou la liste qu'on veut
#   bash scripts/inventaire-nas.sh --analyse          # resume seul, sans rescanner
#
# Indexe chaque partage monte sous /Volumes, puis ecrit un resume court dans
# ~/Inventaire/carte-nas.txt, oriente menage des photos et de la musique :
# c'est ce fichier, et lui seul, qu'on colle a Claude. Lecture seule : rien
# n'est ecrit sur le NAS.
set -u

NAS="NasDom._smb._tcp.local"
ICI="$(cd "$(dirname "$0")" && pwd)"
INVENTAIRE="${ICI}/inventaire.py"
RESUME="${HOME}/Inventaire/carte-nas.txt"

ANALYSE=0
if [ "${1:-}" = "--analyse" ]; then ANALYSE=1; shift; fi

[ -f "${INVENTAIRE}" ] || { echo "inventaire.py introuvable à côté de ce script : ${INVENTAIRE}" >&2; exit 1; }
[ $# -gt 0 ] && PARTAGES=("$@") || PARTAGES=(homes photo video music)

faits=()
for p in "${PARTAGES[@]}"; do
    if [ ${ANALYSE} -eq 1 ]; then
        [ -f "${HOME}/Inventaire/nas-${p}.tsv" ] && faits+=("${p}")
        continue
    fi
    # Un dossier /Volumes/x peut exister sans que le partage soit monte : seul
    # `mount` fait foi.
    if ! mount | grep -q " on /Volumes/${p} "; then
        echo "✗ ${p} non monté (ou inexistant) — le monter avec : open smb://${NAS}/${p}" >&2
        continue
    fi
    echo "→ indexation de ${p}…"
    python3 "${INVENTAIRE}" scan "/Volumes/${p}" --nom "nas-${p}" && faits+=("${p}")
done

[ ${#faits[@]} -gt 0 ] || { echo "Aucun partage indexé." >&2; exit 1; }

echo "→ rédaction du résumé…"
{
    echo "# Carte du NAS — $(date '+%d/%m/%Y %H:%M')"
    echo "# Partages demandés : ${PARTAGES[*]} — indexés : ${faits[*]}"
    echo
    python3 "${INVENTAIRE}" liste
    for p in "${faits[@]}"; do
        echo; echo "=================== nas-${p}"
        python3 "${INVENTAIRE}" carte "nas-${p}" --profondeur 2 --limite 25
        for c in photos musique; do
            echo; echo "--- ${c} seulement"
            python3 "${INVENTAIRE}" carte "nas-${p}" --categorie "${c}" --profondeur 3 --limite 25
        done
    done
    for c in photos musique; do
        echo; echo "=================== recouvrements : ${c}"
        python3 "${INVENTAIRE}" recouvrements --categorie "${c}" --profondeur 4 --limite 25 \
            --sources $(printf "nas-%s " "${faits[@]}")
    done
} > "${RESUME}" 2>&1

echo
echo "Résumé écrit : ${RESUME} ($(wc -l < "${RESUME}" | tr -d ' ') lignes)"
echo "À coller à Claude : pbcopy < \"${RESUME}\""
[ ${#faits[@]} -eq ${#PARTAGES[@]} ] || exit 2
