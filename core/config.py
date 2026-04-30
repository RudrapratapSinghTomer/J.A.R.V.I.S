import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

class SpeechConfig:
    """Configuration for JARVIS Speech Subsystem."""
    
    # --- STT (Speech-to-Text) ---
    # Options: "faster-whisper", "legacy-sr" (SpeechRecognition)
    STT_BACKEND = os.getenv("JARVIS_STT_BACKEND", "faster-whisper")
    WHISPER_MODEL = os.getenv("JARVIS_WHISPER_MODEL", "base.en")
    
    # --- TTS (Text-to-Speech) ---
    # Options: "edge-tts", "kokoro", "pyttsx3" (legacy)
    TTS_BACKEND = os.getenv("JARVIS_TTS_BACKEND", "edge-tts")
    VOICE_CLOUD = os.getenv("JARVIS_VOICE_CLOUD", "en-GB-RyanNeural")
    VOICE_LOCAL = os.getenv("JARVIS_VOICE_LOCAL", "af_bella") # Default Kokoro voice
    
    # --- Wake Word ---
    WAKE_WORDS = ["jarvis", "buddy", "computer", "hi jarvis", "hey jarvis", "ok computer"]
    CONVERSATION_TIMEOUT = 30  # Seconds
    
    # --- Audio Input ---
    INPUT_DEVICE_INDEX = os.getenv("JARVIS_INPUT_DEVICE", None)
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 512 # Smaller chunks for faster VAD response
    
    # --- VAD (Voice Activity Detection) ---
    VAD_THRESHOLD = 0.5
    MIN_SILENCE_MS = 1000  # Stop recording after 1s of silence

class SystemConfig:
    """General JARVIS settings."""
    NAME = "J.A.R.V.I.S"
    USER_NAME = os.getenv("JARVIS_USER", "Sir")
    DEBUG = os.getenv("JARVIS_DEBUG", "false").lower() == "true"
    
    # Memory
    MEMORY_ENABLED = os.getenv("JARVIS_MEMORY_ENABLED", "true").lower() == "true"
    
    # Process Management
    LOCK_FILE = BASE_DIR / "data" / "jarvis.lock"
