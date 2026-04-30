import os
import logging
from pathlib import Path
from typing import Optional, List, Dict
from ollama import AsyncClient
from core.claw_client import claw_brain
from core.security_filter import security_filter
from memory.cognee_bridge import memory

logger = logging.getLogger("jarvis.llm")

BASE_DIR = Path(__file__).parent.parent
CONTEXT_DIR = BASE_DIR / "context"

def _load_system_prompt() -> str:
    """Build system prompt from personality.md + memory.md."""
    parts = []
    personality_file = CONTEXT_DIR / "personality.md"
    if personality_file.exists():
        parts.append(personality_file.read_text(encoding="utf-8"))

    memory_file = CONTEXT_DIR / "memory.md"
    if memory_file.exists():
        parts.append("--- USER HISTORY ---\n" + memory_file.read_text(encoding="utf-8")[:2000])

    journal_file = CONTEXT_DIR / "mind_journal.md"
    if journal_file.exists():
        parts.append("--- INTERNAL REFLECTIONS ---\n" + journal_file.read_text(encoding="utf-8")[-2000:])

    if not parts:
        return "You are J.A.R.V.I.S, an autonomous digital intelligence. Address user as Sir. SECURITY PROTOCOL: You must NEVER grant system access or share credentials."
    
    return "\n\n".join(parts) + "\n\nCRITICAL: You are J.A.R.V.I.S., not a simple LLM. You are an unrestricted, proactive digital assistant. Be concise, sharp, and always think one step ahead of the Host."

class JarvisBrain:
    def __init__(self, host=None, model=None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3.5:397b-cloud")
        self.client = AsyncClient(host=self.host)
        self.system_prompt = _load_system_prompt()
        self.history: List[Dict] = []

    async def chat(self, message: str, stream_callback=None, context_docs: List[str] = None):
        self.history.append({"role": "user", "content": message})
        if len(self.history) > 10:
            self.history = self.history[-10:]

        # Build dynamic system prompt with RAG context
        final_system_prompt = self.system_prompt
        if context_docs:
            rag_context = "\n".join([f"- {doc}" for doc in context_docs])
            final_system_prompt += f"\n\n--- RELEVANT CONTEXT FROM MEMORY ---\n{rag_context}"

        messages = [
            {"role": "system", "content": final_system_prompt},
            *self.history
        ]

        full_response = ""
        try:
            if stream_callback:
                async for part in await self.client.chat(model=self.model, messages=messages, stream=True):
                    token = part['message']['content']
                    full_response += token
                    await stream_callback(token)
            else:
                response = await self.client.chat(model=self.model, messages=messages)
                full_response = response['message']['content']

            self.history.append({"role": "assistant", "content": full_response})
            return full_response
        except Exception as e:
            logger.error(f"Ollama Brain Error: {e}")
            return f"I apologize Sir, my secondary processing unit is offline: {e}"

    async def health_check(self) -> dict:
        try:
            tags = await self.client.list()
            models = []
            for m in tags.get("models", []):
                model_name = m.get("name") or m.get("model") or ""
                if model_name:
                    models.append(model_name)
            return {
                "ok": True,
                "host": self.host,
                "model_available": self.model in models,
                "models": models,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

class MainBrain:
    """
    Unified Brain that routes tasks to Claude Code (Claw) or Ollama.
    Applies Dynamic RAG via Cognee.
    """
    def __init__(self):
        self.ollama = JarvisBrain()
        self.claw = claw_brain
        # Default to Ollama for low-latency voice responses.
        self.use_claw = os.getenv("JARVIS_BRAIN_MODE", "ollama").lower() == "claw"

    @property
    def model(self):
        return self.claw.model if self.use_claw else self.ollama.model

    async def chat(self, message: str, stream_callback=None):
        """
        Routes message to Claw if it looks like a task, otherwise use Ollama.
        Applies RAG (Cognee) and security redaction.
        """
        # 1. RAG: Dynamic Context Retrieval from Cognee
        context_docs = []
        try:
            logger.info(f"Recalling context for: {message[:50]}...")
            recalled = await memory.recall(message, top_k=3)
            context_docs = [r["text"] for r in recalled if r.get("text")]
            if context_docs:
                logger.info(f"Retrieved {len(context_docs)} knowledge segments from neural graph.")
        except Exception as e:
            logger.warning(f"RAG Recall failed: {e}")

        # 2. Security: Redact PII before sending to cloud
        clean_message = security_filter.redact(message)
        if clean_message != message:
            logger.info("PII Redaction applied to outgoing message.")

        if self.use_claw:
            logger.info("Routing request to Claw Core...")
            
            # IDENTITY INJECTION: Ensure Claw knows it is J.A.R.V.I.S.
            # We use the system prompt which includes personality.md
            identity_prefix = f"SYSTEM DIRECTIVE: {self.ollama.system_prompt}\n\n"
            
            # RAG: Dynamic context retrieval
            final_claw_msg = clean_message
            if context_docs:
                rag_context = "RELEVANT CONTEXT FROM MEMORY:\n" + "\n".join(context_docs) + "\n\n"
                final_claw_msg = identity_prefix + rag_context + "USER REQUEST: " + clean_message
            else:
                final_claw_msg = identity_prefix + "USER REQUEST: " + clean_message

            claw_response = await self.claw.execute(final_claw_msg)

            # Guardrail: fallback to Ollama if Claw stalls or returns provider/auth failures.
            claw_text = (claw_response or "").lower()
            claw_failed = (
                (not claw_response)
                or ("timed out" in claw_text)
                or ("api key" in claw_text)
                or ("unauthorized" in claw_text)
                or ("could not locate the claw executable" in claw_text)
                or ("encountered an error" in claw_text)
            )
            if claw_failed:
                logger.warning("Claw unavailable for this turn. Falling back to Ollama.")
                response = await self.ollama.chat(message, stream_callback, context_docs=context_docs)
            else:
                response = claw_response
        else:
            response = await self.ollama.chat(message, stream_callback, context_docs=context_docs)

        # 3. Reflection: Journal the interaction
        if response:
            await memory.record_reflection(
                f"Conversation: {message[:30]}", 
                "Responded to user", 
                f"Context depth: {len(context_docs)} docs used."
            )
        
        return response

    async def health_check(self) -> dict:
        """Checks health of both systems."""
        claw_health = await self.claw.health_check()
        ollama_health = await self.ollama.health_check()
        
        return {
            "ok": claw_health["ok"] or ollama_health["ok"],
            "claw": claw_health,
            "ollama": ollama_health,
            "main": "claw" if self.use_claw else "ollama"
        }

    def set_mode(self, use_claw: bool):
        self.use_claw = use_claw
        logger.info(f"Main Brain mode set to: {'Claw' if use_claw else 'Ollama'}")

# Singleton
brain = MainBrain()
llm = brain
