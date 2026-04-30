import pyaudio

def list_devices():
    pa = pyaudio.PyAudio()
    print("\n" + "="*50)
    print("   J.A.R.V.I.S. Audio Device Discovery")
    print("="*50)
    print(f"{'Index':<7} {'Device Name':<40} {'Channels':<10}")
    print("-" * 57)
    
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if info.get('maxInputChannels') > 0:
            print(f"{i:<7} {info.get('name')[:38]:<40} {info.get('maxInputChannels'):<10}")
            
    print("="*50)
    print("\nDIRECTIONS:")
    print("1. Find the index number of your actual microphone.")
    print("2. Add 'JARVIS_INPUT_DEVICE=X' to your .env file (replace X with the index).")
    pa.terminate()

if __name__ == "__main__":
    list_devices()
