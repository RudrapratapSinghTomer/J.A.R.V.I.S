#!/usr/bin/env python3
"""
J.A.R.V.I.S Session Manager
==============================
Tracks conversation sessions, manages session lifecycle,
and enables JARVIS to remember what happened across restarts.

Each session:
- Gets a unique ID
- Logs start/end time
- Saves summary to Cognee memory on exit
- Tracks commands processed

This is how JARVIS "remembers" yesterday's conversation.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis.session")

SESSIONS_DIR = Path(__file__).parent.parent / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class Session:
    """Tracks a single JARVIS interaction session."""

    def __init__(self):
        self.id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.commands: list[dict] = []
        self.security_status: Optional[str] = None
        self.llm_model: Optional[str] = None
        self.claw_available: Optional[bool] = None

        logger.info(f"Session started: {self.id}")

    def log_command(self, command: str, response: str = "", route: str = ""):
        """Log a command processed during this session."""
        self.commands.append({
            "time": datetime.now().isoformat(),
            "command": command,
            "response": response[:200],  # Cap for storage
            "route": route,  # fast_path or llm
        })

    def end(self):
        """End the session and save to disk."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        session_data = {
            "id": self.id,
            "start": self.start_time.isoformat(),
            "end": self.end_time.isoformat(),
            "duration_minutes": round(duration / 60, 1),
            "commands_count": len(self.commands),
            "commands": self.commands,
            "security_status": self.security_status,
            "llm_model": self.llm_model,
            "claw_available": self.claw_available,
        }

        # Save to disk
        session_file = SESSIONS_DIR / f"session_{self.id}.json"
        try:
            session_file.write_text(
                json.dumps(session_data, indent=2),
                encoding="utf-8",
            )
            logger.info(
                f"Session {self.id} ended. Duration: {round(duration/60, 1)}min, "
                f"Commands: {len(self.commands)}"
            )
        except Exception as e:
            logger.error(f"Failed to write session log {session_file}: {e}")

        # Also save summary to Cognee memory (async)
        self._save_to_memory(session_data)

        return session_data

    def _save_to_memory(self, session_data: dict):
        """Save session summary to Cognee for cross-session recall."""
        # TEMPORARY: Disable memory save if the global disable is active
        import os
        if os.getenv("JARVIS_MEMORY_ENABLED", "true").lower() == "false":
            return

        try:
            from memory.cognee_bridge import memory

            summary = (
                f"Session {session_data['id']}: "
                f"{session_data['duration_minutes']} minutes, "
                f"{session_data['commands_count']} commands. "
            )

            # Include top commands for context
            if self.commands:
                top_commands = [c["command"] for c in self.commands[:5]]
                summary += f"Topics: {', '.join(top_commands)}"

            memory.remember_sync(
                summary,
                metadata={
                    "type": "session_log",
                    "session_id": self.id,
                    "date": session_data["start"],
                },
            )
        except Exception as e:
            logger.warning(f"Could not save session to memory: {e}")

    @property
    def summary(self) -> str:
        """Quick summary of current session."""
        duration = (datetime.now() - self.start_time).total_seconds()
        return (
            f"Session {self.id} | "
            f"{round(duration/60, 1)}min | "
            f"{len(self.commands)} commands"
        )


def get_recent_sessions(count: int = 5) -> list[dict]:
    """Load the most recent session logs."""
    session_files = sorted(SESSIONS_DIR.glob("session_*.json"), reverse=True)
    sessions = []
    for f in session_files[:count]:
        try:
            sessions.append(json.loads(f.read_text()))
        except Exception:
            pass
    return sessions
