#!/bin/bash
# Régler l'iMac pour qu'il reste allumé et joignable en permanence.
#
# Par défaut le script n'applique RIEN : il affiche les commandes qu'il exécuterait
# et l'état actuel. Il faut passer --apply pour qu'il agisse (et il demandera sudo).
#
# Usage :
#   bash scripts/imac-24-7.sh            # simulation, aucun changement
#   bash scripts/imac-24-7.sh --apply    # applique les réglages d'énergie

set -u

APPLIQUER=0
[ "${1:-}" = "--apply" ] && APPLIQUER=1

if [ "$(uname -s)" != "Darwin" ]; then
  echo "Ce script est prévu pour macOS (uname = $(uname -s))." >&2
  exit 1
fi

# sleep 0        : la machine ne se met jamais en veille
# disksleep 0    : les disques ne s'arrêtent pas (évite les réveils lents)
# displaysleep 15: l'écran s'éteint, lui, au bout d'un quart d'heure
# womp 1         : réveil à la demande du réseau
# autorestart 1  : redémarrage automatique après une coupure de courant
# powernap 0     : pas de réveils programmés en arrière-plan
REGLAGES="sleep=0 disksleep=0 displaysleep=15 womp=1 autorestart=1 powernap=0"

echo "=== Réglages d'énergie actuels ==="
pmset -g custom 2>/dev/null | sed 's/^ */  /'

echo
echo "=== Cible ==="
for r in $REGLAGES; do echo "  ${r%%=*} → ${r##*=}"; done

commande="sudo pmset -a"
for r in $REGLAGES; do commande="$commande ${r%%=*} ${r##*=}"; done

echo
if [ "$APPLIQUER" -eq 1 ]; then
  echo "=== Application ==="
  echo "$commande"
  # shellcheck disable=SC2086
  sudo pmset -a $(for r in $REGLAGES; do echo "${r%%=*} ${r##*=}"; done)
  echo
  echo "=== Réglages après application ==="
  pmset -g custom 2>/dev/null | sed 's/^ */  /'
else
  echo "=== Simulation : rien n'a été modifié ==="
  echo "Commande qui serait exécutée :"
  echo "  $commande"
  echo
  echo "Relancer avec --apply pour l'appliquer."
fi

cat <<'RESTE'

=== À faire à la main, dans cet ordre ===

  1. SSH            Réglages Système → Partage → Session à distance (Remote Login)
                    puis clé publique uniquement :
                      ssh-copy-id utilisateur@imac.local
                      sudo sed -i '' 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' \
                        /etc/ssh/sshd_config

  2. Accès distant  Tailscale plutôt qu'une redirection de port sur la box.

  3. Session auto   Réglages Système → Utilisateurs → Options → ouverture de session
                    automatique. Sans ça, un redémarrage après coupure laisse la machine
                    bloquée sur l'écran de connexion. (Incompatible avec FileVault actif.)

  4. tmux           brew install tmux — pour qu'une session lancée à distance survive
                    à la coupure de la connexion.

  5. Mises à jour   Les passer en manuel si la machine tourne sous OpenCore Legacy Patcher :
                    chaque mise à jour de macOS efface les root patches.

  6. Time Machine   Vers un second disque externe. La machine a 13 ans.
RESTE
