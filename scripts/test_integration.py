import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.claw_client import claw_brain

async def test_brain():
    print("\n[TEST] Testing J.A.R.V.I.S Brain Integration")
    print("========================================")
    
    # 1. Health check
    print(f"[*] Checking health of primary core...")
    health = await claw_brain.health_check()
    
    if health["ok"]:
        print(f"[+] Primary core ONLINE (Version: {health.get('version')})")
        print(f"[+] Target Model: {health.get('model')}")
        print(f"[+] Base URL: {health.get('base_url')}")
        
        # 2. Execution test
        print(f"[*] Sending test prompt: 'say hello world briefly'")
        response = await claw_brain.execute("say hello world briefly")
        print(f"\n[RESPONSE] >>> {response}\n")
    else:
        print(f"[!] Primary core OFFLINE: {health.get('error')}")
        print("\nPossible fixes:")
        print("1. Ensure Ollama is running (`ollama serve`)")
        print("2. Ensure gemma4:latest is pulled (`ollama pull gemma4:latest`)")
        print("3. Check CLAW_PATH in .env")

if __name__ == "__main__":
    asyncio.run(test_brain())
