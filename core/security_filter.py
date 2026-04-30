import re
import os
import logging

logger = logging.getLogger("jarvis.security_filter")

class SecurityFilter:
    """
    Scans and redacts sensitive information (PII) before it is sent to the cloud LLM.
    """
    def __init__(self):
        # Patterns for common sensitive data
        self.patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "api_key": r"(?:key|token|auth|pwd|password|secret|pass)[\s:=]+['\"]?([a-zA-Z0-9\-_{}]{16,})['\"]?",
            "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "system_path": r"[a-zA-Z]:\\[\\\w\s\.\-\(\)]+" # Windows paths
        }

    def redact(self, text: str) -> str:
        """Replace sensitive strings with [REDACTED_TYPE]."""
        if not text:
            return text
            
        redacted_text = text
        for label, pattern in self.patterns.items():
            def replacer(match):
                # Keep the label but hide the value
                return f"[REDACTED_{label.upper()}]"
            
            try:
                redacted_text = re.sub(pattern, replacer, redacted_text, flags=re.IGNORECASE)
            except Exception as e:
                logger.error(f"Redaction failed for {label}: {e}")
                
        return redacted_text

    def is_sensitive_command(self, command: str) -> bool:
        """Detect if a command requires Human-in-the-Loop approval."""
        sensitive_keywords = [
            "delete", "remove", "format", "chmod", "grant", "permission", 
            "access", "password", "env", "credentials", "token", "shutdown",
            "restart", "install", "uninstall", "shell", "terminal"
        ]
        cmd_lower = command.lower()
        return any(k in cmd_lower for k in sensitive_keywords)

security_filter = SecurityFilter()
