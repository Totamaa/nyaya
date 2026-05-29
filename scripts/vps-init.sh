#!/usr/bin/env bash
# =============================================================================
# vps-init.sh — Setup initial du VPS pour Nyaya
#
# À exécuter en root (ou avec sudo) sur le VPS, une seule fois.
#
# Usage :
#   bash vps-init.sh '<contenu_de_la_cle_publique_ssh>'
#
# Exemple complet depuis la machine de dev :
#   scp scripts/vps-init.sh root@vps:/tmp/
#   ssh root@vps "bash /tmp/vps-init.sh '$(cat ~/.ssh/id_ed25519_nyaya_deploy.pub)'"
#
# Ce script :
#   1. Crée l'utilisateur système "nyaya" (mot de passe verrouillé, SSH uniquement)
#   2. Définit /opt/nyaya comme répertoire de déploiement
#   3. Ajoute "nyaya" au groupe docker
#   4. Configure ~/.ssh/authorized_keys avec la clé publique fournie
# =============================================================================

set -euo pipefail

# ── Vérifications préalables ──────────────────────────────────────────────────

if [[ "${EUID}" -ne 0 ]]; then
  echo "❌ Ce script doit être exécuté en root (ou via sudo)." >&2
  exit 1
fi

if [[ $# -lt 1 || -z "${1}" ]]; then
  echo "❌ Usage : bash vps-init.sh '<contenu_cle_publique_ssh>'" >&2
  echo "   Ex    : bash vps-init.sh 'ssh-ed25519 AAAA... github-actions-nyaya'" >&2
  exit 1
fi

PUBLIC_KEY="${1}"
APP_USER="nyaya"
APP_DIR="/opt/nyaya"

echo "=== Nyaya — Initialisation VPS ==="
echo ""

# ── 1. Créer l'utilisateur ────────────────────────────────────────────────────

if id "${APP_USER}" &>/dev/null; then
  echo "ℹ️  L'utilisateur '${APP_USER}' existe déjà — skip création"
else
  useradd \
    --create-home \
    --home-dir "${APP_DIR}" \
    --shell /bin/bash \
    --comment "Nyaya deploy user — géré par CI/CD" \
    "${APP_USER}"
  echo "✅ Utilisateur '${APP_USER}' créé"
fi

# Verrouiller le mot de passe : connexion SSH par clé uniquement, jamais par mot de passe
passwd -l "${APP_USER}"
echo "✅ Mot de passe verrouillé (SSH key uniquement)"

# ── 2. Configurer /opt/nyaya ──────────────────────────────────────────────────

mkdir -p "${APP_DIR}"
chown "${APP_USER}:${APP_USER}" "${APP_DIR}"

# 750 : nyaya peut lire/écrire/exécuter, son groupe aussi, les autres n'ont aucun accès
chmod 750 "${APP_DIR}"
echo "✅ Répertoire '${APP_DIR}' configuré (chmod 750)"

# ── 3. Ajouter au groupe docker ───────────────────────────────────────────────

# Nécessaire pour que "nyaya" puisse lancer "docker compose" sans sudo.
# Note : appartenir au groupe docker équivaut à des droits root sur le socket Docker.
# C'est acceptable pour un user de déploiement dédié sur un VPS mono-tenant.

if getent group docker &>/dev/null; then
  usermod -aG docker "${APP_USER}"
  echo "✅ '${APP_USER}' ajouté au groupe 'docker'"
else
  echo "⚠️  Le groupe 'docker' n'existe pas encore." >&2
  echo "    Installez Docker, puis relancez ce script ou exécutez :" >&2
  echo "    usermod -aG docker ${APP_USER}" >&2
fi

# ── 4. Configurer la clé SSH ──────────────────────────────────────────────────

SSH_DIR="${APP_DIR}/.ssh"
AUTH_KEYS="${SSH_DIR}/authorized_keys"

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

# Ajouter la clé si elle n'est pas déjà présente
if ! grep -qF "${PUBLIC_KEY}" "${AUTH_KEYS}" 2>/dev/null; then
  echo "${PUBLIC_KEY}" >> "${AUTH_KEYS}"
  echo "✅ Clé publique ajoutée à authorized_keys"
else
  echo "ℹ️  Clé publique déjà présente dans authorized_keys — skip"
fi

chmod 600 "${AUTH_KEYS}"
chown -R "${APP_USER}:${APP_USER}" "${SSH_DIR}"

# ── Résumé ────────────────────────────────────────────────────────────────────

echo ""
echo "=== Setup terminé ==="
echo ""
echo "Utilisateur  : ${APP_USER}"
echo "Répertoire   : ${APP_DIR}"
echo "Groupes      : $(id -Gn ${APP_USER})"
echo ""
echo "Tester la connexion depuis la machine de dev :"
echo "  ssh -i ~/.ssh/id_ed25519_nyaya_deploy ${APP_USER}@<ip_vps> 'whoami && docker info | head -3'"
echo ""
echo "Valeurs pour les GitHub Secrets :"
echo "  VPS_USER = ${APP_USER}"
echo "  VPS_HOST = <ip_ou_hostname_du_vps>"
echo "  VPS_SSH_KEY = <contenu_de_id_ed25519_nyaya_deploy>"
