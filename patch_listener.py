import sys

patch = """
            audio_data = np.concatenate(frames).astype(np.float32) / 32768.0
            
            # --- START DATASET LOGGING ---
            import wave
            import csv
            import datetime
            from pathlib import Path
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_dir = Path("data/training_audio")
            audio_dir.mkdir(parents=True, exist_ok=True)
            wav_path = audio_dir / f"{timestamp}.wav"
            
            try:
                # Save the raw 16-bit PCM audio frames
                raw_audio = np.concatenate(frames).astype(np.int16).tobytes()
                with wave.open(str(wav_path), 'wb') as wf:
                    wf.setnchannels(SpeechConfig.CHANNELS)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(SpeechConfig.SAMPLE_RATE)
                    wf.writeframes(raw_audio)
                
                # Get the transcription
                text = self._whisper.transcribe(audio_data)
                
                # Append to dataset.csv
                csv_path = audio_dir / "dataset.csv"
                file_exists = csv_path.exists()
                with open(csv_path, 'a', newline='', encoding='utf-8') as cf:
                    writer = csv.writer(cf)
                    if not file_exists:
                        writer.writerow(['Timestamp', 'AudioFile', 'WhisperHeard', 'Rating', 'GroundTruth'])
                    writer.writerow([timestamp, f"{timestamp}.wav", text, '', ''])
                
                return text
                
            except Exception as ex:
                logger.error(f"Error saving training data: {ex}")
                # Fallback to standard transcribe if saving fails
                return self._whisper.transcribe(audio_data)
            # --- END DATASET LOGGING ---
"""

with open('core/listener.py', 'r') as f:
    content = f.read()

target = """            audio_data = np.concatenate(frames).astype(np.float32) / 32768.0
            return self._whisper.transcribe(audio_data)"""

if target in content:
    content = content.replace(target, patch)
    with open('core/listener.py', 'w') as f:
        f.write(content)
    print("Patched listener.py successfully.")
else:
    print("Could not find target string in listener.py")
