import os

# Fix Windows symlink privilege error (WinError 1314).
# These must be set BEFORE any HuggingFace/SpeechBrain imports.
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
# Tell SpeechBrain to use direct file copy instead of symlinks on Windows
os.environ["SPEECHBRAIN_FETCH_STRATEGY"] = "copy"

import torch
import torchaudio
import numpy as np
import logging
import soundfile as sf  # [NEW] Robust fallback for audio loading
from pathlib import Path
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy

logger = logging.getLogger("jarvis.voice_auth")

class VoiceAuthenticator:
    def __init__(self, model_source="speechbrain/spkrec-ecapa-voxceleb"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_dir = Path("models/voice_auth")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initializing Voice Auth on {self.device}...")
        try:
            # FORCE DOWNLOAD to avoid symlink issues on Windows
            from huggingface_hub import snapshot_download
            logger.info("Ensuring model files are downloaded locally (no symlinks)...")
            local_path = snapshot_download(
                repo_id=model_source,
                local_dir=self.model_dir,
                local_dir_use_symlinks=False,
                token=os.getenv("JARVIS_HF_TOKEN")
            )
            
            self.classifier = EncoderClassifier.from_hparams(
                source=str(self.model_dir), 
                run_opts={"device": self.device},
                savedir=str(self.model_dir),
                local_strategy=LocalStrategy.COPY,
            )
            logger.info("Neural Voice model ready.")
        except Exception as e:
            logger.error(f"Failed to load Voice Auth model: {e}", exc_info=True)
            self.classifier = None

        self.host_print_path = Path("context/host_voice_print.npy")
        self.host_embedding = self._load_host_print()

    def _load_host_print(self):
        if self.host_print_path.exists():
            try:
                return np.load(self.host_print_path)
            except Exception as e:
                logger.error(f"Error loading host voice print: {e}")
        return None

    def extract_embedding(self, audio_path):
        """Extract 192-dim embedding from audio file."""
        if not self.classifier:
            logger.error("Classifier model not loaded. Cannot extract embedding.")
            return None
        
        if not audio_path or not Path(audio_path).exists():
            logger.error(f"Audio file not found: {audio_path}")
            return None

        try:
            # Check file size
            size = Path(audio_path).stat().st_size
            if size < 100:
                logger.error(f"Audio file is too small ({size} bytes): {audio_path}")
                return None

            logger.info(f"Loading audio for embedding: {audio_path} ({size} bytes)")
            
            # [FIX] Use soundfile natively. torchaudio.load causes massive FFmpeg/torchcodec exception spam on Windows.
            try:
                data, fs = sf.read(audio_path)
                signal = torch.from_numpy(data).float()
                if signal.ndim == 1:
                    signal = signal.unsqueeze(0)
                else:
                    signal = signal.transpose(0, 1) # Convert to (channels, frames)
            except Exception as e:
                logger.error(f"Failed to load audio with soundfile: {e}")
                return None
            
            logger.info(f"Raw audio loaded: shape={signal.shape}, fs={fs}")
            
            # [FIX] Mono Conversion: ECAPA-TDNN expects (1, L) or (L,)
            if signal.shape[0] > 1:
                logger.info(f"Converting {signal.shape[0]} channels to mono...")
                signal = torch.mean(signal, dim=0, keepdim=True)
            
            # [FIX] Signal Normalization: Ensure consistent volume levels
            if torch.max(torch.abs(signal)) > 0:
                signal = signal / torch.max(torch.abs(signal))
            
            # ECAPA-TDNN expects 16kHz
            if fs != 16000:
                resampler = torchaudio.transforms.Resample(fs, 16000)
                signal = resampler(signal)
            
            # Convert to embedding
            with torch.no_grad():
                # EncoderClassifier expects (Batch, Time)
                embeddings = self.classifier.encode_batch(signal)
            
            emb_np = embeddings.squeeze().cpu().numpy()
            logger.info(f"Embedding extracted successfully. Shape: {emb_np.shape}")
            return emb_np
        except Exception as e:
            logger.error(f"Embedding extraction failed for {audio_path}: {e}", exc_info=True)
            return None

    def enroll_host(self, audio_paths):
        """Enroll the host using multiple samples."""
        embeddings = []
        logger.info(f"Starting enrollment with {len(audio_paths)} samples.")
        for i, path in enumerate(audio_paths):
            emb = self.extract_embedding(path)
            if emb is not None:
                embeddings.append(emb)
                logger.info(f"Sample {i+1} processed successfully.")
            else:
                logger.warning(f"Sample {i+1} failed embedding extraction.")
        
        if not embeddings:
            logger.error("No valid embeddings extracted from samples. Enrollment aborted.")
            return False
        
        # Average the embeddings for a robust signature
        host_signature = np.mean(embeddings, axis=0)
        np.save(self.host_print_path, host_signature)
        self.host_embedding = host_signature
        logger.info(f"Host enrolled successfully. Signature saved to {self.host_print_path}")
        return True

    def has_signature(self):
        """Check if a host voice signature exists."""
        return self.host_embedding is not None

    def verify(self, audio_path, threshold=0.40):
        """Verify if the audio matches the host embedding."""
        if self.host_embedding is None:
            logger.warning("No host voice print found. Security policy: FAIL-CLOSED.")
            return False
        
        current_emb = self.extract_embedding(audio_path)
        if current_emb is None:
            return False
        
        # Cosine Similarity
        similarity = np.dot(self.host_embedding, current_emb) / (
            np.linalg.norm(self.host_embedding) * np.linalg.norm(current_emb)
        )
        
        logger.info(f"Voice similarity score: {similarity:.4f}")
        return similarity >= threshold

voice_auth = VoiceAuthenticator()
