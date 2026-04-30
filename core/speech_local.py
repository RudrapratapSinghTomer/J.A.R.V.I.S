#!/usr/bin/env python3
"""
J.A.R.V.I.S Local Speech Recognition (Vosk)
=============================================
REPLACES Google Speech API with fully offline Vosk.

🔴 SECURITY FIX: The original listener.py used recognize_google()
which sends audio to Google's cloud servers — violating the
zero-cloud, zero-billing policy. Vosk runs 100% locally.

Vosk models:
- vosk-model-small-en-us-0.15 (~40MB) — fast, good for commands
- vosk-model-en-us-0.22 (~1.8GB) — high accuracy, conversational

First run will need model download. After that, fully offline.

Usage:
    from core.speech_local import LocalSpeechRecognizer
    recognizer = LocalSpeechRecognizer()
    text = recognizer.listen()
"""

import os
import json
import logging
import queue
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.speech")

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models" / "vosk"


class LocalSpeechRecognizer:
    """
    Fully offline speech recognition using Vosk.
    Zero cloud. Zero billing. Zero data leaves your machine.
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the local speech recognizer.
        
        Args:
            model_path: Path to Vosk model directory.
                        If None, uses default small model in models/vosk/
        """
        self.model_path = model_path
        self._model = None
        self._recognizer = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Load the Vosk model. Call once on startup.
        
        Returns:
            True if model loaded successfully.
        """
        if self._initialized:
            return True

        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            import sounddevice  # noqa: F401 — verify audio available

            # Suppress Vosk's verbose logging
            SetLogLevel(-1)

            # Find model
            model_path = self._resolve_model_path()
            
            if model_path:
                logger.info(f"Loading Vosk model from: {model_path}")
                self._model = Model(str(model_path))
            else:
                # If resolve returned None, it might have auto-downloaded
                # or we are using the internal Vosk cache
                logger.info("Initializing Vosk with default/cached model...")
                try:
                    self._model = Model(model_name="vosk-model-small-en-us-0.15")
                except Exception as e:
                    logger.error(f"Vosk model loading failed: {e}")
                    return False

            self._recognizer = KaldiRecognizer(self._model, 16000)
            self._recognizer.SetWords(True)
            self._initialized = True
            logger.info("Local speech recognition initialized (Vosk, offline) ✅")
            return True

        except ImportError as e:
            logger.error(
                f"Missing dependency: {e}\n"
                "Install with: pip install vosk sounddevice\n"
                "Then download a model: python -c \"\n"
                "from vosk import Model; Model(model_name='vosk-model-small-en-us-0.15')\""
            )
            return False
        except Exception as e:
            logger.error(f"Speech init failed: {e}")
            return False

    def _resolve_model_path(self) -> Optional[Path]:
        """Find the Vosk model directory."""
        # 1. Explicit path
        if self.model_path and Path(self.model_path).exists():
            return Path(self.model_path)

        # 2. Look in models/vosk/ for any model directory
        if MODELS_DIR.exists():
            for item in sorted(MODELS_DIR.iterdir()):
                if item.is_dir() and (item / "conf" / "mfcc.conf").exists():
                    return item

        # 3. Auto-download small model
        print("\n📥 J.A.R.V.I.S: No speech model found. Downloading (~40MB)...")
        print("   This only happens once. Please wait, Sir.")
        logger.info("No Vosk model found. Downloading small model (~40MB)...")
        try:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            from vosk import Model
            # Vosk auto-downloads to cache, but we can also point it
            model = Model(model_name="vosk-model-small-en-us-0.15")
            print("   ✅ Download complete. Initializing systems...")
            logger.info("Model downloaded successfully.")
            # The model is cached by Vosk internally
            self._model = model
            return None  # Model already loaded
        except Exception as e:
            logger.error(
                f"Could not download model: {e}\n"
                "Manual download:\n"
                "  1. Go to https://alphacephei.com/vosk/models\n"
                "  2. Download 'vosk-model-small-en-us-0.15'\n"
                f"  3. Extract to {MODELS_DIR}/\n"
                f"  Expected path: {MODELS_DIR}/vosk-model-small-en-us-0.15/"
            )
            return None

    def listen(self, timeout: int = 8, phrase_limit: int = 12) -> str:
        """
        Listen for speech and return transcribed text.
        Fully offline — no data leaves the machine.
        
        Args:
            timeout: Max seconds to wait for speech to start
            phrase_limit: Max seconds for a single phrase
            
        Returns:
            Transcribed text (lowercase), or "" if nothing heard
        """
        if not self._initialized:
            if not self.initialize():
                logger.error("Cannot listen — speech recognition not initialized")
                return ""

        try:
            import sounddevice as sd
            import numpy as np

            audio_queue = queue.Queue()

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Audio status: {status}")
                audio_queue.put(bytes(indata))

            # Record audio
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                logger.debug("Listening... (Vosk offline)")

                # Collect audio for up to phrase_limit seconds
                frames_collected = 0
                max_frames = int(16000 * phrase_limit / 4000)
                silence_frames = 0
                max_silence = int(16000 * 2 / 4000)  # 2 seconds of silence = end

                while frames_collected < max_frames:
                    try:
                        data = audio_queue.get(timeout=timeout)
                        frames_collected += 1

                        if self._recognizer.AcceptWaveform(data):
                            result = json.loads(self._recognizer.Result())
                            text = result.get("text", "").strip()
                            if text:
                                logger.info(f">>> Heard (Vosk): '{text}'")
                                return text.lower()

                        # Check for partial results to detect speech
                        partial = json.loads(self._recognizer.PartialResult())
                        if partial.get("partial", ""):
                            silence_frames = 0
                        else:
                            silence_frames += 1
                            if silence_frames > max_silence and frames_collected > 3:
                                break

                    except queue.Empty:
                        logger.debug("Timeout waiting for speech")
                        break

                # Get final result
                final = json.loads(self._recognizer.FinalResult())
                text = final.get("text", "").strip()
                if text:
                    logger.info(f">>> Heard (Vosk final): '{text}'")
                    return text.lower()

                return ""

        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            return ""
        except Exception as e:
            logger.error(f"Listen error: {e}")
            return ""

    def listen_continuous(self):
        """
        Generator that yields transcribed text continuously.
        Use in a loop: for text in recognizer.listen_continuous(): ...
        """
        while True:
            text = self.listen()
            if text:
                yield text
