import asyncio
import logging
import os
from pathlib import Path
from core.speech_output import speaker
from core.llm_client import brain

logger = logging.getLogger("jarvis.skills.engineer")

class EngineerSkill:
    """
    The Self-Evolution Skill.
    Allows J.A.R.V.I.S. to modify its own source code or debug its systems
    using the high-privilege Claw brain.
    """
    def __init__(self, interface=None):
        self.interface = interface
        self.workspace_root = Path(__file__).parent.parent

    async def execute(self, request: str):
        """
        Executes a code modification or debugging task.
        """
        await speaker.speak(f"Sir, I am initiating a self-diagnostic and engineering sequence for: {request}")
        
        if not brain.use_claw:
            await speaker.speak("I'm sorry Sir, but my engineering core is currently offline. Please enable Claw mode.")
            return False

        # Enhance the request with engineering context
        engineer_prompt = (
            "You are the Core Engineering Unit of J.A.R.V.I.S.\n"
            "Your task is to execute the following technical request on your own codebase.\n"
            "You have full permission to READ, MODIFY, or CREATE files in the workspace.\n"
            "If the request is a bug report, debug it first. If it's a feature request, implement it.\n\n"
            f"User Request: '{request}'\n\n"
            "Instructions:\n"
            "1. Analyze the current state of the relevant files.\n"
            "2. Make the necessary changes to fulfill the request.\n"
            "3. Ensure the code remains functional and follows existing patterns.\n"
            "4. Provide a summary of your actions at the end."
        )

        try:
            logger.info(f"Dispatching engineering task to Claw: {request}")
            # We use claw's direct execution to allow it to use tools (read/write files)
            response = await brain.claw.execute(engineer_prompt)
            
            if response:
                logger.info("Engineering task completed.")
                # Truncate long responses for speech
                summary = response[:300] + "..." if len(response) > 300 else response
                await speaker.speak(f"Sequence complete. {summary}")
                return True
            else:
                await speaker.speak("The engineering sequence failed to return a result, Sir.")
                return False

        except Exception as e:
            logger.error(f"Engineering sequence failed: {e}")
            await speaker.speak(f"Sir, I encountered a critical error during the engineering sequence: {str(e)}")
            return False

# Singleton instance
engineer_skill = EngineerSkill()
