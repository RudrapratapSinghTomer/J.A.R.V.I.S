#!/usr/bin/env python3
"""
J.A.R.V.I.S Face Enrollment Script
=====================================
Run this ONCE to register your face as the Host.
It captures 5 photos from different angles for near-100% accuracy.

Usage:
    python scripts/enroll_face.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def main():
    print("\n" + "="*60)
    print("   J.A.R.V.I.S — Face Enrollment")
    print("   This will register you as the Host with full access.")
    print("="*60)

    # Check dependencies
    try:
        import face_recognition
        import cv2
        import numpy as np
    except ImportError as e:
        print(f"\n❌ Missing dependency: {e}")
        print("\nInstall with:")
        print("  pip install face_recognition opencv-python numpy")
        print("\nNote: face_recognition requires cmake + dlib.")
        print("  Windows: pip install cmake dlib face_recognition")
        sys.exit(1)

    from core.face_module import FaceModule
    fm = FaceModule()
    if not fm.initialize():
        print("❌ FaceModule failed to initialize. Check dependencies.")
        sys.exit(1)

    # Check if already enrolled
    enrolled = fm.list_enrolled()
    if enrolled:
        print(f"\n⚠️  Already enrolled: {', '.join(enrolled)}")
        choice = input("   Re-enroll to improve accuracy? (y/n): ").strip().lower()
        if choice != 'y':
            print("   Keeping existing enrollment. Exiting.")
            sys.exit(0)
        # Remove old enrollment for clean re-enroll
        for name in enrolled:
            fm.remove(name)
            print(f"   Removed old encoding for: {name}")

    print("\n📋 INSTRUCTIONS FOR BEST ACCURACY:")
    print("   • Make sure your face is well-lit (not backlit)")
    print("   • Look directly at the camera for the first 3 shots")
    print("   • Slightly turn left/right for shots 4 and 5")
    print("   • Remove sunglasses (regular glasses are fine)")
    print()

    name = input("   Enter your name (as you want JARVIS to call you): ").strip()
    if not name:
        name = "Rudra"

    print(f"\n📸 Starting 5-sample enrollment for '{name}'...")
    print("   JARVIS will greet you using this name on boot.\n")

    success = fm.enroll(name, num_samples=5)

    if success:
        print(f"\n✅ SUCCESS! '{name}' is now the J.A.R.V.I.S Host.")
        print("   Face data saved to: data/faces/encodings.json")
        print("\n   Next time you start JARVIS, he will recognize you")
        print("   automatically and boot in full Host Mode.\n")

        # Save the host name to .env so main.py knows who to greet
        env_path = ROOT / ".env"
        env_content = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
        if "JARVIS_HOST_NAME=" in env_content:
            import re
            env_content = re.sub(r"JARVIS_HOST_NAME=.*", f"JARVIS_HOST_NAME={name}", env_content)
        else:
            env_content += f"\n# Face ID Host\nJARVIS_HOST_NAME={name}\n"
        env_path.write_text(env_content, encoding="utf-8")
        print(f"   Host name '{name}' saved to .env")

        # Also set up the override password
        print("\n🔐 FAILSAFE SETUP:")
        print("   If JARVIS ever fails to recognize you (e.g. bad lighting),")
        print("   you can say 'override [password]' to force Host Mode.")
        override_pw = input("   Set your override password: ").strip()
        if override_pw:
            if "JARVIS_OVERRIDE_PASSWORD=" in env_content:
                env_content = re.sub(r"JARVIS_OVERRIDE_PASSWORD=.*", f"JARVIS_OVERRIDE_PASSWORD={override_pw}", env_content)
            else:
                env_content += f"JARVIS_OVERRIDE_PASSWORD={override_pw}\n"
            env_path.write_text(env_content, encoding="utf-8")
            print(f"   ✅ Override password set. Say 'override {override_pw}' to unlock Host Mode.")
        else:
            print("   Skipped. You can set this later in .env as JARVIS_OVERRIDE_PASSWORD=yourpassword")

    else:
        print("\n❌ Enrollment failed. Please check your webcam and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
