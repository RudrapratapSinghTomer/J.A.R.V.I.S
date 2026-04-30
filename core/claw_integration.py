import subprocess
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("jarvis.claw")

class ClawClient:
    """
    Wrapper for the 'claw' CLI to provide agentic LLM capabilities to J.A.R.V.I.S.
    """
    def __init__(self, binary_path=None):
        if binary_path is None:
            binary_name = "claw.exe" if os.name == "nt" else "claw"
            candidates = [
                Path(__file__).parent.parent / "submodules" / "Claude Local Setup" / "claw-code" / "rust" / "target" / "debug" / binary_name,
                Path(__file__).parent.parent / "submodules" / "claw-code-src" / "rust" / "target" / "debug" / binary_name,
            ]
            binary_path = next((p for p in candidates if p.exists()), candidates[0])
        self.binary_path = Path(binary_path)
        self.model = os.getenv("CLAW_MODEL", os.getenv("OLLAMA_MODEL", "qwen3.5:397b-cloud"))
        self.base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
        
    def is_available(self):
        """Check if claw binary exists."""
        return self.binary_path.exists()
        
    def prompt(self, text, output_format="text"):
        """
        Execute a one-shot prompt through claw.
        """
        if not self.is_available():
            return "Error: Claw binary not found. Please build it first."
            
        env = os.environ.copy()
        env["OPENAI_BASE_URL"] = self.base_url
        env["OPENAI_API_KEY"] = "local-dev-token"
        
        # Ensure Anthropic keys are NOT used
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        
        cmd = [
            str(self.binary_path),
            "--model", self.model,
            "--output-format", output_format,
            "prompt", text
        ]
        
        try:
            logger.info(f"Invoking Claw: {text[:50]}...")
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=180 # Complex tasks can take time
            )
            
            if result.returncode != 0:
                logger.error(f"Claw error: {result.stderr}")
                return f"Claw error: {result.stderr}"
                
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            logger.error("Claw prompt timed out")
            return "I apologize, Sir. The task was taking too long and I had to stop it."
        except Exception as e:
            logger.error(f"Claw invocation failed: {e}")
            return f"Error invoking Claw: {e}"

# Singleton instance
claw = ClawClient()
