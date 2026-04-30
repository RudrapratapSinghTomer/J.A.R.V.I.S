# 🏗️ J.A.R.V.I.S. Architectural Records
> This document maintains a record of the folder structure and design decisions for J.A.R.V.I.S.

## 📁 Folder Structure (Current)

```text
J.A.R.V.I.S/
├── main.py              # Main entry point (Orchestrator)
├── requirements.txt     # Python dependencies
├── .env                 # Local configuration (secrets, IPs)
├── core/                # Core Logic Modules
│   ├── listener.py      # Voice I/O (Google + Vosk)
│   ├── speech_local.py  # Vosk offline engine
│   ├── intent_router.py # Decision engine (Fast-Path vs Slow-Path)
│   ├── llm_client.py    # Local LLM Interface (Ollama)
│   ├── session_manager.py# Lifecycle & Context tracking
│   └── alsa_suppress.py # C-level audio warning suppressor
├── memory/              # Knowledge Graph & Memory
│   └── cognee_bridge.py # Cognee (RAG / Knowledge Graph)
├── context/             # Static Personality & Memory files
│   ├── personality.md   # Assistant character profile
│   ├── memory.md        # Static user facts
│   └── tasks.md         # Active task list
├── scripts/             # Utility & Security Scripts
│   ├── security_scan.sh # Bash-based system check
│   └── cron_setup.sh    # Background task installer
├── tools/               # Integration Tools
│   ├── telegram_bot.py  # Remote interface
│   └── system_mcp.py    # MCP (Model Context Protocol) server
└── data/                # Runtime Data
    ├── cognee_db/       # Memory database
    └── sessions/        # JSON session logs
```

## 🧠 Design Philosophy: Two-Tiered Orchestration

1.  **The "Fast-Path" (Python/Regex)**:
    - Handles simple commands (Time, Date, Security Checks) instantly.
    - Does NOT require an LLM, ensuring zero latency for basic tasks.
    - Uses Phonetic Fuzzy Matching to ensure it hears the wake-word even with noise.

2.  **The "Slow-Path" (Claude/Ollama)**:
    - Triggered when the Fast-Path doesn't recognize a command.
    - Sends the full request to the Local LLM (Claude-enhanced Ollama).
    - The LLM creates an "Execution Plan" and calls specialized tools (MCP).

## 🔐 Security & Privacy
- **Zero-Cloud LLM**: All thinking happens on your Windows host/Ubuntu VM.
- **Vosk Fallback**: If internet is lost, J.A.R.V.I.S. can still recognize basic commands via local Vosk models.
- **Encrypted/Local Memory**: No user data is sent to vector-database providers; everything stays in `data/cognee_db`.

---
*Generated: 2026-04-22*
