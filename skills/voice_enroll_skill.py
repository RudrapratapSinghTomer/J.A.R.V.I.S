import asyncio
import logging
import os
from pathlib import Path
from core.speech_output import speaker
from core.voice_authenticator import voice_auth

logger = logging.getLogger("jarvis.skills.voice_enroll")

async def enroll_voice_routine(interface):
    """
    Interactive routine to enroll the host's voice.
    Asks the user to speak 3 phrases for neural signature extraction.
    """
    await speaker.speak("Initiating neural voice enrollment. I will need three audio samples to create your unique vocal signature.")
    
    # Calibration step
    await speaker.speak("First, let's calibrate. Please say anything for two seconds so I can check your audio levels.")
    loop = asyncio.get_running_loop()
    cal_result = await loop.run_in_executor(None, interface.listen)
    if isinstance(cal_result, tuple):
        _, cal_path = cal_result
        if cal_path and os.path.exists(cal_path):
            size = os.path.getsize(cal_path)
            if size < 2000:
                await speaker.speak("I am having trouble hearing you. Please check your microphone and try again.")
                return False
            logger.info(f"Calibration successful: {size} bytes.")
    
    await speaker.speak("Calibration successful. Proceeding with samples.")
    
    samples = []
    prompts = [
        "Please say: J.A.R.V.I.S., authorize host access.",
        "Please say: My voice is my passport, verify me.",
        "Please say: The future belongs to those who believe in the beauty of their dreams."
    ]
    
    temp_dir = Path("data/temp_enrollment")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        for i, prompt in enumerate(prompts):
            await speaker.speak(f"Sample {i+1} of {len(prompts)}. {prompt}")
            logger.info(f"Enrolling sample {i+1}...")
            
            # Wrapped in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, interface.listen)
            
            # Unpack if it returns (text, audio_path)
            if isinstance(result, tuple):
                text, audio_path = result
            else:
                text, audio_path = result, None # Fallback if listener behavior varies
            
            if audio_path and os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                if file_size > 2000: # Rough check for short audio
                    samples.append(audio_path)
                    logger.info(f"Captured sample {i+1}: {audio_path} ({file_size} bytes)")
                    await speaker.speak("Sample captured.")
                else:
                    logger.warning(f"Sample {i+1} was too quiet or short ({file_size} bytes).")
                    await speaker.speak("That sample was a bit too short or quiet. Let's try again.")
                    return False
            else:
                await speaker.speak("I couldn't hear you clearly. Please try again.")
                return False

        await speaker.speak("Processing neural signature. This may take a moment.")
        
        # Run CPU-intensive enrollment in executor
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, voice_auth.enroll_host, samples)
        
        if success:
            await speaker.speak("Enrollment complete. Now, let's verify your identity. Please say your name.")
            
            # Immediate Self-Verification Test
            test_result = await loop.run_in_executor(None, interface.listen)
            if isinstance(test_result, tuple):
                test_text, test_path = test_result
                if test_path and voice_auth.verify(test_path, threshold=0.40):
                    await speaker.speak("Biometric match confirmed. Your identity is now protected, Sir.")
                    logger.info("Enrollment self-verification passed.")
                    return True
                else:
                    await speaker.speak("Verification failed. The signature might be unstable. We should try again later.")
                    logger.warning("Enrollment self-verification failed.")
                    return False
            return True
        else:
            await speaker.speak("Enrollment failed during neural processing. I may need clearer audio samples with less background noise.")
            return False
            
    finally:
        # Cleanup temp files is handled by listener or we can do it here if we copied them
        pass

class VoiceEnrollSkill:
    def __init__(self, interface):
        self.interface = interface

    async def execute(self):
        return await enroll_voice_routine(self.interface)
