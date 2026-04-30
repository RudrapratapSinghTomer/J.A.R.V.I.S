import logging
import os
import numpy as np
from pathlib import Path
from faster_whisper import WhisperModel

logger = logging.getLogger("jarvis.whisper")

class WhisperSpeechRecognizer:
    """
    High-performance local speech recognition using Faster-Whisper.
    Runs 100% offline on CPU with Int8 quantization.
    """
    def __init__(self, model_size="small.en", device="cpu", compute_type="int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.models_dir = Path(__file__).parent.parent / "models" / "whisper"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self):
        """Load the Whisper model into memory."""
        try:
            logger.info(f"Initializing Faster-Whisper ({self.model_size})...")
            # Set model path to local directory to avoid re-downloading
            self.model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type,
                download_root=str(self.models_dir)
            )
            logger.info("Faster-Whisper engine: READY")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")
            return False

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe raw audio data (numpy array) to text.
        """
        if self.model is None:
            if not self.initialize():
                return ""

        try:
            segments, info = self.model.transcribe(
                audio_data, 
                beam_size=5, 
                vad_filter=True,
                initial_prompt="Jarvis, J.A.R.V.I.S., Rudra, Sir.",
                vad_parameters=dict(
                    min_silence_duration_ms=700,
                    speech_pad_ms=400
                )
            )
            
            segments = list(segments)
            if not segments:
                return ""

            # Check average log probability to filter out hallucinations in noise
            avg_logprob = sum([s.avg_logprob for s in segments]) / len(segments)
            if avg_logprob < -1.0:
                logger.debug(f"Ignoring hallucination due to low logprob ({avg_logprob:.2f}): {segments[0].text}")
                return ""

            text = "".join([segment.text for segment in segments]).strip()
            
            # Confidence filtering: ignore if language probability is too low
            # or if the transcription is likely just noise hallucinations (like "Thank you")
            if info.language_probability < 0.4:
                logger.debug(f"Ignoring low-confidence noise ({info.language_probability:.2f}): {text}")
                return ""
            
            # Common Whisper hallucinations in noise
            if text.lower() in ["thank you.", "thanks for watching.", "subtitles by", "you"]:
                logger.debug(f"Ignoring Whisper hallucination: {text}")
                return ""

            if text:
                logger.info(f"Whisper heard: '{text}' (Lang: {info.language}, Prob: {info.language_probability:.2f})")
            return text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

# Singleton instance
whisper_engine = WhisperSpeechRecognizer()
