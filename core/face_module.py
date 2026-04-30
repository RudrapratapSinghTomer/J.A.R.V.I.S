#!/usr/bin/env python3
"""
J.A.R.V.I.S Face Recognition Module
======================================
Fully local face detection + recognition using dlib/face_recognition + OpenCV.
Zero cloud. All processing on CPU.

Capabilities:
1. ENROLL  — Register a face with a name (stores encoding locally)
2. VERIFY  — Check if the person in front of camera is known
3. DETECT  — Real-time face detection from webcam
4. GUARD   — Security mode: only allow recognized users

Data stored in: J.A.R.V.I.S/data/faces/
- encodings.json  — face encodings (128-d vectors per person)
- photos/         — reference photos (optional, for review)

Dependencies:
    pip install face_recognition opencv-python-headless numpy

Usage:
    from core.face_module import FaceModule
    fm = FaceModule()
    fm.enroll("Rudrapratap")           # Takes photo from webcam
    name = fm.verify()                  # Returns name or "unknown"
"""

import os
import json
import logging
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("jarvis.face")

BASE_DIR = Path(__file__).parent.parent
FACES_DIR = BASE_DIR / "data" / "faces"
PHOTOS_DIR = FACES_DIR / "photos"
ENCODINGS_FILE = FACES_DIR / "encodings.json"


class FaceModule:
    """
    Local face recognition for J.A.R.V.I.S.
    All processing runs on CPU using dlib's HOG detector.
    """

    def __init__(self):
        self._encodings: dict[str, list] = {}  # name -> list of 128-d encodings
        self._initialized = False
        FACES_DIR.mkdir(parents=True, exist_ok=True)
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        """Load saved face encodings from disk."""
        try:
            import face_recognition  # noqa: F401
            import cv2  # noqa: F401
        except ImportError as e:
            logger.error(
                f"Missing dependency: {e}\n"
                "Install with:\n"
                "  pip install face_recognition opencv-python-headless numpy\n"
                "Note: face_recognition requires dlib. On Ubuntu:\n"
                "  sudo apt install cmake libboost-all-dev\n"
                "  pip install dlib face_recognition"
            )
            return False

        # Load saved encodings
        if ENCODINGS_FILE.exists():
            try:
                data = json.loads(ENCODINGS_FILE.read_text())
                self._encodings = data
                names = list(data.keys())
                logger.info(f"Loaded {len(names)} face(s): {', '.join(names)}")
            except Exception as e:
                logger.error(f"Failed to load encodings: {e}")

        self._initialized = True
        return True

    def _save_encodings(self):
        """Save face encodings to disk."""
        ENCODINGS_FILE.write_text(json.dumps(self._encodings, indent=2))
        logger.info(f"Saved {len(self._encodings)} face encoding(s) to disk.")

    def _capture_frame(self, camera_id: int = 0) -> Optional["numpy.ndarray"]:
        """Capture a single frame from the webcam."""
        import cv2

        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            logger.error(
                f"Cannot open camera {camera_id}. "
                "Check: ls /dev/video* or try camera_id=1"
            )
            return None

        # Warm up camera (first frames are often dark)
        for _ in range(5):
            cap.read()

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            logger.error("Failed to capture frame from camera.")
            return None

        return frame

    def enroll(self, name: str, camera_id: int = 0, num_samples: int = 3) -> bool:
        """
        Enroll a new face. Takes multiple photos for better accuracy.
        
        Args:
            name: Person's name (used as identifier)
            camera_id: Camera device index (0 = default webcam)
            num_samples: Number of photos to take (more = more accurate)
            
        Returns:
            True if enrollment successful
        """
        if not self._initialized:
            if not self.initialize():
                return False

        import face_recognition
        import cv2

        logger.info(f"Enrolling face for: {name}")
        print(f"\n📸 Face Enrollment for '{name}'")
        print(f"   Taking {num_samples} photos. Look at the camera.\n")

        encodings_collected = []

        for i in range(num_samples):
            input(f"   Press Enter to capture photo {i+1}/{num_samples}...")

            frame = self._capture_frame(camera_id)
            if frame is None:
                print(f"   ❌ Camera capture failed on photo {i+1}")
                continue

            # Convert BGR (OpenCV) to RGB (face_recognition)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            if not face_locations:
                print(f"   ⚠️  No face detected in photo {i+1}. Try again.")
                continue

            if len(face_locations) > 1:
                print(f"   ⚠️  Multiple faces detected. Using the largest one.")
                # Use largest face (closest to camera)
                face_locations = [max(face_locations, key=lambda f: (f[2]-f[0]) * (f[1]-f[3]))]

            # Get 128-d face encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            if face_encodings:
                encodings_collected.append(face_encodings[0].tolist())

                # Save reference photo
                photo_path = PHOTOS_DIR / f"{name}_{i+1}.jpg"
                cv2.imwrite(str(photo_path), frame)
                print(f"   ✅ Photo {i+1} captured and encoded.")

        if not encodings_collected:
            print("   ❌ No faces could be encoded. Enrollment failed.")
            return False

        # Store encodings
        if name not in self._encodings:
            self._encodings[name] = []
        self._encodings[name].extend(encodings_collected)
        self._save_encodings()

        print(f"\n   ✅ '{name}' enrolled with {len(encodings_collected)} encoding(s).")
        print(f"   📁 Photos saved to: {PHOTOS_DIR}/")
        logger.info(f"Enrolled: {name} with {len(encodings_collected)} encodings")
        return True

    def verify(self, camera_id: int = 0, tolerance: float = 0.6) -> dict:
        """
        Verify who is in front of the camera.
        
        Args:
            camera_id: Camera device index
            tolerance: How strict the matching is (lower = stricter)
                       0.6 is default, 0.4 is strict, 0.8 is lenient
        
        Returns:
            dict with:
                - 'name': recognized person's name, or 'unknown'
                - 'confidence': match confidence (0-1, higher = better)
                - 'face_detected': bool
        """
        if not self._initialized:
            if not self.initialize():
                return {"name": "error", "confidence": 0, "face_detected": False}

        import face_recognition
        import cv2
        import numpy as np

        frame = self._capture_frame(camera_id)
        if frame is None:
            return {"name": "error", "confidence": 0, "face_detected": False}

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")

        if not face_locations:
            return {"name": "no_face", "confidence": 0, "face_detected": False}

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if not face_encodings:
            return {"name": "no_encoding", "confidence": 0, "face_detected": True}

        # Compare against enrolled faces
        test_encoding = face_encodings[0]
        best_match = "unknown"
        best_distance = 1.0

        for name, stored_encodings in self._encodings.items():
            for stored_enc in stored_encodings:
                distance = face_recognition.face_distance(
                    [np.array(stored_enc)], test_encoding
                )[0]
                if distance < best_distance:
                    best_distance = distance
                    if distance <= tolerance:
                        best_match = name

        confidence = max(0, 1 - best_distance)

        result = {
            "name": best_match,
            "confidence": round(confidence, 3),
            "face_detected": True,
        }

        if best_match != "unknown":
            logger.info(f"Face verified: {best_match} (confidence: {confidence:.1%})")
        else:
            logger.warning(f"Unknown face detected (best distance: {best_distance:.3f})")

        return result

    def list_enrolled(self) -> list[str]:
        """List all enrolled face names."""
        if not self._initialized:
            self.initialize()
        return list(self._encodings.keys())

    def remove(self, name: str) -> bool:
        """Remove an enrolled face."""
        if name in self._encodings:
            del self._encodings[name]
            self._save_encodings()

            # Remove photos
            for photo in PHOTOS_DIR.glob(f"{name}_*.jpg"):
                photo.unlink()

            logger.info(f"Removed face: {name}")
            return True
        return False

    def guard_mode(self, camera_id: int = 0, tolerance: float = 0.5) -> bool:
        """
        Security guard mode — returns True only if a KNOWN face is detected.
        Use this to gate access to sensitive JARVIS commands.
        
        Stricter tolerance (0.5) than normal verify (0.6).
        """
        result = self.verify(camera_id=camera_id, tolerance=tolerance)

        if result["name"] not in ("unknown", "no_face", "no_encoding", "error"):
            logger.info(f"🔐 Guard: Access granted to {result['name']}")
            return True
        else:
            logger.warning(f"🔴 Guard: Access DENIED — {result['name']}")
            return False
