import os
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jarvis.git")

class GitManager:
    """
    Autonomous Git Manager for J.A.R.V.I.S.
    Ensures commits are attributed to the JARVIS persona using dedicated tokens.
    """
    def __init__(self):
        self.jarvis_token = os.getenv("JARVIS_GITHUB_TOKEN")
        self.jarvis_name = os.getenv("JARVIS_NAME", "Jarvis AI_Assistant")
        self.jarvis_email = os.getenv("JARVIS_EMAIL", "rudra.jarvisai@gmail.com")
        
        if not self.jarvis_token:
            logger.warning("JARVIS_GITHUB_TOKEN not found. Git operations will use system defaults.")

    def _run_git(self, args, cwd=None):
        """Helper to run git commands with the JARVIS identity."""
        env = os.environ.copy()
        # Ensure the token is used for authentication if available
        # Note: For HTTPS, we usually use the token in the URL or via a credential helper.
        # Here we just set the local config for the specific commit.
        
        try:
            # 1. Temporarily set user identity for the next action
            subprocess.run(["git", "config", "user.name", self.jarvis_name], cwd=cwd, check=True)
            subprocess.run(["git", "config", "user.email", self.jarvis_email], cwd=cwd, check=True)
            
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            return None

    def commit_and_push(self, repo_path, message, branch="main"):
        """Commit changes and push to remote using JARVIS identity."""
        repo_path = str(Path(repo_path).absolute())
        
        logger.info(f"JARVIS initiating commit in {repo_path}...")
        
        # Add changes
        self._run_git(["add", "."], cwd=repo_path)
        
        # Commit
        commit_res = self._run_git(["commit", "-m", f"[JARVIS] {message}"], cwd=repo_path)
        if commit_res:
            logger.info("Commit successful.")
            
            # Push (requires token setup in remote URL)
            # We assume the remote is already configured with a token-based URL or SSH
            # If not, we can construct the push URL here.
            try:
                self._run_git(["push", "origin", branch], cwd=repo_path)
                logger.info(f"Pushed to {branch} successfully.")
                return True
            except Exception as e:
                logger.error(f"Push failed: {e}")
                return False
        return False

git_manager = GitManager()
