import asyncio
import datetime
import logging
import re
import platform
from core.listener import JarvisInterface
from core.llm_client import brain
from core.speech_output import speaker
from core.semantic_router import SemanticRouter

from core.security_filter import security_filter
from core.voice_authenticator import voice_auth
from memory.cognee_bridge import memory

logger = logging.getLogger("jarvis.router")

class IntentRouter:
    """
    Asynchronous Intent Router.
    Routes user speech to either specific local tools or the LLM brain.
    Now uses Semantic Routing + Role-Based Access Control (Host vs Guest).
    """
    # Intents blocked in Guest mode
    HOST_ONLY_INTENTS = {"TERMINAL_COMMAND", "SHUTDOWN", "SYSTEM_STATUS"}
    
    # Intents requiring Human-in-the-Loop approval / Biometric Verification
    SENSITIVE_INTENTS = {"TERMINAL_COMMAND", "SHUTDOWN", "FILE_MODIFICATION", "PERMISSION_CHANGE", "ENROLL_VOICE", "CODE_MODIFICATION", "DEBUG_SYSTEM"}

    def __init__(self, interface: JarvisInterface, host_mode: bool = True):
        self.interface = interface
        self.brain = brain
        self.semantic_router = SemanticRouter()
        self._initialized = False
        self.host_mode = host_mode  # True = full access, False = read-only guest

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.semantic_router.initialize()
            self._initialized = True

    async def process_command(self, text: str, audio_path: str = None):
        """
        Main entry point for command processing.
        Routes to fast-path tools, semantic skills, or the LLM brain.
        """
        if not text:
            return

        text_clean = text.lower().strip()
        await self._ensure_initialized()
        
        # 1. Ultra-Fast Path: Literal/Simple Regex (Zero latency)
        if any(w in text_clean for w in ["time", "what time"]):
            now = datetime.datetime.now()
            await speaker.speak(f"The current time is {now.strftime('%I:%M %p')}, Sir.")
            return

        if any(w in text_clean for w in ["date", "what day"]):
            now = datetime.datetime.now()
            await speaker.speak(f"Today is {now.strftime('%A, %B %d, %Y')}, Sir.")
            return

        if any(w in text_clean for w in ["stop music", "shut up jarvis", "stop playing", "stop the song"]):
            from skills.youtube_skill import stop_music
            await speaker.speak("Stopping music playback, Sir.")
            stop_music()
            return

        # [FAST-PATH] Engineering & Debugging & Voice Enrollment
        if any(w in text_clean for w in ["debug", "fix code", "modify code", "edit code", "help me debug"]):
            from skills.engineer_skill import engineer_skill
            await speaker.speak("Initiating engineering diagnostic sequence, Sir. Accessing internal systems.")
            await engineer_skill.execute(text_clean)
            await memory.record_reflection("Engineering Diagnostic", "Initiated code analysis/fix", f"User requested debugging for: {text_clean}")
            return
            
        if any(w in text_clean for w in ["enroll my voice", "start voice enrollment", "enroll voice", "and roll", "unroll", "enroll"]):
            from skills.voice_enroll_skill import enroll_voice_routine
            await enroll_voice_routine(self.interface)
            return

        # 2. Semantic Routing (The Intelligence Layer)
        intent, score = await self.semantic_router.route(text_clean)
        
        # [OPTIMIZATION] Neural Command Cleaning
        # Only clean if confidence is genuinely low
        if score < 0.60 and len(text_clean.split()) > 3:
            logger.info(f"Low confidence ({score:.2f}). Triggering Neural Command Cleaner...")
            cleaned = await self._neural_clean(text)
            if cleaned:
                logger.info(f"Cleaned command: '{text_clean}' -> '{cleaned}'")
                text_clean = cleaned.lower()
                intent, score = await self.semantic_router.route(text_clean)

        # Role-Based Access Control: block host-only intents for guests
        if not self.host_mode and intent in self.HOST_ONLY_INTENTS:
            logger.warning(f"Guest attempted host-only intent: {intent}")
            await speaker.speak("I apologize, but that action requires Host authorization. Please ensure the host is present.")
            return

        # 3. Neural Voice Authentication Gatekeeper
        if intent in self.SENSITIVE_INTENTS:
            logger.info(f"Sensitive intent detected: {intent}. Initiating biometric check...")
            
            # [NEW] Chain-of-Thought (CoT) Verification
            # Before proceeding, we check the Mind Journal for any relevant security reflections.
            reflections = await memory.recall(f"security protocol for {intent}", top_k=2)
            if reflections:
                logger.info("Retrieved relevant security reflections for CoT verification.")
                # We don't block here yet, but we log the alignment.
                # In the future, this will be an automated 'Reflection Gate'.

            # [SPECIAL CASE] First-time enrollment
            if intent == "ENROLL_VOICE" and not voice_auth.has_signature():
                logger.info("No voice signature found. Allowing initial enrollment...")
                # Proceed to execution without verification
            elif audio_path:
                if not voice_auth.verify(audio_path):
                    logger.warning("VOICE VERIFICATION FAILED. Unauthorized speaker for sensitive command.")
                    await speaker.speak("Voice identity not verified. Sensitive command execution aborted.")
                    return
                else:
                    logger.info("Voice identity verified. Proceeding with sensitive command.")
            else:
                logger.warning("No biometric data available for sensitive command. Bypassing (unsafe).")
        
        if intent == "GET_WEATHER":
            # Extract city if mentioned
            city = "Mumbai" # Default
            match = re.search(r"in ([\w\s]+)", text_clean)
            if match:
                city = match.group(1).strip()
            
            from skills.weather_news_skill import weather_news
            report = weather_news.get_weather(city)
            await speaker.speak(report)
            return

        elif intent == "PLAY_YOUTUBE":
            song_query = text_clean.replace("youtube", "").replace("play", "").strip()
            if not song_query:
                await speaker.speak("What should I play for you on YouTube, Sir?")
                return
            from skills.youtube_skill import play_video
            await speaker.speak(f"Searching YouTube for {song_query}, Sir.")
            # Run in executor because play_video can be slow (network search)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, play_video, song_query)
            return

        elif intent == "ENROLL_VOICE":
            from skills.voice_enroll_skill import enroll_voice_routine
            await enroll_voice_routine(self.interface)
            return
            
        elif intent == "IDENTIFY_ME":
            if not audio_path:
                await speaker.speak("I heard your request, Sir, but I don't have enough audio data to verify your identity.")
                return
            
            await speaker.speak("Processing biometric signature. One moment.")
            if voice_auth.verify(audio_path):
                await speaker.speak(f"Biometric signature confirmed. You are the Host, Rudrapratap. Access granted.")
                self.host_mode = True
            else:
                await speaker.speak("Your vocal signature is not recognized in my database. You are currently operating in Guest Mode.")
                self.host_mode = False
            return

        elif intent == "GET_NEWS":
            from skills.weather_news_skill import weather_news
            report = weather_news.get_news()
            await speaker.speak(report)
            return

        elif intent == "WEB_SEARCH":
            search_query = text_clean.replace("search", "").replace("google", "").replace("for", "").strip()
            if search_query:
                from skills.gemini_skill import gemini_core
                await speaker.speak(f"Accessing satellite data for {search_query}...")
                response = await gemini_core.ask(search_query)
                await speaker.speak(response)
                return

        elif intent == "SYSTEM_STATUS":
            health = await self.brain.health_check()
            status = "All systems are operational." if health["ok"] else "Some systems are offline, Sir."
            await speaker.speak(f"{status} Primary core is {health['main']}. Neural processing units are at peak efficiency.")
            return

        elif intent == "TERMINAL_COMMAND":
            await speaker.speak("Sir, you are requesting terminal access. This is a high-level operation.")
            if await self._request_approval("Authorize terminal access?"):
                from core.face_module import face_recognizer
                await speaker.speak("Initiating biometric scan for final verification.")
                verified = await face_recognizer.guard_mode()
                
                if verified:
                    await speaker.speak("Identity confirmed. Terminal is ready for your instructions.")
                else:
                    await speaker.speak("Verification failed. Terminal access denied.")
            else:
                await speaker.speak("Operation cancelled. Safety protocol maintained.")
            return

        elif intent == "SHUTDOWN":
            if await self._request_approval("Confirm system deactivation?"):
                await speaker.speak("Deactivating systems. Goodbye, Sir.")
                exit(0)
            else:
                await speaker.speak("Shutdown aborted.")
            return

        elif intent in ["CODE_MODIFICATION", "DEBUG_SYSTEM"]:
            # These are high-level engineering tasks
            await speaker.speak(f"Sir, you are requesting a {intent.lower().replace('_', ' ')}. This will modify my internal systems.")
            if await self._request_approval(f"Authorize {intent.lower().replace('_', ' ')}?"):
                from skills.engineer_skill import engineer_skill
                await engineer_skill.execute(text_clean)
                await memory.record_reflection(f"Code Modification: {intent}", "Executed system change", f"Input: {text_clean}")
            else:
                await speaker.speak("Engineering sequence aborted, Sir.")
            return

        # 3. Slow-Path: General Conversation (Ollama/Claw)
        now = datetime.datetime.now()
        context = {
            "current_time": now.strftime("%I:%M %p"),
            "current_date": now.strftime("%B %d, %Y"),
            "user_name": "Rudrapratap",
            "platform": f"{platform.system()} {platform.release()}",
            "system_load": "optimal"
        }
        
        enhanced_query = f"[Context: {context}] {text}"
        # [SECURITY] Check for sensitive keywords in general conversation
        if security_filter.is_sensitive_command(text):
            logger.warning(f"Sensitive command detected in chat: {text}")
            if not await self._request_approval(f"Authorization required for sensitive request: {text_clean}"):
                await speaker.speak("I am sorry Sir, but I cannot fulfill that request without your explicit authorization.")
                return

        try:
            timeout = 120.0 if self.brain.use_claw else 90.0
            response = await asyncio.wait_for(self.brain.chat(enhanced_query), timeout=timeout)
            
            if response:
                clean_response = self._cleanup_for_speech(response)
                await speaker.speak(clean_response)
            else:
                await speaker.speak("I processed your request, Sir, but I'm afraid I don't have a definitive answer at the moment.")
                
        except asyncio.TimeoutError:
            await speaker.speak("I'm sorry Sir, my neural core is taking longer than expected. Please try again.")
        except Exception as e:
            logger.error(f"Router processing failed: {e}")
            await speaker.speak("Sir, I am experiencing a temporary disconnect from my processing core.")

    async def _request_approval(self, prompt: str) -> bool:
        """Request verbal approval for sensitive actions."""
        await speaker.speak(f"{prompt}. Say 'Authorize' or 'Proceed' to confirm.")
        loop = asyncio.get_running_loop()
        
        # Wrapped in executor to avoid blocking the event loop
        text_result = await loop.run_in_executor(None, self.interface.listen)
        
        if text_result:
            response = text_result[0] if isinstance(text_result, tuple) else text_result
            if response and any(w in response.lower() for w in ["authorize", "proceed", "yes", "do it"]):
                logger.info("User AUTHORIZED sensitive action.")
                return True
        
        logger.warning("User DENIED or TIMED OUT sensitive action.")
        return False

    async def _neural_clean(self, noisy_text: str) -> str:
        """Use local LLM to strip noise from voice commands."""
        prompt = (
            "You are the Neural Command Cleaner for J.A.R.V.I.S. "
            "Your task is to take a noisy voice-to-text transcript and return ONLY a clean, "
            "direct system command. Strip away filler words, repeated wake words, or honorifics.\n\n"
            "Examples:\n"
            "'Jarvis Sir J.A.R.V.I.S., sunflower on YouTube.' -> 'play sunflower on youtube'\n"
            "'Hey Jarvis tell me what is the time right now' -> 'what is the time'\n"
            "'Jarvis play some music from metro boomin' -> 'play metro boomin'\n\n"
            f"Noisy Text: '{noisy_text}'\n"
            "Clean Command:"
        )
        try:
            # Use a faster, shorter response for cleaning
            response = await self.brain.chat(prompt)
            if response:
                # Clean up any quotes or extra text the LLM might add
                cleaned = response.strip().lower().replace("'", "").replace("\"", "")
                return cleaned
        except Exception as e:
            logger.error(f"Neural clean failed: {e}")
        return None

    def _cleanup_for_speech(self, text: str) -> str:
        """Remove markdown and code blocks from text for better TTS."""
        text = re.sub(r"```.*?```", "[code block omitted]", text, flags=re.DOTALL)
        text = text.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        return text.strip()
