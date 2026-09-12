#!/bin/bash
# État des lieux de l'iMac avant tout changement.
#
# Lecture seule : ce script ne modifie rien, n'installe rien, ne demande pas sudo.
# Le numéro de série et l'UUID matériel sont retirés de la sortie, qui peut donc
# être collée telle quelle dans une conversation ou un ticket.
#
# Usage :  bash scripts/imac-preflight.sh

set -u

titre() { printf '\n==== %s ====\n' "$1"; }
valeur() { printf '%-28s %s\n' "$1" "$2"; }
existe() { command -v "$1" >/dev/null 2>&1; }

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Ce script est prévu pour macOS (uname = $(uname -s))." >&2
  exit 1
fi

titre "Système"
valeur "macOS" "$(sw_vers -productVersion) (build $(sw_vers -buildVersion))"
valeur "Noyau" "$(uname -r)"
valeur "Architecture" "$(uname -m)"
valeur "Allumé depuis" "$(uptime | sed 's/.*up //; s/,  *[0-9]* user.*//')"

titre "Matériel"
# system_profiler expose le numéro de série et l'UUID : on les coupe.
system_profiler SPHardwareDataType 2>/dev/null \
  | grep -v -i -e "Serial Number" -e "Numéro de série" \
               -e "Hardware UUID" -e "UUID du matériel" \
               -e "Provisioning UDID" \
  | sed '/^ *$/d'

titre "Disques"
diskutil list 2>/dev/null
echo
for volume in / ; do
  echo "--- volume $volume"
  diskutil info "$volume" 2>/dev/null \
    | grep -E "Device Node|Volume Name|File System|Solid State|SMART|Disk Size|Volume Free Space|Read-Only" \
    | sed 's/^ *//'
done
echo
df -h / 2>/dev/null

titre "Type de disque physique"
# La question qui décide de tout : SSD, Fusion Drive ou disque mécanique.
system_profiler SPStorageDataType 2>/dev/null \
  | grep -E "Medium Type|Physical Drive|Media Name|Device Name|Free|Capacity|SMART|Type de support" \
  | sed 's/^ *//'

titre "Mémoire"
valeur "RAM physique" "$(( $(sysctl -n hw.memsize) / 1073741824 )) Go"
if existe vm_stat; then
  vm_stat | head -5
fi
sysctl -n vm.swapusage 2>/dev/null | sed 's/^/swap : /'

titre "Sécurité et chiffrement"
valeur "FileVault" "$(fdesetup status 2>/dev/null | head -1)"
valeur "SIP" "$(csrutil status 2>/dev/null | sed 's/System Integrity Protection status: //')"
if existe spctl; then valeur "Gatekeeper" "$(spctl --status 2>/dev/null)"; fi

titre "Énergie (réglages actuels)"
pmset -g custom 2>/dev/null | sed 's/^ */  /'

titre "Réseau"
for iface in en0 en1; do
  ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
  [ -n "$ip" ] && valeur "$iface" "$ip"
done
system_profiler SPAirPortDataType 2>/dev/null \
  | grep -E "Card Type|Firmware Version|Supported PHY Modes" \
  | sed 's/^ *//' | head -3

titre "Outils de développement déjà présents"
for outil in git python3 node npm brew docker tmux VBoxManage; do
  if existe "$outil"; then
    version=$("$outil" --version 2>/dev/null | head -1)
    valeur "$outil" "${version:-présent}"
  else
    valeur "$outil" "absent"
  fi
done
if existe xcode-select; then
  valeur "Command Line Tools" "$(xcode-select -p 2>/dev/null || echo 'non installés')"
fi

titre "Verdict Claude Code"
version_macos=$(sw_vers -productVersion)
majeure=${version_macos%%.*}
if [ "$majeure" -ge 13 ] 2>/dev/null; then
  echo "macOS $version_macos : compatible Claude Code (exigence : macOS 13+)."
  echo "Installation : curl -fsSL https://claude.ai/install.sh | bash"
else
  echo "macOS $version_macos : SOUS le minimum de Claude Code (macOS 13+)."
  echo "Voir docs/imac-2013.md — plan A (Sequoia via OpenCore Legacy Patcher)"
  echo "ou plan B (Claude Code dans une VM Linux, sans toucher à macOS)."
fi

printf '\n(numéro de série et UUID matériel volontairement absents de cette sortie)\n'
