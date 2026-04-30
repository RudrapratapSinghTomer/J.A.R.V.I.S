import asyncio
import os
import logging
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure .env is loaded
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

logger = logging.getLogger("jarvis.claw")

class ClawBrain:
    """
    Asynchronous wrapper for the 'claw' CLI (Claude Code).
    Integrated with Ollama via OpenAI-compatible endpoint.
    """
    def __init__(self):
        self.workspace_root = str(Path(__file__).parent.parent)
        self._first_run = True

    @property
    def model(self) -> str:
        """Returns the current model from the environment configuration."""
        return self._get_env_config()["model"]

    def _get_env_config(self):
        """Re-read env variables at runtime to ensure we have the latest."""
        base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")

        default_path = self._resolve_claw_path()
        return {
            "path": os.getenv("CLAW_PATH", default_path),
            "model": os.getenv("CLAW_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:latest")),
            "base_url": base_url,
            "perm": os.getenv("CLAW_PERMISSION_MODE", "workspace-write"),
            "openai_key": os.getenv("OPENAI_API_KEY", "local-dev-token"),
            "anthropic_key": os.getenv("ANTHROPIC_API_KEY")
        }

    @staticmethod
    def _is_runnable(command: str) -> bool:
        p = Path(command)
        if p.exists() and p.is_file():
            return True
        return shutil.which(command) is not None

    def _resolve_claw_path(self) -> str:
        """Resolve a likely claw executable path across PATH and local submodule builds."""
        binary_name = "claw.exe" if os.name == "nt" else "claw"
        local_candidate_release = (
            Path(__file__).parent.parent
            / "submodules"
            / "Claude Local Setup"
            / "claw-code"
            / "rust"
            / "target"
            / "release"
            / binary_name
        )
        local_candidate_debug = (
            Path(__file__).parent.parent
            / "submodules"
            / "Claude Local Setup"
            / "claw-code"
            / "rust"
            / "target"
            / "debug"
            / binary_name
        )

        candidates = [
            os.getenv("CLAW_PATH", "").strip(),
            shutil.which("claw"),
            str(local_candidate_release),
            str(local_candidate_debug),
            "/usr/local/bin/claw" if os.name != "nt" else "claw.exe",
        ]

        for candidate in candidates:
            if not candidate:
                continue
            p = Path(candidate)
            if p.exists() and p.is_file():
                return str(p)
            if candidate == "claw.exe":
                return candidate
        return "claw"

    async def execute(self, prompt: str, override_model: Optional[str] = None) -> str:
        """
        Executes a prompt using the 'claw' CLI in non-interactive mode.
        """
        config = self._get_env_config()
        model_to_use = override_model or config["model"]
        if not self._is_runnable(config["path"]):
            return (
                "Sir, I could not locate the Claw executable. "
                "Please set CLAW_PATH or build claw in submodules."
            )
        
        if self._first_run:
            masked_key = f"{config['openai_key'][:5]}..." if config['openai_key'] else "None"
            logger.info(f"Claw Core Config: Model={config['model']}, BaseURL={config['base_url']}, Key={masked_key}")
            self._first_run = False
        
        cmd = [
            config["path"],
            "--model", model_to_use,
            "--output-format", "text",
            "--compact",
            "--dangerously-skip-permissions", # Auto-approve tool execution for autonomous operation
            "prompt",
            prompt
        ]

        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Set the environment variables for claw
        env = os.environ.copy()
        env["OPENAI_BASE_URL"] = config["base_url"]
        env["OPENAI_API_KEY"] = config["openai_key"] or "local-dev-token"
        if config["anthropic_key"]:
            env["ANTHROPIC_API_KEY"] = config["anthropic_key"]

        try:
            def _run():
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    cwd=self.workspace_root,
                    env=env,
                    timeout=int(os.getenv("CLAW_TIMEOUT_SECONDS", "300")),
                )

            result = await asyncio.to_thread(_run)
            
            if result.returncode != 0:
                error_msg = (result.stderr or "").strip()
                logger.error(f"Claw Error (Code {result.returncode}): {error_msg}")
                return f"I apologize Sir, I encountered an error while processing that with my primary core: {error_msg}"

            output = (result.stdout or "").strip()
            
            # Clean up the output (remove ANSI escape sequences if any)
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@~])')
            clean_output = ansi_escape.sub('', output)
            
            return clean_output

        except subprocess.TimeoutExpired:
            return "Sir, the primary core timed out before completing the task."
        except Exception as e:
            logger.error(f"Failed to execute claw: {e}")
            return f"Sir, I was unable to reach my primary core. Error: {str(e)}"

    async def health_check(self) -> dict:
        """Checks if the claw binary is accessible and responds."""
        config = self._get_env_config()
        if not self._is_runnable(config["path"]):
            return {"ok": False, "error": f"Claw binary not found at: {config['path']}"}
        try:
            env = os.environ.copy()
            env["OPENAI_BASE_URL"] = config["base_url"]
            env["OPENAI_API_KEY"] = config["openai_key"] or "local-dev-token"
            if config["anthropic_key"]:
                env["ANTHROPIC_API_KEY"] = config["anthropic_key"]

            def _run():
                return subprocess.run(
                    [config["path"], "version"],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=env,
                    timeout=30,
                )

            result = await asyncio.to_thread(_run)
            
            if result.returncode == 0:
                version = (result.stdout or "").strip()
                return {
                    "ok": True,
                    "version": version,
                    "model": config["model"],
                    "base_url": config["base_url"]
                }
            else:
                return {"ok": False, "error": f"Claw failed: {(result.stderr or '').strip()}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Claw health check timed out."}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def set_model(self, model_name: str):
        """Updates the default model for future requests."""
        os.environ["CLAW_MODEL"] = model_name
        logger.info(f"Claw model updated to: {model_name}")

# Singleton instance
claw_brain = ClawBrain()
