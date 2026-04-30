import asyncio
import os
import logging
import time
from pathlib import Path
from core.config import SpeechConfig

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

logger = logging.getLogger("jarvis.speech_out")

class NeuralSpeaker:
    """
    Modular Neural TTS System for J.A.R.V.I.S.
    Supports multiple backends (Edge-TTS, Kokoro, etc.)
    """
    def __init__(self):
        self.backend_type = SpeechConfig.TTS_BACKEND
        self.temp_dir = Path(__file__).parent.parent / "data" / "tts"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._audio_ready = False
        self._speak_lock = asyncio.Lock()

        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
            self._audio_ready = True
        except Exception as e:
            logger.error(f"Pygame mixer init failed: {e}")

    async def speak(self, text: str):
        """Main speak entry point. Routes to configured backend."""
        if not text:
            return

        # logger.debug(f"Speaking ({self.backend_type}): {text[:50]}...")
        
        try:
            # Serialize playback on Windows to avoid file-lock races.
            async with self._speak_lock:
                if self.backend_type == "edge-tts":
                    await self._speak_edge(text)
                elif self.backend_type == "kokoro":
                    await self._speak_kokoro(text)
                else:
                    # Fallback to legacy pyttsx3 if configured
                    await self._speak_legacy(text)
        except Exception as e:
            logger.error(f"TTS Error ({self.backend_type}): {e}")
            print(f"[JARVIS] {text}")

    async def _speak_edge(self, text: str):
        """Cloud-based Neural TTS using Edge-TTS."""
        import edge_tts
        temp_file = self.temp_dir / f"speech_{int(time.time() * 1000)}.mp3"
        communicate = edge_tts.Communicate(text, SpeechConfig.VOICE_CLOUD, rate="+10%")
        await communicate.save(str(temp_file))
        await self._play_audio(temp_file)

        try:
            temp_file.unlink(missing_ok=True)
        except Exception as e:
            logger.debug(f"Could not remove temp speech file {temp_file}: {e}")

    async def _speak_kokoro(self, text: str):
        """Local-based High-Fidelity TTS using Kokoro."""
        # Note: This is a placeholder for Phase 3 implementation.
        # We will integrate the kokoro-82M pipeline here.
        logger.warning("Kokoro backend is being integrated. Falling back to Edge-TTS.")
        await self._speak_edge(text)

    async def _speak_legacy(self, text: str):
        """Legacy local TTS using pyttsx3."""
        # This is a non-async library, we run it in a thread
        import pyttsx3
        def _say():
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.say(text)
            engine.runAndWait()
        
        await asyncio.to_thread(_say)

    def stop(self):
        """Immediately stop any current audio playback."""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                # logger.info("Listening...")
                # logger.info("Speaking...")
                logger.info("Speech playback stopped by system.")
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")

    async def _play_audio(self, audio_file: Path):
        """Play the generated audio file using pygame."""
        if not self._audio_ready or not audio_file.exists():
            return

        try:
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            start_play = time.time()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                if time.time() - start_play > 400: # 5 minute safety timeout for long TTS
                    logger.warning("Audio playback timed out.")
                    break
            pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"Playback error: {e}")

# Singleton instance
speaker = NeuralSpeaker()
