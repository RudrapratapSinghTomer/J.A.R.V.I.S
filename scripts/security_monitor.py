#!/usr/bin/env python3
"""
J.A.R.V.I.S Security Monitor
==============================
Reads the latest security scan report and surfaces alerts.
Called by main.py on every startup.

Provides:
- get_latest_report()  → returns parsed security summary
- check_security()     → prints 🔴 SECURITY ALERT if issues found
"""

import os
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("jarvis.security")

SECURITY_DIR = Path(__file__).parent.parent / "security"
SCANNER_SCRIPT = Path(__file__).parent / "enhanced_security_scan.py"


def run_enhanced_scan():
    """Execute the Python-based enhanced security scanner."""
    try:
        logger.info("Executing Enhanced Security Scan...")
        subprocess.run([sys.executable, str(SCANNER_SCRIPT)], check=True, capture_output=True)
    except Exception as e:
        logger.error(f"Enhanced scan execution failed: {e}")


def get_latest_report() -> dict:
    """
    Find and parse the most recent security scan report.
    """
    if not SECURITY_DIR.exists():
        os.makedirs(SECURITY_DIR, exist_ok=True)
    
    # Run a fresh scan if no report exists or if requested
    reports = sorted(SECURITY_DIR.glob("scan_*.md"), reverse=True)
    if not reports:
        run_enhanced_scan()
        reports = sorted(SECURITY_DIR.glob("scan_*.md"), reverse=True)

    if not reports:
        return {"date": None, "path": None, "warnings": ["Failed to generate security report."], "ok": False, "raw_text": ""}

    latest = reports[0]
    raw_text = latest.read_text(encoding="utf-8")

    # Extract warnings and vulnerability findings.
    warnings = []
    warning_markers = ["WARNING", "CRITICAL", "ALERT", "vulnerable", "CVE-"]
    
    for line in raw_text.splitlines():
        line_stripped = line.strip()
        if any(marker in line_stripped.upper() for marker in warning_markers):
            warnings.append(line_stripped)

    return {
        "date": latest.stem.replace("scan_", ""),
        "path": str(latest),
        "warnings": warnings,
        "ok": len(warnings) == 0,
        "raw_text": raw_text,
    }


def check_security(speak_func=None):
    """
    Check security status and report to user.
    """
    # [IMPROVEMENT] Always run a quick scan on startup to ensure no new tools are running
    run_enhanced_scan()
    report = get_latest_report()

    if report["ok"]:
        msg = "Security: All clear. No issues found in last scan."
        logger.info(msg)
        if speak_func:
            speak_func("Security check passed. Your system is secure, Sir.")
        return True
    else:
        # Surface every warning
        header = f"SECURITY ALERT — Scan: {report['date']}"
        logger.warning(header)
        print(f"\n{'='*60}")
        print(header)
        print(f"{'='*60}")
        
        for w in report["warnings"]:
            print(f"  {w}")
            logger.warning(f"  {w}")
        
        print(f"  Full report: {report['path']}")
        print(f"{'='*60}\n")

        if speak_func:
            count = len(report["warnings"])
            speak_func(
                f"Security alert, Sir. I have found {count} potential vulnerabilities. "
                f"I am displaying the report now."
            )
        
        return False
