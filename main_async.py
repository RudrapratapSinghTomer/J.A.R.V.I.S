import asyncio
import time
import logging
import os
import threading
import re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# CRITICAL: Set tiktoken cache dir BEFORE any cognee/litellm import.
_TIKTOKEN_CACHE = Path(__file__).parent / "data" / "tiktoken_cache"
_TIKTOKEN_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(_TIKTOKEN_CACHE))

# Core Modules
from core.config import SpeechConfig
from core.listener import JarvisInterface
from core.llm_client import brain
from core.speech_output import speaker
from core.session_manager import Session
from core.intent_router import IntentRouter
from core.mind_loop import mind_loop
from core.prompt_refiner import refiner

# Setup Logging
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(logs_dir / "jarvis_async.log")
    ]
)
logger = logging.getLogger("jarvis.main")


class JarvisAsyncCore:
    def __init__(self):
        self.interface = JarvisInterface()
        self.session = Session()
        self.is_awake = False
        self.last_wake_time = 0
        self.CONVERSATION_TIMEOUT = SpeechConfig.CONVERSATION_TIMEOUT
        self.llm_ready = False
        self.host_mode = True  # Determined during startup_checks via face scan
        self.host_name = os.getenv("JARVIS_HOST_NAME", "Sir")
        self.override_pw = os.getenv("JARVIS_OVERRIDE_PASSWORD", "")
        # Router is created AFTER face scan so it gets the correct host_mode
        self.router = None
        self.mind_loop_task = None
        self.current_cmd_task = None 
        self.listening_announced = False # Prevent repetitive "Listening..."

    @staticmethod
    def _is_wake_text(text_lower: str) -> bool:
        """
        Robust wake-word detection.
        Accepts variants like:
        - jarvis
        - j.a.r.v.i.s
        - j a r v i s
        """
        if "jarvis" in text_lower:
            return True

        compact = re.sub(r"[^a-z]", "", text_lower)
        return "jarvis" in compact

    async def startup_checks(self):
        """
        Run all startup checks before entering the main loop.
        Order: Face-ID → Security → LLM Health → Memory
        """
        # 0. SILENT FACE-ID SCAN — no pop-up, no notification
        logger.info("Performing silent Face-ID scan...")
        loop = asyncio.get_running_loop()
        try:
            from core.face_module import FaceModule
            fm = FaceModule()

            def _scan():
                if fm.initialize() and fm.list_enrolled():
                    return fm.verify(tolerance=0.5)
                return None

            result = await loop.run_in_executor(None, _scan)

            if result is None:
                # No faces enrolled yet — don't cripple JARVIS
                logger.warning("Face-ID: No enrolled faces found. Defaulting to Host mode. Run scripts/enroll_face.py to register.")
                self.host_mode = True
                self.session.host_mode = True
                self.session.recognized_user = "unenrolled"
            else:
                name = result.get("name", "unknown")
                if name not in ("unknown", "no_face", "no_encoding", "error"):
                    self.host_mode = True
                    self.session.host_mode = True
                    self.session.recognized_user = name
                    logger.info(f"Face-ID: HOST verified — '{name}'")
                else:
                    self.host_mode = False
                    self.session.host_mode = False
                    self.session.recognized_user = "guest"
                    logger.info(f"Face-ID: GUEST mode — face result was '{name}'")
        except Exception as e:
            logger.warning(f"Face-ID scan failed (defaulting to Guest mode): {e}")
            self.host_mode = False
            self.session.host_mode = False
            self.session.recognized_user = "error"

        # Build router now that host_mode is determined
        self.router = IntentRouter(self.interface, host_mode=self.host_mode)

        # 1. Security check — ALWAYS runs
        logger.info("Running startup security check...")
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from scripts.security_monitor import check_security
            is_secure = check_security(speak_func=None)
            self.session.security_status = "clean" if is_secure else "warnings_found"
            if not is_secure:
                await speaker.speak("Security alert, Sir. Warnings found in the nightly scan. Please check the logs.")
            else:
                logger.info("Security check passed.")
        except Exception as e:
            logger.warning(f"Security check skipped: {e}")

        # 2. LLM health check
        logger.info("Checking local LLM cores (Claw & Ollama)...")
        try:
            health = await brain.health_check()
            if health["ok"]:
                main_core = health["main"]
                core_health = health[main_core]
                if core_health.get("ok"):
                    model_name = core_health.get("model")
                    if not model_name:
                        try:
                            model_name = brain.model
                        except Exception:
                            model_name = "unknown"
                    logger.info(f"Main Brain ({main_core}) online using {model_name}")
                    self.session.llm_model = model_name
                    self.llm_ready = True
                else:
                    logger.warning(f"Main core {main_core} has issues: {core_health.get('error')}")
                    await speaker.speak(f"Warning: Main core {main_core} is experiencing issues, Sir.")
            else:
                logger.error("All LLM cores are offline.")
                await speaker.speak("Warning: All neural cores are offline. Complex requests will not work, Sir.")
        except Exception as e:
            logger.error(f"Brain health check failed: {e}")

        # 3. Memory initialization (background thread)
        if not self.llm_ready:
            logger.warning("Memory startup skipped — local LLM is not ready.")
            return

        logger.info("Starting memory system in background...")
        self._start_memory_background()

    def _start_memory_background(self):
        """Initialize Cognee off the startup path so voice readiness cannot hang."""
        finished = threading.Event()

        def _run_memory():
            loop = None
            try:
                from memory.cognee_bridge import memory
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _init():
                    try:
                        logger.info("Memory: Initializing engine...")
                        # Increased timeout for initial setup
                        await asyncio.wait_for(memory.initialize(), timeout=60.0)
                        logger.info("Memory: Loading context files...")
                        await asyncio.wait_for(memory.load_context(), timeout=120.0)
                        logger.info("Memory system fully online.")
                    except asyncio.TimeoutError:
                        logger.warning("Memory initialization timed out (background).")
                    except Exception as e:
                        logger.warning(f"Memory background error: {e}")

                loop.run_until_complete(_init())
            except Exception as e:
                logger.error(f"Memory thread failed to start: {e}")
            finally:
                if loop is not None:
                    loop.close()
                finished.set()

        def _watch_memory():
            if not finished.wait(timeout=90):
                logger.warning("Memory startup still running after 90s. Continuing without it.")

        threading.Thread(target=_run_memory, name="jarvis-memory-init", daemon=True).start()
        threading.Thread(target=_watch_memory, name="jarvis-memory-watchdog", daemon=True).start()

    async def startup(self):
        """Perform system initialization."""
        print("\n" + "="*60)
        print("   J.A.R.V.I.S — Asynchronous Neural Assistant")
        print("   Status: 100% Local · Neural Voice · Async Brain")
        print("="*60 + "\n")

        await self.startup_checks()

        # 1. PLAY STARTUP ANTHEM (requested by user)
        # We start this in the background so it doesn't block the system greeting
        asyncio.create_task(self._play_anthem())

        # 2. Identity-aware greeting
        logger.info("Sending final greeting...")
        user = getattr(self.session, 'recognized_user', 'unenrolled')
        if self.host_mode:
            if user == 'unenrolled':
                await speaker.speak("Systems synchronized. No host profile found. Running in unrestricted mode.")
            else:
                await speaker.speak(f"Welcome back, {self.host_name}. All systems are online. Full host access granted.")
        else:
            await speaker.speak("Hello. I am J.A.R.V.I.S. I am currently operating in guest mode with limited access.")
        logger.info("Startup complete.")

    async def _play_anthem(self):
        """Play the user's requested startup song via YouTube."""
        try:
            from skills.youtube_skill import play_video
            # New default anthem: https://youtu.be/pAgnJDJN4VA?si=ksQv5qen0BzxvpKD
            logger.info("Initiating Startup Anthem in background...")
            # Use run_in_executor because play_video is likely blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, play_video, "https://youtu.be/pAgnJDJN4VA?si=ksQv5qen0BzxvpKD")
        except Exception as e:
            logger.warning(f"Failed to play startup anthem: {e}")

    async def run(self):
        """Main Async Loop with PID Lock & Singleton Protection."""
        if not self._acquire_lock():
            return

        try:
            await self.startup()
            self.mind_loop_task = asyncio.create_task(mind_loop.start())
            
            loop = asyncio.get_running_loop()
            STOP_WORDS = ["stop", "shut up", "be quiet", "cancel", "hold on", "never mind"]
            
            logger.info("J.A.R.V.I.S. is now listening...")
            
            while True:
                if not self.listening_announced:
                    print("\n[SYSTEM] Listening...")
                    self.listening_announced = True

                text, audio_path = await loop.run_in_executor(None, self.interface.listen)
                
                if not text:
                    continue

                text_lower = text.lower().strip()
                self.listening_announced = False
                
                if any(sw in text_lower for sw in STOP_WORDS):
                    if self.current_cmd_task and not self.current_cmd_task.done():
                        logger.info("GLOBAL STOP TRIGGERED.")
                        self.current_cmd_task.cancel()
                        speaker.stop() 
                        from skills.youtube_skill import stop_music
                        stop_music()
                        await speaker.speak("Understood. I am standing by.")
                        continue

                current_time = time.time()
                is_in_conversation = (current_time - self.last_wake_time) < self.CONVERSATION_TIMEOUT
                is_wake = self._is_wake_text(text_lower)

                if is_wake or is_in_conversation:
                    self.last_wake_time = current_time
                    logger.info(f"Processing Raw: {text_lower}")
                    
                    # 1. Refine the prompt (Neural Guard Pass)
                    refined_data = await refiner.refine(text_lower)
                    refined_text = refined_data["refined_text"]
                    intent_hint = refined_data["intent"]

                    if self.current_cmd_task and not self.current_cmd_task.done():
                        self.current_cmd_task.cancel()
                        speaker.stop()

                    self.current_cmd_task = asyncio.create_task(
                        self.router.process_command(refined_text, audio_path=audio_path)
                    )
                    # We do NOT await here, so J.A.R.V.I.S. can listen while speaking.
                    # The next iteration of the loop will handle interruptions via self.current_cmd_task.cancel()

        except asyncio.CancelledError:
            logger.info("Main loop cancelled.")
        finally:
            self._release_lock()
            mind_loop.stop()
            if self.mind_loop_task is not None:
                self.mind_loop_task.cancel()
            if self.current_cmd_task is not None:
                self.current_cmd_task.cancel()

    def _acquire_lock(self) -> bool:
        """Prevent multiple instances from running simultaneously."""
        lock_file = SystemConfig.LOCK_FILE
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        if lock_file.exists():
            try:
                with open(lock_file, "r") as f:
                    old_pid = int(f.read().strip())
                
                # Check if the old process is still alive
                import psutil
                if psutil.pid_exists(old_pid):
                    logger.error(f"FATAL: J.A.R.V.I.S. is already running (PID {old_pid}). Shutdown that instance first.")
                    print(f"\n[ERROR] J.A.R.V.I.S. is already active in another terminal (PID {old_pid}).")
                    return False
            except Exception:
                # Stale lock or corrupted file, ignore
                pass

        try:
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))
            logger.info(f"PID lock acquired: {os.getpid()}")
            return True
        except Exception as e:
            logger.error(f"Failed to create lock file: {e}")
            return False

    def _release_lock(self):
        """Remove the lock file on exit."""
        try:
            if SystemConfig.LOCK_FILE.exists():
                SystemConfig.LOCK_FILE.unlink()
                logger.info("PID lock released.")
        except Exception as e:
            logger.warning(f"Failed to release lock file: {e}")


if __name__ == "__main__":
    from core.config import SystemConfig
    jarvis = JarvisAsyncCore()
    try:
        asyncio.run(jarvis.run())
    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user.")
    except Exception as e:
        logger.exception(f"Unhandled exception in main: {e}")
    finally:
        try:
            session_data = jarvis.session.end()
            logger.info(
                f"Shutdown complete. Session: {session_data['duration_minutes']}min, "
                f"{session_data['commands_count']} commands."
            )
        except Exception:
            pass
