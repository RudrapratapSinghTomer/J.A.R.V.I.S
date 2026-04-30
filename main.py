import asyncio
import sys
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# CRITICAL: Set tiktoken cache dir BEFORE any cognee/litellm import.
# Without this, tiktoken tries to download ~1.7MB from OpenAI on first run,
# blocking the entire thread with a synchronous request.
_TIKTOKEN_CACHE = Path(__file__).parent / "data" / "tiktoken_cache"
_TIKTOKEN_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["TIKTOKEN_CACHE_DIR"] = str(_TIKTOKEN_CACHE)
from core.listener import JarvisInterface
from core.intent_router import IntentRouter
from core.session_manager import Session

# Force root logger to use our handlers even if other modules call basicConfig
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

stream_handler = logging.StreamHandler()
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(logs_dir / "jarvis.log", mode="a")
formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger("jarvis.main")


def _run_coro_sync(coro):
    """Run an async coroutine from sync code safely."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def startup_checks(interface: JarvisInterface, session: Session) -> bool:
    """
    Run all startup checks before entering the main loop.
    Order: Face-ID → Security → LLM Health → Memory → Context Load
    Returns True if Host Mode, False if Guest Mode.
    """
    print("\n" + "="*60)
    print("   J.A.R.V.I.S — Local AI Assistant")
    print("   Zero Cloud · Zero Billing · Security Always-On")
    print("="*60 + "\n")

    # 0. SILENT FACE-ID SCAN — Runs before any greeting
    host_name = os.getenv("JARVIS_HOST_NAME", "Sir")
    host_mode = False
    logger.info("Performing silent Face-ID scan...")
    try:
        from core.face_module import FaceModule
        fm = FaceModule()
        if fm.initialize() and fm.list_enrolled():
            result = fm.verify(tolerance=0.5)
            recognized_name = result.get("name", "unknown")
            if recognized_name not in ("unknown", "no_face", "no_encoding", "error"):
                host_mode = True
                session.host_mode = True
                session.recognized_user = recognized_name
                logger.info(f"Face-ID: HOST verified as '{recognized_name}'")
            else:
                session.host_mode = False
                session.recognized_user = "guest"
                logger.info(f"Face-ID: GUEST mode — face result was '{recognized_name}'")
        else:
            # No faces enrolled yet — default to host mode so JARVIS is not crippled
            logger.warning("Face-ID: No enrolled faces found. Defaulting to Host mode. Run scripts/enroll_face.py to set up.")
            host_mode = True
            session.host_mode = True
            session.recognized_user = "unenrolled"
    except Exception as e:
        logger.warning(f"Face-ID scan failed (non-fatal, defaulting to Guest): {e}")
        host_mode = False
        session.host_mode = False
        session.recognized_user = "error"

    # 1. Security check — ALWAYS FIRST (personality.md mandate)
    logger.info("Running startup security check...")
    try:
        # Add scripts dir to path for import
        sys.path.insert(0, str(Path(__file__).parent))
        from scripts.security_monitor import check_security
        is_secure = check_security(speak_func=interface.speak)
        session.security_status = "clean" if is_secure else "warnings_found"
    except ImportError:
        logger.info("Security monitor not yet installed. Skipping.")
        session.security_status = "not_available"
    except Exception as e:
        logger.warning(f"Security check error (non-fatal): {e}")

    # 2. LLM health check
    logger.info("Checking local LLM status...")
    try:
        from core.llm_client import brain
        health = _run_coro_sync(brain.health_check())
        if health["ok"]:
            main_core = health.get("main", "claw")
            core_health = health.get(main_core, {})
            if core_health.get("ok"):
                model_name = core_health.get("model") or getattr(brain, "model", "unknown")
                logger.info(f"Main Brain ({main_core}) online using {model_name}")
                session.llm_model = model_name
            else:
                logger.warning(f"Main core {main_core} is reachable but unhealthy: {core_health.get('error')}")
                interface.speak(
                    f"Warning: main core {main_core} is experiencing issues. "
                    "Please check logs for details."
                )
        else:
            logger.error(
                "All LLM cores appear offline. "
                f"Claw={health.get('claw', {}).get('error')}, "
                f"Ollama={health.get('ollama', {}).get('error')}"
            )
            interface.speak(
                "Warning: Local neural cores are offline. "
                "Complex requests will not work until they are restored."
            )
    except Exception as e:
        logger.error(f"LLM check failed: {e}")

    # 3. Doctor Claw Engine check
    logger.info("Checking Doctor Claw engine status...")
    try:
        from core.claw_integration import claw
        if claw.is_available():
            logger.info("Doctor Claw engine: READY ✅")
            session.claw_available = True
        else:
            logger.info("Doctor Claw engine: Not built yet (compilation pending).")
            session.claw_available = False
    except Exception as e:
        logger.warning(f"Claw check error: {e}")
        session.claw_available = False

    # 3. Memory initialization — RE-ENABLED (Background Threaded)
    logger.info("Starting memory system in background...")
    
    def _run_memory_bg():
        """Dedicated thread for memory initialization to prevent any UI lag."""
        loop = None
        try:
            from memory.cognee_bridge import memory
            # Set up the loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _init():
                try:
                    logger.info("Memory: Initializing engine...")
                    await asyncio.wait_for(memory.initialize(), timeout=20.0)
                    logger.info("Memory: Loading context files...")
                    await asyncio.wait_for(memory.load_context(), timeout=60.0)
                    logger.info("Memory system fully online. Knowledge graph ready.")
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

    import threading
    threading.Thread(target=_run_memory_bg, daemon=True).start()

    return host_mode


def main():
    logger.info("Initializing J.A.R.V.I.S. Core System...")
    interface = JarvisInterface(use_google_fallback=True)
    session = Session()

    # Run all startup checks — returns host_mode boolean
    host_mode = startup_checks(interface, session)

    # Pass host_mode into router
    router = IntentRouter(interface, host_mode=host_mode)

    # Greet based on identity
    host_name = os.getenv("JARVIS_HOST_NAME", "Sir")
    override_pw = os.getenv("JARVIS_OVERRIDE_PASSWORD", "")

    if host_mode:
        recognized = getattr(session, 'recognized_user', 'unenrolled')
        if recognized == 'unenrolled':
            interface.speak("System initialized. No host profile found. Running in unrestricted mode. I recommend running the enrollment script.")
        else:
            interface.speak(f"Welcome back, {host_name}. All systems are online. Full host access granted.")
    else:
        interface.speak("Hello. I am J.A.R.V.I.S. I am currently operating in guest mode with limited access.")

    # Initialize last_wake_time to "never" (current time - 1 hour)
    last_wake_time = time.time() - 3600
    CONVERSATION_TIMEOUT = 30 # Seconds to stay "awake" after a wake word

    try:
        while True:
            text = interface.listen()
            if not text:
                continue

            current_time = time.time()
            text_lower = text.lower()
            
            # Check for wake word using FUZZY MATCHING
            from thefuzz import fuzz
            WAKE_WORD = "jarvis"
            COMMON_MISSES = ["jervis", "travis", "service", "harvest", "chavez", "garbage", "arvis", "darvis"]
            
            words = text_lower.split()
            max_score = 0
            best_match = ""
            for word in words:
                if word == WAKE_WORD or word in COMMON_MISSES:
                    max_score = 100
                    best_match = word
                    break
                score = fuzz.ratio(word, WAKE_WORD)
                if score > max_score:
                    max_score = score
                    best_match = word
            
            # If we hear "Jarvis" OR we are in an active conversation (last 30s)
            is_active = (current_time - last_wake_time) < CONVERSATION_TIMEOUT
            
            if max_score >= 55:
                # WAKE WORD DETECTED
                last_wake_time = current_time
                command = text_lower.replace(best_match, "", 1).strip()
                logging.info(f">>> WAKE WORD DETECTED (Similarity: {max_score}%, Word: '{best_match}')")

                # Check for override passcode (Failsafe)
                if override_pw and command.startswith("override ") and override_pw in command:
                    router.host_mode = True
                    session.host_mode = True
                    host_name = os.getenv("JARVIS_HOST_NAME", "Sir")
                    interface.speak(f"Override accepted. Welcome back, {host_name}. Full host access restored.")
                    logging.info(">>> HOST MODE: Restored via override passcode.")
                elif command:
                    _run_coro_sync(router.process_command(command))
                    session.log_command(command, route="processed")
                else:
                    if router.host_mode:
                        interface.speak(f"Yes, {os.getenv('JARVIS_HOST_NAME', 'Sir')}? How can I help?")
                    else:
                        interface.speak("Yes? How may I assist you?")
            
            elif is_active:
                # CONTINUOUS CONVERSATION (No wake word needed)
                logging.info(f">>> ACTIVE CONVERSATION: '{text}'")
                _run_coro_sync(router.process_command(text_lower))
                session.log_command(text_lower, route="continuous")
                # Refresh the timer so the conversation stays alive
                last_wake_time = current_time
            
            else:
                # No wake word and not in a conversation
                logging.info(f">>> Listening... (Say 'Jarvis' to wake me up. Last heard: {round(current_time - last_wake_time)}s ago)")
                # Uncomment the line below to respond to ALL speech (no wake word needed):
                # router.process_command(text)
    except KeyboardInterrupt:
        session_data = session.end()
        interface.speak("Shutting down systems. Goodbye, Sir.")
        logger.info(
            f"Shutdown complete. Session: {session_data['duration_minutes']}min, "
            f"{session_data['commands_count']} commands."
        )
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
