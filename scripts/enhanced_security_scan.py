import os
import re
import psutil
import socket
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("jarvis.security_scan")

class EnhancedScanner:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.report_path = self.root_dir / "security" / f"scan_{datetime.now().strftime('%Y-%m-%d')}.md"
        self.warnings = []

    def scan_for_secrets(self):
        """Scan all files for hardcoded API keys, passwords, or tokens."""
        secret_patterns = {
            "Generic Secret": r"(?i)(key|token|auth|pwd|password|secret|pass)[\s:=]+['\"]([a-zA-Z0-9\-_{}]{16,})['\"]",
            # Require Gmail/app-pass context to avoid false positives from normal words.
            "Gmail App Pass": r"(?is)(gmail|app[\s_-]?pass(?:word)?)\s*[:=]?\s*['\"]([a-z]{4}\s?[a-z]{4}\s?[a-z]{4}\s?[a-z]{4})['\"]",
            "Private Key": r"-----BEGIN RSA PRIVATE KEY-----"
        }
        
        # Files to ignore
        ignore_exts = {'.pyc', '.exe', '.bin', '.png', '.jpg', '.mp3', '.git'}
        ignore_dirs = {
            ".git", "venv", "__pycache__", "node_modules", ".claw",
            ".code-review-graph", "models", "submodules"
        }
        ignore_files = {
            "enhanced_security_scan.py",
            "jarvis_async.log",
            "dataset.csv",
        }
        
        for path in self.root_dir.rglob("*"):
            if any(part in ignore_dirs for part in path.parts):
                continue
            if path.name in ignore_files:
                continue
            if path.is_file() and path.suffix not in ignore_exts:
                try:
                    content = path.read_text(errors='ignore')
                    for name, pattern in secret_patterns.items():
                        if re.search(pattern, content):
                            # Don't flag .env or .env.example as they are expected to have labels
                            if path.name not in [".env", ".env.example"]:
                                self.warnings.append(f"CRITICAL: Possible {name} found in {path.relative_to(self.root_dir)}")
                except Exception as e:
                    logger.error(f"Could not scan {path}: {e}")

    def scan_network(self):
        """Check for unauthorized external port exposure."""
        try:
            # Check if Ollama or other local services are exposed to the internet
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'LISTEN':
                    laddr = conn.laddr
                    if laddr.ip not in ['127.0.0.1', '::1', '0.0.0.0']:
                        self.warnings.append(f"WARNING: Service listening on non-local IP: {laddr.ip}:{laddr.port}")
        except Exception as e:
            logger.error(f"Network scan failed: {e}")

    def scan_processes(self):
        """Check for suspicious monitoring tools or debuggers."""
        suspicious = ["wireshark", "tcpview", "processhacker", "x64dbg"]
        for proc in psutil.process_iter(['name']):
            try:
                if any(s in proc.info['name'].lower() for s in suspicious):
                    self.warnings.append(f"ALERT: Suspicious tool running: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def generate_report(self):
        """Save the findings to a markdown report."""
        os.makedirs(self.report_path.parent, exist_ok=True)
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write(f"# J.A.R.V.I.S Enhanced Security Report\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n")
            if not self.warnings:
                f.write("All systems secure. No vulnerabilities detected.\n")
            else:
                f.write(f"[WARNING] {len(self.warnings)} Warnings Found!\n\n")
                for w in self.warnings:
                    f.write(f"- {w}\n")
            
            f.write("\n---\n*Scan performed by J.A.R.V.I.S Security Core*")
        
        return self.report_path

if __name__ == "__main__":
    scanner = EnhancedScanner(os.getcwd())
    scanner.scan_for_secrets()
    scanner.scan_network()
    scanner.scan_processes()
    report = scanner.generate_report()
    print(f"Scan complete. Report generated at: {report}")
