import logging
import numpy as np
import time
from typing import Optional
from core.config import SpeechConfig

logger = logging.getLogger("jarvis.listener")

class JarvisInterface:
    """
    Modular Voice Interface for J.A.R.V.I.S.
    Supports Legacy (SpeechRecognition) and Modern (Direct Stream) backends.
    
    NOTE: The 'legacy-sr' setup is preserved but disabled by default. 
    We are now proceeding with direct PyAudio capture to solve ALSA/JACK errors.
    """

    def __init__(self, use_google_fallback: bool = False):
        self.use_google_fallback = use_google_fallback
        self.backend = SpeechConfig.STT_BACKEND
        self._whisper = None
        
        # Legacy components (Keep for fallback, but disabled by default)
        self._sr_recognizer = None
        self._microphone = None
        
        # Modern components
        self._pyaudio_stream = None
        self._pa = None

        # Initialize Whisper (shared across backends)
        self._init_speech()
        
        if self.backend == "legacy-sr":
            logger.info("Initializing Legacy SpeechRecognition backend...")
            self._init_legacy_sr()
        else:
            logger.info(f"Initializing Modern {self.backend} backend (Direct Audio)...")
            self._init_pyaudio()

    def _init_speech(self):
        """Initialize speech recognition — Faster-Whisper (Primary)."""
        try:
            from core.speech_whisper import whisper_engine
            self._whisper = whisper_engine
            if self._whisper.initialize():
                logger.info("Speech recognition: Faster-Whisper (Local)")
            else:
                logger.warning("Whisper init failed.")
        except ImportError:
            logger.warning("Faster-Whisper not installed.")

    def _init_legacy_sr(self):
        """Initialize the old SpeechRecognition setup (Deprecated)."""
        try:
            import speech_recognition as sr
            from core.alsa_suppress import suppress_alsa_warnings
            self._sr_recognizer = sr.Recognizer()
            self._sr_recognizer.dynamic_energy_threshold = True
            self._sr_recognizer.energy_threshold = 600
            self._sr_recognizer.pause_threshold = 1.2
            self._sr_recognizer.non_speaking_duration = 0.5
            
            with suppress_alsa_warnings():
                self._microphone = sr.Microphone()
                with self._microphone as source:
                    logger.info("Calibrating legacy microphone...")
                    self._sr_recognizer.adjust_for_ambient_noise(source, duration=1.5)
                    if self._sr_recognizer.energy_threshold < 400:
                        self._sr_recognizer.energy_threshold = 600
            logger.info(f"Legacy SR ready. Energy: {self._sr_recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"Legacy SR init failed: {e}")

    def _init_pyaudio(self):
        """Initialize direct PyAudio stream to avoid ALSA/JACK probing noise."""
        try:
            import pyaudio
            from core.alsa_suppress import suppress_alsa_warnings
            
            with suppress_alsa_warnings():
                self._pa = pyaudio.PyAudio()
                
                # Check for specific device index or use default
                device_index = SpeechConfig.INPUT_DEVICE_INDEX
                if device_index is not None:
                    device_index = int(device_index)
                
                try:
                    self._pyaudio_stream = self._pa.open(
                        format=pyaudio.paInt16,
                        channels=SpeechConfig.CHANNELS,
                        rate=SpeechConfig.SAMPLE_RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=SpeechConfig.CHUNK_SIZE
                    )
                except Exception as e:
                    logger.error(f"Failed to open device {device_index}: {e}")
                    if device_index != 1:
                        logger.info("Trying fallback to Device Index 1...")
                        self._pyaudio_stream = self._pa.open(
                            format=pyaudio.paInt16,
                            channels=SpeechConfig.CHANNELS,
                            rate=SpeechConfig.SAMPLE_RATE,
                            input=True,
                            input_device_index=1,
                            frames_per_buffer=SpeechConfig.CHUNK_SIZE
                        )
                    else:
                        raise
                        
            logger.info(f"Direct PyAudio stream opened (Mode: Modern, Device: {device_index if device_index is not None else 'Default'}).")
        except Exception as e:
            logger.error(f"PyAudio init failed: {e}")
            self._list_audio_devices()

    def _list_audio_devices(self):
        """Helper to list all audio devices if initialization fails."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            logger.info("Listing available audio devices:")
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if info.get('maxInputChannels') > 0:
                    logger.info(f"  [{i}] {info.get('name')}")
            pa.terminate()
        except Exception:
            pass

    def speak(self, text: str):
        """Convert text to speech using the neural speaker."""
        from core.speech_output import speaker
        import asyncio
        
        logger.info(f"J.A.R.V.I.S.: {text}")
        try:
            # Check if there's a running loop to use async speak
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(speaker.speak(text))
            else:
                asyncio.run(speaker.speak(text))
        except Exception:
            # Fallback to simple print
            print(f"[JARVIS] {text}")

    def listen(self):
        """Main listening entry point. Routes to configured backend."""
        if self.backend == "legacy-sr":
            result = self._listen_legacy()
        else:
            result = self._listen_modern()
            
        # Guarantee a 2-tuple (text, audio_path)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return str(result), None

    def _listen_legacy(self) -> str:
        """Old listening logic using SpeechRecognition library."""
        from core.alsa_suppress import suppress_alsa_warnings
        if not self._sr_recognizer or not self._microphone:
            return "", None
        if not self._whisper:
            logger.warning("Whisper engine unavailable in legacy listener path.")
            return "", None
            
        try:
            with suppress_alsa_warnings():
                with self._microphone as source:
                    logger.debug("Legacy listening...")
                    audio = self._sr_recognizer.listen(source, timeout=10, phrase_time_limit=15)
                
            audio_data = np.frombuffer(audio.get_raw_data(convert_rate=16000, convert_width=2), dtype=np.int16)
            audio_float32 = audio_data.astype(np.float32) / 32768.0
            return self._whisper.transcribe(audio_float32), None
        except Exception as e:
            import speech_recognition as sr
            if not isinstance(e, sr.WaitTimeoutError):
                logger.debug(f"Legacy listen state: {e}")
            return "", None

    def _listen_modern(self) -> str:
        """
        New listening logic using direct stream + Intelligent VAD.
        Detects when speech starts and stops automatically.
        """
        if not self._pyaudio_stream:
            return "", None
        if not self._whisper:
            logger.warning("Whisper engine unavailable in modern listener path.")
            return "", None
            
        try:
            frames = []
            # Pre-roll buffer to capture the very start of speech (0.5s)
            pre_roll = []
            max_pre_roll = int(0.5 * SpeechConfig.SAMPLE_RATE / SpeechConfig.CHUNK_SIZE)
            
            logger.debug("Modern listening (VAD Active)...")
            
            # VAD State
            is_recording = False
            silence_start = None
            
            # Adaptive energy threshold (start with a safe floor)
            ambient_energy = 500
            last_log_time = 0
            
            # Safety timeout (don't listen forever)
            start_time = time.time()
            LISTEN_TIMEOUT = 20 

            logger.debug("Listening...")
            
            while time.time() - start_time < LISTEN_TIMEOUT:
                data = self._pyaudio_stream.read(SpeechConfig.CHUNK_SIZE, exception_on_overflow=False)
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                
                # Calculate energy (RMS)
                energy = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
                
                # Dynamic threshold adjustment
                if not is_recording:
                    # Slowly track ambient noise floor
                    ambient_energy = 0.98 * ambient_energy + 0.02 * energy
                    trigger_threshold = ambient_energy + 500 # Increased from 200 to prevent noise triggers
                    
                    # High-frequency logging for calibration
                    if time.time() - start_time < 3.0:
                        logger.debug(f"CALIBRATION: Energy={energy:.1f}, Threshold={trigger_threshold:.1f}")
                    # Noisy logs removed as requested
                    pass
                else:
                    # While recording, be a bit more sensitive to hold the line
                    trigger_threshold = ambient_energy + 250 # Increased from 100

                if energy > trigger_threshold: 
                    if not is_recording:
                        logger.debug(f"Speech detected (Energy: {energy:.1f}, Threshold: {trigger_threshold:.1f})")
                        is_recording = True
                        # Prepend the captured pre-roll
                        frames.extend(pre_roll)
                    
                    frames.append(audio_chunk)
                    silence_start = None
                elif is_recording:
                    frames.append(audio_chunk)
                    if silence_start is None:
                        silence_start = time.time()
                    
                    # Silence check
                    if (time.time() - silence_start) > (SpeechConfig.MIN_SILENCE_MS / 1000.0):
                        logger.debug("Speech ended (silence detected).")
                        break
                else:
                    # Still waiting... maintain pre-roll ring buffer
                    pre_roll.append(audio_chunk)
                    if len(pre_roll) > max_pre_roll:
                        pre_roll.pop(0)
                    continue

            if not frames:
                return "", None

            # Filter out very short recordings (noise spikes < 0.3s)
            duration = len(frames) * SpeechConfig.CHUNK_SIZE / SpeechConfig.SAMPLE_RATE
            if duration < 0.3:
                logger.debug(f"Ignored short audio artifact ({duration:.2f}s)")
                return "", None


            audio_data = np.concatenate(frames).astype(np.float32) / 32768.0
            
            # --- START DATASET LOGGING ---
            import wave
            import csv
            import datetime
            from pathlib import Path
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_dir = Path("data/training_audio")
            audio_dir.mkdir(parents=True, exist_ok=True)
            wav_path = audio_dir / f"{timestamp}.wav"
            
            try:
                # Save the raw 16-bit PCM audio frames
                raw_audio = np.concatenate(frames).astype(np.int16).tobytes()
                with wave.open(str(wav_path), 'wb') as wf:
                    wf.setnchannels(SpeechConfig.CHANNELS)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(SpeechConfig.SAMPLE_RATE)
                    wf.writeframes(raw_audio)
                
                # Get the transcription
                text = self._whisper.transcribe(audio_data)
                
                # Append to dataset.csv
                csv_path = audio_dir / "dataset.csv"
                file_exists = csv_path.exists()
                with open(csv_path, 'a', newline='', encoding='utf-8') as cf:
                    writer = csv.writer(cf)
                    if not file_exists:
                        writer.writerow(['Timestamp', 'AudioFile', 'WhisperHeard', 'Rating', 'GroundTruth'])
                    writer.writerow([timestamp, f"{timestamp}.wav", text, '', ''])
                
                return text, str(wav_path)
                
            except Exception as ex:
                logger.error(f"Error saving training data: {ex}")
                # Fallback to standard transcribe if saving fails
                return self._whisper.transcribe(audio_data), None
            # --- END DATASET LOGGING ---

            
        except Exception as e:
            logger.error(f"Modern VAD listen error: {e}")
            return "", None
