# 🧠 J.A.R.V.I.S — The Autonomous AI Assistant

J.A.R.V.I.S is a modular, high-performance local AI assistant designed to run completely offline on your own hardware. It integrates voice recognition, neural speech synthesis, long-term memory (Cognee), and an autonomous agent brain (Claw).

---

## 🖥️ Windows 11 Migration Guide
If you are moving this project from Ubuntu to Windows 11, follow these steps carefully.

### 1. Prerequisites
- **Python 3.12+**: Ensure you have Python installed and added to your PATH.
- **Git**: Installed with "Enable symbolic links" (important for submodules).
- **Build Tools**: Install [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (required for `dlib` and `pyaudio`).
- **Ollama**: Download and install [Ollama for Windows](https://ollama.com/download/windows).

### 2. Cloning the Repository
Since J.A.R.V.I.S uses submodules, you **must** clone with the `--recursive` flag:
```powershell
git clone --recursive <your-repo-url>
cd J.A.R.V.I.S
```

### 3. Setting Up the Virtual Environment
Windows uses different paths for the virtual environment than Linux.
```powershell
# Create venv
python -m venv venv

# Activate venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration Changes (.env)
You must update your `.env` file for Windows compatibility. Use `\` or `/` (Python handles both, but Windows native paths use `\`).

**Crucial Windows Changes:**
| Variable | Ubuntu Value (Example) | Windows Value (Example) |
|----------|-------------------------|-------------------------|
| `CLAW_PATH` | `/usr/local/bin/claw` | `C:\Users\YourName\bin\claw.exe` |
| `COGNEE_DB_PATH` | `./data/cognee_db` | `.\data\cognee_db` |
| `OLLAMA_HOST` | `http://localhost:11434`| `http://127.0.0.1:11434` |

### 5. Audio Subsystem
Windows handles audio via PortAudio. If `pip install pyaudio` fails, you may need to download a pre-compiled `.whl` file or ensure Build Tools are installed.
- **Microphone**: Ensure your default recording device is set correctly in Windows Sound Settings.
- **TTS**: The system uses `edge-tts` or `pyttsx3`, which are compatible with Windows.

### 6. Submodules (Claw)
The `claw-code` submodule in `submodules/claw-code` needs to be functional. On Windows, you will need the Windows version of the `claw` binary.
1. Go to `submodules/claw-code`.
2. Follow its specific README to build or download the Windows executable.
3. Update `CLAW_PATH` in your `.env` to point to the `.exe`.

---

## 🚀 General Setup (Standard)
1. **Pull the Model**: `ollama pull qwen3.5:397b-cloud`
2. **Setup Memory**: `python -m memory.cognee_bridge` (to initialize DB)
3. **Run**: `python main_async.py`

## 📂 Project Structure
- `main_async.py`: Main entry point (Asynchronous).
- `core/`: Core logic (listener, intent routing, LLM/Claw clients).
- `submodules/claw-code`: The autonomous brain core.
- `memory/`: Long-term memory and knowledge graph integration.
- `skills/`: Autonomous behaviors (learner, security).
- `data/`: Local databases and session state (Git Ignored).

## ⚠️ Important Notes
- **Line Endings**: Git might change line endings to CRLF on Windows. This is usually fine for Python but be careful with shell scripts in `scripts/`.
- **Paths**: Always use `os.path.join()` or `pathlib` when writing new code to ensure cross-platform compatibility.
