# 🚀 J.A.R.V.I.S — Setup & Run Guide
> Everything runs locally. Zero cloud. Zero billing. Zero API keys needed.

---

## Prerequisites
- Python 3.12+ (you have 3.12.3 ✅)
- Ollama installed and running (`ollama serve`)
- ~2GB free disk space for Gemma2 model
- Webcam (for face recognition — optional)
- Microphone (for voice commands)
- Internet for first-time package download only

### System Dependencies (for face recognition)
```bash
# Required for dlib/face_recognition compilation
sudo apt install cmake libboost-all-dev build-essential
```

---

## Step 1: Environment Setup

```bash
cd /home/rudrapratap/Desktop

# Your venv is already the J.A.R.V.I.S directory
source J.A.R.V.I.S/bin/activate

# Create .env from template
cp J.A.R.V.I.S/.env.example J.A.R.V.I.S/.env
# Edit .env if needed (defaults work out of the box)
```

## Step 2: Install Dependencies

```bash
# With venv activated:
pip install -r J.A.R.V.I.S/requirements.txt
```

**What gets installed (all free, all open-source):**
| Package | Size | What For |
|---------|------|----------|
| cognee | ~50MB | Memory/knowledge graph engine |
| feedparser | ~100KB | RSS feed parsing (learning) |
| pip-audit | ~5MB | Dependency vulnerability scanner |
| ollama | ~2MB | Python client for local Ollama |
| schedule | ~50KB | Job scheduling |
| psutil | ~1MB | System monitoring |

## Step 3: Pull Gemma2 Model

```bash
# ~1.6GB download — only needed once
ollama pull qwen3.5:397b-cloud
```

**Or, if you have custom weights from Google Drive:**
```bash
# Download from Drive
pip install gdown
gdown --folder "https://drive.google.com/drive/folders/1qpxL_7k6SPrFX5oKEDuRhWdmNn3BW3VJ" \
      -O J.A.R.V.I.S/models/

# If weights are .safetensors, convert to GGUF:
# (see config/ollama_modelfile for full instructions)

# Register custom model
cd J.A.R.V.I.S
ollama create jarvis-gemma -f config/ollama_modelfile
# Then set OLLAMA_MODEL=jarvis-gemma in .env
```

## Step 4: Install Nightly Cron Jobs

```bash
# Sets up: learning at 1 AM IST + security at 2 AM IST
bash J.A.R.V.I.S/scripts/cron_setup.sh

# Verify:
crontab -l
```

## Step 5: Run J.A.R.V.I.S

```bash
cd /home/rudrapratap/Desktop/J.A.R.V.I.S
source bin/activate
python main.py
```

**What happens on startup:**
1. 🔐 Security check — reads latest scan report
2. 🤖 LLM health check — verifies Ollama + Gemma2 are running
3. 🧠 Memory init — connects to Cognee, loads context files
4. 🎤 Listening — waiting for "Hey JARVIS" wake word

---

## Voice Commands

| Say | What Happens |
|-----|-------------|
| "JARVIS hello" | Greeting |
| "JARVIS what time is it" | Current time |
| "JARVIS what's the date" | Current date |
| "JARVIS remember I prefer dark themes" | Saves to memory |
| "JARVIS what do you know about my preferences" | Searches memory |
| "JARVIS security check" | Shows latest scan report |
| "JARVIS enroll face" | Registers your face via webcam (3 photos) |
| "JARVIS verify face" / "JARVIS who am I" | Identifies who’s in front of camera |
| "JARVIS list faces" | Shows all enrolled faces |
| "JARVIS [anything else]" | Sent to local Gemma2 LLM |

---

## Manual Commands

```bash
# Run security scan manually
bash scripts/security_scan.sh

# Run learning manually
python -m skills.autonomous_learner

# Check Ollama status
ollama list
```

---

## File Structure

```
J.A.R.V.I.S/
├── main.py                  # Entry point ← START HERE
├── requirements.txt         # Dependencies
├── .env.example             # Template (copy to .env)
├── .env                     # Your secrets (gitignored)
├── .gitignore               # Protects secrets & data
├── PROGRESS.md              # Build progress tracker
├── core/
│   ├── listener.py          # Voice I/O (mic + TTS)
│   ├── intent_router.py     # Command routing (fast/slow path)
│   └── llm_client.py        # Ollama client (chat, stream)
├── context/                 # Personal context files
│   ├── memory.md            # Long-term facts about you
│   ├── personality.md       # How JARVIS behaves
│   ├── skills.md            # Your technical profile
│   ├── projects.md          # Active projects
│   └── tasks.md             # Current priorities
├── memory/
│   └── cognee_bridge.py     # Cognee integration
├── skills/
│   └── autonomous_learner.py # Nightly web learning
├── tools/                   # MCP servers (future)
├── scripts/
│   ├── security_scan.sh     # Nightly security scan
│   ├── security_monitor.py  # Startup security check
│   └── cron_setup.sh        # Cron installer
├── config/
│   └── ollama_modelfile     # Custom Gemma2 model config
├── security/                # Scan reports (auto-generated)
├── models/                  # Custom GGUF weights
├── data/cognee_db/          # Cognee knowledge graph
└── logs/                    # Runtime logs
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot connect to Ollama" | Run `ollama serve` in another terminal |
| "Model not found" | Run `ollama pull gemma2:2b` |
| "Cognee not installed" | `pip install cognee` (in venv) |
| "No security report" | Run `bash scripts/security_scan.sh` first |
| "Microphone not working" | Check `arecord -l` for audio devices |

---
*All local. All free. No API keys. No billing. Ever.*
