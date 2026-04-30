import os
import logging
import google.generativeai as genai

logger = logging.getLogger("jarvis.skills.gemini")

class GeminiSkill:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = None
        if self.api_key and "your_" not in self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini Flash core: READY")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")

    async def ask(self, prompt: str) -> str:
        """Call Gemini Flash for high-speed web/complex queries."""
        if not self.model:
            return "Sir, my Gemini core is not configured. Please provide a valid Google API key."

        try:
            # We add a small system instruction for consistency
            full_prompt = f"You are J.A.R.V.I.S., a helpful AI assistant. Answer concisely for voice output. Question: {prompt}"
            response = await self.model.generate_content_async(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return f"I encountered an error while reaching my satellite processing core, Sir: {e}"

# Singleton
gemini_core = GeminiSkill()
