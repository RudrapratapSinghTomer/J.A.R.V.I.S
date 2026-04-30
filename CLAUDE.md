# JARVIS Developer Guide

## Build & Run
- **Python Version**: 3.12+ (managed in venv)
- **Start Project**: `python main_async.py`
- **Dependencies**: `pip install -r requirements.txt`
- **Speech Requirements**: `ffmpeg`, `libportaudio2` (on Linux)

## Core Commands
- **Wake Words**: "jarvis", "buddy", "computer"
- **Conversation Mode**: Stays active for 30 seconds after the last interaction.

## Architecture
- `main_async.py`: Orchestrator for the voice loop.
- `core/listener.py`: Captures audio and converts to text using Whisper.
- `core/intent_router.py`: Decides whether to use the "Fast Path" (local tools) or "LLM Path" (Ollama/Gemma).
- `core/speech_output.py`: High-fidelity TTS using Edge-TTS.
- `core/llm_client.py`: Interface for OLLAMA (Local LLM).
- `memory/`: Integration with Cognee for long-term memory.

## Development Patterns
- Use `async/await` for all I/O bound tasks.
- Keep `core/` modules independent where possible.
- Use `logger` for all debugging; avoid `print`.
- Secrets go in `.env` (NOT committed).
