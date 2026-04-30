import logging
import json
import os
from skills.gemini_skill import gemini_core

logger = logging.getLogger("jarvis.refiner")

class PromptRefiner:
    """
    Neural Pre-processor using Gemini 1.5 Flash.
    Cleans noisy transcriptions, identifies intent, and formats for the Main Brain.
    """
    
    SYSTEM_INSTRUCTION = """
    You are the Input Refinement Unit for J.A.R.V.I.S.
    Your task is to take noisy voice transcriptions and convert them into clean, structured commands.
    
    RULES:
    1. Remove filler words and acoustic hallucinations (e.g., "K.A.R.I.V.I.S" -> "J.A.R.V.I.S").
    2. Correct misheard technical terms based on the context of a coding assistant.
    3. Identify if the user is asking for a SYSTEM action (local skill) or a KNOWLEDGE/COGNITIVE task (LLM Brain).
    4. Return ONLY a JSON object.
    
    JSON FORMAT:
    {
        "refined_text": "The cleaned command",
        "intent": "SYSTEM|KNOWLEDGE|CODE",
        "confidence": 0.0-1.0
    }
    """

    @staticmethod
    async def refine(raw_text: str) -> dict:
        """
        Scrub raw transcription and return structured intent.
        """
        if not raw_text or len(raw_text.strip()) < 3:
            return {"refined_text": raw_text, "intent": "SYSTEM", "confidence": 1.0}

        try:
            # We bypass the standard gemini_core.ask to use a custom system prompt
            if not gemini_core.model:
                return {"refined_text": raw_text, "intent": "KNOWLEDGE", "confidence": 0.5}

            prompt = f"{PromptRefiner.SYSTEM_INSTRUCTION}\n\nUser Input: \"{raw_text}\"\n\nJSON Output:"
            
            # Use generate_content_async directly for specialized instructions
            response = await gemini_core.model.generate_content_async(prompt)
            
            # Clean JSON response (sometimes Gemini adds ```json ... ```)
            resp_text = response.text.strip()
            if "```" in resp_text:
                resp_text = resp_text.split("```")[1]
                if resp_text.startswith("json"):
                    resp_text = resp_text[4:].strip()
            
            data = json.loads(resp_text)
            logger.info(f"Refined Intent: {data['intent']} | Text: {data['refined_text']}")
            return data
            
        except Exception as e:
            logger.warning(f"Refinement failed: {e}. Falling back to raw text.")
            return {"refined_text": raw_text, "intent": "KNOWLEDGE", "confidence": 0.5}

# Singleton
refiner = PromptRefiner()
