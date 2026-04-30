#!/bin/bash
# ===========================================================
# J.A.R.V.I.S Daily Security Scan
# ===========================================================
# Runs at 2 AM IST (20:30 UTC) via cron.
# All results saved to J.A.R.V.I.S/security/ directory.
#
# Cron entry:
#   30 20 * * * /home/rudrapratap/Desktop/J.A.R.V.I.S/scripts/security_scan.sh
# ===========================================================

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
JARVIS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SECURITY_DIR="${JARVIS_DIR}/security"
DATE=$(TZ=Asia/Kolkata date +%Y-%m-%d)
REPORT="${SECURITY_DIR}/scan_${DATE}.md"
LAST_SCAN_MARKER="${SECURITY_DIR}/.last_scan"

mkdir -p "${SECURITY_DIR}"

# ---- Header ----
cat > "${REPORT}" << EOF
# 🔴 J.A.R.V.I.S Security Scan Report
**Date:** $(TZ=Asia/Kolkata date '+%Y-%m-%d %H:%M IST')  
**Host:** $(hostname)  
**Uptime:** $(uptime -p)

---

EOF

# ---- 1. Open Ports ----
echo "## 🔌 Open Ports (Listening)" >> "${REPORT}"
echo '```' >> "${REPORT}"
ss -tlnp 2>/dev/null | head -30 >> "${REPORT}" || echo "ss command not available" >> "${REPORT}"
echo '```' >> "${REPORT}"
echo "" >> "${REPORT}"

# ---- 2. Ollama Exposure Check ----
echo "## 🤖 Ollama API Exposure" >> "${REPORT}"
if command -v ss &> /dev/null; then
    ollama_binds=$(ss -tlnH 2>/dev/null | awk '$4 ~ /:11434$/ {print $4}')
    if [ -z "${ollama_binds}" ]; then
        echo "ℹ️  Ollama not running at scan time" >> "${REPORT}"
    else
        non_local_bind=$(echo "${ollama_binds}" | grep -Ev '^(127\.0\.0\.1:11434|\[::1\]:11434)$' || true)
        if [ -n "${non_local_bind}" ]; then
            echo "⚠️  **WARNING:** Ollama is network-exposed on: ${non_local_bind}" >> "${REPORT}"
            echo "**Fix:** Bind Ollama to loopback only (127.0.0.1 / ::1)." >> "${REPORT}"
        else
            echo "✅ Ollama bound to localhost only (secure)" >> "${REPORT}"
        fi
    fi
elif curl -s --max-time 3 http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "ℹ️  ss unavailable; localhost probe succeeded (cannot verify external exposure)" >> "${REPORT}"
else
    echo "ℹ️  Ollama not running at scan time" >> "${REPORT}"
fi
echo "" >> "${REPORT}"

# ---- 3. Python Dependency Audit ----
echo "## 📦 Python Dependency Vulnerabilities" >> "${REPORT}"
echo '```' >> "${REPORT}"
cd "${JARVIS_DIR}"
if command -v pip-audit &> /dev/null; then
    # Activate venv if exists
    if [ -f "${JARVIS_DIR}/J.A.R.V.I.S/bin/activate" ]; then
        source "${JARVIS_DIR}/J.A.R.V.I.S/bin/activate"
    fi
    set +e
    pip_audit_output=$(pip-audit --desc 2>&1)
    pip_audit_status=$?
    set -e

    echo "${pip_audit_output}" | head -50 >> "${REPORT}"
    if [ "${pip_audit_status}" -gt 1 ]; then
        echo "⚠️  pip-audit command failed with exit code ${pip_audit_status}" >> "${REPORT}"
    fi
else
    echo "pip-audit not installed. Run: pip install pip-audit" >> "${REPORT}"
fi
echo '```' >> "${REPORT}"
echo "" >> "${REPORT}"

# ---- 4. Suspicious Processes ----
echo "## 🔍 Suspicious Processes" >> "${REPORT}"
echo '```' >> "${REPORT}"
# Check for processes listening on unexpected ports
ps aux --sort=-%mem | head -15 >> "${REPORT}"
echo '```' >> "${REPORT}"
echo "" >> "${REPORT}"

# ---- 5. File Integrity (JARVIS directory changes) ----
echo "## 📁 File Changes Since Last Scan" >> "${REPORT}"
if [ -f "${LAST_SCAN_MARKER}" ]; then
    changes=$(find "${JARVIS_DIR}" \
        -newer "${LAST_SCAN_MARKER}" \
        -not -path "*/__pycache__/*" \
        -not -path "*/.git/*" \
        -not -path "*/security/*" \
        -not -path "*/logs/*" \
        -not -path "*/lib/*" \
        -not -path "*/bin/*" \
        -not -path "*/data/*" \
        -type f 2>/dev/null | head -30)
    if [ -n "${changes}" ]; then
        echo "Files modified since last scan:" >> "${REPORT}"
        echo '```' >> "${REPORT}"
        echo "${changes}" >> "${REPORT}"
        echo '```' >> "${REPORT}"
    else
        echo "✅ No unexpected file changes detected" >> "${REPORT}"
    fi
else
    echo "ℹ️  First scan — establishing baseline" >> "${REPORT}"
fi
echo "" >> "${REPORT}"

# ---- 6. Failed SSH Logins (if ssh is running) ----
echo "## 🔑 Failed Login Attempts (last 24h)" >> "${REPORT}"
if command -v journalctl &> /dev/null; then
    failed=$(journalctl -u ssh --since "24 hours ago" 2>/dev/null | grep -i "failed" | tail -10 || true)
    if [ -n "${failed}" ]; then
        echo "⚠️  Failed login attempts detected:" >> "${REPORT}"
        echo '```' >> "${REPORT}"
        echo "${failed}" >> "${REPORT}"
        echo '```' >> "${REPORT}"
    else
        echo "✅ No failed login attempts" >> "${REPORT}"
    fi
else
    echo "ℹ️  journalctl not available — skipping" >> "${REPORT}"
fi
echo "" >> "${REPORT}"

# ---- 7. Disk Space ----
echo "## 💾 Disk Space" >> "${REPORT}"
echo '```' >> "${REPORT}"
df -h "${HOME}" 2>/dev/null | tail -1 >> "${REPORT}" || echo "df unavailable" >> "${REPORT}"
echo '```' >> "${REPORT}"
echo "" >> "${REPORT}"

# ---- 8. Lynis Quick Audit (if installed) ----
echo "## 🛡️ System Audit (Lynis)" >> "${REPORT}"
if command -v lynis &> /dev/null; then
    echo '```' >> "${REPORT}"
    if command -v sudo &> /dev/null && sudo -n true 2>/dev/null; then
        sudo -n lynis audit system --quick --no-colors 2>&1 | grep -E "(Warning|Suggestion|Hardening)" | head -20 >> "${REPORT}" || echo "Lynis scan failed" >> "${REPORT}"
    else
        lynis audit system --quick --no-colors 2>&1 | grep -E "(Warning|Suggestion|Hardening)" | head -20 >> "${REPORT}" || echo "Lynis scan failed (sudo unavailable/non-interactive)" >> "${REPORT}"
    fi
    echo '```' >> "${REPORT}"
else
    echo "ℹ️  Lynis not installed. Optional: \`sudo apt install lynis\`" >> "${REPORT}"
fi
echo "" >> "${REPORT}"

# ---- Update marker ----
touch "${LAST_SCAN_MARKER}"

# ---- Footer ----
echo "---" >> "${REPORT}"
echo "*Scan completed at $(TZ=Asia/Kolkata date '+%H:%M IST'). Next scan: tomorrow 2 AM IST.*" >> "${REPORT}"

echo "[JARVIS Security] Scan complete: ${REPORT}"
