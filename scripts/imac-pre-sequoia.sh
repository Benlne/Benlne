#!/bin/bash
# Vérifications avant d'installer macOS Sequoia avec OpenCore Legacy Patcher.
#
# Lecture seule : ne modifie rien, n'installe rien, ne demande pas sudo.
# Répond à une seule question : peut-on lancer la procédure maintenant ?
#
# Usage :  bash scripts/imac-pre-sequoia.sh

set -u

OK=0
ALERTES=0
BLOQUANTS=0

titre() { printf '\n==== %s ====\n' "$1"; }
vert()  { printf '  [ok]     %s\n' "$1"; OK=$((OK + 1)); }
orange(){ printf '  [voir]   %s\n' "$1"; ALERTES=$((ALERTES + 1)); }
rouge() { printf '  [BLOQUE] %s\n' "$1"; BLOQUANTS=$((BLOQUANTS + 1)); }

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Ce script est prévu pour macOS (uname = $(uname -s))." >&2
  exit 1
fi

titre "Machine"
modele=$(sysctl -n hw.model 2>/dev/null)
printf '  %s — macOS %s\n' "$modele" "$(sw_vers -productVersion)"
case "$modele" in
  iMac14,1|iMac14,2|iMac14,3|iMac14,4)
    vert "Modèle pris en charge par OpenCore Legacy Patcher" ;;
  *)
    orange "Modèle $modele : vérifier la liste des modèles supportés par OCLP" ;;
esac

titre "Droits d'administration"
if dseditgroup -o checkmember -m "$USER" admin >/dev/null 2>&1; then
  vert "$USER est administrateur"
else
  rouge "$USER n'est pas administrateur — OCLP ne pourra pas écrire la partition EFI"
fi

titre "Espace disque"
libre_go=$(df -g / 2>/dev/null | awk 'NR==2 {print $4}')
printf '  %s Go libres sur le volume système\n' "${libre_go:-?}"
if [ "${libre_go:-0}" -ge 60 ] 2>/dev/null; then
  vert "Assez de place pour un second système (60 Go recommandés)"
elif [ "${libre_go:-0}" -ge 40 ] 2>/dev/null; then
  orange "Juste : Sequoia tiendra, mais il restera peu de marge. Faire du ménage d'abord"
else
  rouge "Moins de 40 Go libres : libérer de la place avant de commencer"
fi

titre "Volume Sequoia"
if diskutil list 2>/dev/null | grep -q "APFS Volume Sequoia"; then
  vert "Le volume APFS 'Sequoia' existe déjà"
else
  orange "Volume 'Sequoia' pas encore créé — étape 2 du runbook (Utilitaire de disque)"
fi

titre "Disques externes branchés"
# Deux besoins distincts et incompatibles : un support a effacer pour l'installeur
# Sequoia, et un disque a conserver pour la sauvegarde Time Machine. Ce bloc
# decrit ce qui est branche, il ne designe jamais un disque porteur de donnees
# comme effaçable.
#
# On part des volumes MONTES et non de "diskutil list external physical" : un
# disque externe en APFS apparait comme volume d'un conteneur synthetise, que
# cette liste-la ne montre pas. C'est ce qui faisait passer un disque plein pour
# un disque vide.
porteurs_avec_donnees=" "
disque_sauvegarde=0
externes=0

for montage in /Volumes/*; do
  [ -d "$montage" ] || continue
  info=$(diskutil info "$montage" 2>/dev/null) || continue
  printf '%s' "$info" | grep -q "Device Location: *External" || continue
  externes=$((externes + 1))

  noeud=$(printf '%s' "$info" | awk -F': *' '/Device Node/ {print $2; exit}')
  ssd=$(printf '%s' "$info" | awk -F': *' '/Solid State/ {print $2; exit}')
  # Disque physique porteur : le magasin APFS s'il existe, sinon le disque entier.
  physique=$(printf '%s' "$info" | awk -F': *' '/APFS Physical Store/ {print $2; exit}' | sed 's/s[0-9]*$//')
  [ -z "$physique" ] && physique=$(printf '%s' "$info" | awk -F': *' '/Part of Whole/ {print $2; exit}')
  case "$ssd" in
    Yes) type="SSD ou clé" ;;
    No)  type="disque mécanique" ;;
    *)   type="type inconnu" ;;
  esac

  occupation=$(df -h "$montage" 2>/dev/null | awk 'NR==2 {print $3" utilisés sur "$2}')
  printf '  %-28s %s — %s — %s\n' "$(basename "$montage")" "${noeud:-?}" "$type" "${occupation:-?}"
  printf '      disque physique porteur : %s\n' "${physique:-?}"

  utilise_ko=$(df -k "$montage" 2>/dev/null | awk 'NR==2 {print $3}')
  if [ -d "$montage/Backups.backupdb" ]; then
    printf '      %s\n' "sauvegarde Time Machine existante"
    disque_sauvegarde=1
    porteurs_avec_donnees="$porteurs_avec_donnees$physique "
  elif [ "${utilise_ko:-0}" -gt 1048576 ] 2>/dev/null; then
    printf '      %s\n' "contient des données — à conserver, ne jamais le désigner à OCLP"
    disque_sauvegarde=1
    porteurs_avec_donnees="$porteurs_avec_donnees$physique "
  fi
done

# Un support vraiment vierge (clé neuve, disque efface) n'a aucun volume monte :
# on le retrouve par la liste des disques physiques externes.
candidat_installeur=0
while IFS= read -r disque; do
  [ -z "$disque" ] && continue
  identifiant=$(basename "$disque")
  info=$(diskutil info "$disque" 2>/dev/null)
  octets=$(printf '%s' "$info" | awk '/Disk Size/ {print $5; exit}' | tr -d '(')
  taille=$(printf '%s' "$info" | awk '/Disk Size/ {print $3, $4; exit}')
  nom=$(printf '%s' "$info" | awk -F': *' '/Device \/ Media Name/ {print $2; exit}')
  [ "${octets:-0}" -ge 15000000000 ] 2>/dev/null || continue
  case "$porteurs_avec_donnees" in
    *" $identifiant "*)
      printf '  %s (%s, %s) : porte des données, écarté comme installeur\n' "$identifiant" "${nom:-?}" "${taille:-?}" ;;
    *)
      printf '  %s (%s, %s) : aucun volume de données monté — candidat installeur\n' "$identifiant" "${nom:-?}" "${taille:-?}"
      candidat_installeur=1 ;;
  esac
done <<EOF
$(diskutil list external physical 2>/dev/null | awk '/^\/dev\/disk/ {print $1}')
EOF

if [ "$externes" -eq 0 ] && [ "$candidat_installeur" -eq 0 ]; then
  orange "Aucun disque externe branché — il en faut deux rôles : un support de 16 Go à effacer pour l'installeur, et de préférence un disque pour Time Machine"
else
  if [ "$candidat_installeur" -eq 1 ]; then
    vert "Un support d'au moins 16 Go sans données peut servir d'installeur"
  else
    orange "Aucun support vide de 16 Go : brancher une clé dédiée, et ne PAS effacer un disque qui contient des données"
  fi
  if [ "$disque_sauvegarde" -eq 1 ]; then
    vert "Un disque externe porteur de données est branché : candidat pour Time Machine"
  else
    orange "Pas de disque identifié pour Time Machine — la sauvegarde reste le meilleur filet avant de toucher au système"
  fi
fi

titre "Outils"
if xcode-select -p >/dev/null 2>&1; then
  vert "Command Line Tools installés ($(xcode-select -p))"
else
  orange "Command Line Tools absents — pas bloquant pour OCLP, utile ensuite"
fi

titre "Chiffrement"
if fdesetup status 2>/dev/null | grep -qi "off"; then
  vert "FileVault désactivé — c'est ce qu'il faut pour OCLP"
else
  orange "FileVault actif : le désactiver avant de commencer"
fi

titre "Réseau"
if curl -s -m 10 -o /dev/null -w '' https://github.com 2>/dev/null; then
  vert "Accès Internet fonctionnel (15 Go à télécharger, prévoir le temps)"
else
  rouge "Pas d'accès Internet : le téléchargement de Sequoia est impossible"
fi
if ifconfig en0 2>/dev/null | grep -q "status: active"; then
  vert "Ethernet connecté"
else
  orange "Wi-Fi seulement : le téléchargement sera plus long, et la liaison moins sûre"
fi

titre "À mettre à l'abri avant de commencer"
echo "  Pas de sauvegarde Time Machine : copier ce qui est irremplaçable sur un"
echo "  disque externe ou dans un cloud. Poids des dossiers personnels :"
for dossier in Documents Bureau Desktop Images Pictures Films Movies Musique Music Téléchargements Downloads; do
  chemin="$HOME/$dossier"
  [ -d "$chemin" ] || continue
  taille=$(du -sh "$chemin" 2>/dev/null | cut -f1)
  [ -n "$taille" ] && printf '    %-16s %s\n' "$dossier" "$taille"
done

titre "Verdict"
printf '  %d points vérifiés, %d à regarder, %d bloquants\n' "$OK" "$ALERTES" "$BLOQUANTS"
if [ "$BLOQUANTS" -gt 0 ]; then
  echo "  NE PAS COMMENCER tant que les points [BLOQUE] ne sont pas réglés."
elif [ "$ALERTES" -gt 0 ]; then
  echo "  Praticable : régler les points [voir] au fur et à mesure du runbook."
else
  echo "  Tout est en place — docs/sequoia-oclp.md, étape 2."
fi
