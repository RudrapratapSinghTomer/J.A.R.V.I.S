import os
import logging
from pathlib import Path
from huggingface_hub import HfApi, HfFolder, Repository, login
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jarvis.huggingface")

class HuggingFaceManager:
    """
    Autonomous Hugging Face Hub Manager.
    Allows J.A.R.V.I.S to manage models, datasets, and training logs.
    """
    def __init__(self):
        # Prioritize JARVIS identity for autonomous operations
        self.token = os.getenv("JARVIS_HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        self.username = os.getenv("JARVIS_NAME") or os.getenv("HUGGINGFACE_USERNAME")
        self.api = HfApi()
        
        if self.token:
            try:
                login(token=self.token)
                logger.info(f"Successfully authenticated with Hugging Face Hub as persona: {self.username}")
            except Exception as e:
                logger.error(f"Hugging Face authentication failed: {e}")
        else:
            logger.warning("No JARVIS_HF_TOKEN or HUGGINGFACE_TOKEN found in .env. Hub operations will be limited.")

    def create_repo(self, repo_name, repo_type="model", private=True):
        """Create a new repository on the Hub."""
        try:
            repo_id = f"{self.username}/{repo_name}"
            url = self.api.create_repo(repo_id=repo_id, repo_type=repo_type, private=private, exist_ok=True)
            logger.info(f"Repository created/verified: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to create repository {repo_name}: {e}")
            return None

    def upload_file(self, path_or_fileobj, path_in_repo, repo_id, repo_type="model"):
        """Upload a single file to a repository."""
        try:
            self.api.upload_file(
                path_or_fileobj=path_or_fileobj,
                path_in_repo=path_in_repo,
                repo_id=repo_id,
                repo_type=repo_type
            )
            logger.info(f"Uploaded {path_in_repo} to {repo_id}")
            return True
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False

    def upload_folder(self, folder_path, repo_id, repo_type="model", commit_message="Autonomous update"):
        """Upload an entire folder (e.g., model weights) to a repository."""
        try:
            self.api.upload_folder(
                folder_path=folder_path,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=commit_message
            )
            logger.info(f"Uploaded folder {folder_path} to {repo_id}")
            return True
        except Exception as e:
            logger.error(f"Folder upload failed: {e}")
            return False

    def download_model(self, repo_id, local_dir):
        """Download a model from the Hub."""
        try:
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            self.api.snapshot_download(repo_id=repo_id, local_dir=local_dir)
            logger.info(f"Model {repo_id} downloaded to {local_dir}")
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def delete_repo(self, repo_id, repo_type="model"):
        """Delete a repository (use with caution)."""
        try:
            self.api.delete_repo(repo_id=repo_id, repo_type=repo_type)
            logger.info(f"Deleted repository: {repo_id}")
            return True
        except Exception as e:
            logger.error(f"Deletion failed: {e}")
            return False

hf_manager = HuggingFaceManager()
