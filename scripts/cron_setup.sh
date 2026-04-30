#!/bin/bash
# ===========================================================
# J.A.R.V.I.S Cron Installer
# ===========================================================
# Sets up nightly cron jobs for:
#   1. Autonomous learning (1 AM IST / 19:30 UTC)
#   2. Security scan (2 AM IST / 20:30 UTC)
#
# Usage: bash scripts/cron_setup.sh
# ===========================================================

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
JARVIS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${JARVIS_DIR}/J.A.R.V.I.S/bin/python"
CRON_MARKER="# JARVIS-CRON"
CRON_TMP="$(mktemp)"
trap 'rm -f "${CRON_TMP}"' EXIT

echo "=== J.A.R.V.I.S Cron Setup ==="

# Check Python exists in venv
if [ ! -f "${PYTHON}" ]; then
    echo "ERROR: Python not found at ${PYTHON}"
    echo "Activate your venv first: source ${JARVIS_DIR}/J.A.R.V.I.S/bin/activate"
    exit 1
fi

# Make security scan executable
chmod +x "${JARVIS_DIR}/scripts/security_scan.sh"

# Build cron entries
LEARN_CRON="30 19 * * * cd ${JARVIS_DIR} && ${PYTHON} -m skills.autonomous_learner >> ${JARVIS_DIR}/logs/learner_cron.log 2>&1 ${CRON_MARKER}"
SECURITY_CRON="30 20 * * * ${JARVIS_DIR}/scripts/security_scan.sh >> ${JARVIS_DIR}/logs/security_cron.log 2>&1 ${CRON_MARKER}"

# Remove old JARVIS cron entries if any
crontab -l 2>/dev/null | grep -v "${CRON_MARKER}" > "${CRON_TMP}" || true

# Add new entries
echo "${LEARN_CRON}" >> "${CRON_TMP}"
echo "${SECURITY_CRON}" >> "${CRON_TMP}"

# Install
crontab "${CRON_TMP}"

echo ""
echo "✅ Cron jobs installed:"
echo "   📚 Learning:  Daily 1:00 AM IST (19:30 UTC)"
echo "   🔐 Security:  Daily 2:00 AM IST (20:30 UTC)"
echo ""
echo "Verify with: crontab -l"
echo ""
echo "Logs saved to:"
echo "   ${JARVIS_DIR}/logs/learner_cron.log"
echo "   ${JARVIS_DIR}/logs/security_cron.log"
