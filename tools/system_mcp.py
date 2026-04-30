#!/usr/bin/env python3
"""
J.A.R.V.I.S System MCP Tool Server
=====================================
Exposes system information as an MCP-compliant tool.
Ruflo (or any MCP client) can call these tools.

Tools provided:
- get_system_info: CPU, RAM, disk usage
- get_ollama_status: Which models are running
- get_security_report: Latest security scan summary
- get_uptime: System uptime

Usage:
    python -m tools.system_mcp
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.tools.system")


def get_system_info() -> dict:
    """Get current system CPU, RAM, disk usage."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.home()))

        return {
            "cpu_percent": cpu_percent,
            "cpu_cores": psutil.cpu_count(),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_percent": round(disk.percent, 1),
            "timestamp": datetime.now().isoformat(),
        }
    except ImportError:
        return {"error": "psutil not installed. Run: pip install psutil"}


def get_ollama_status() -> dict:
    """Check which Ollama models are available and running."""
    import requests

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    if host.endswith("/v1"):
        host = host[:-3]
    try:
        resp = requests.get(f"{host}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = [
            {
                "name": m["name"],
                "size_gb": round(m.get("size", 0) / (1024**3), 1),
                "modified": m.get("modified_at", ""),
            }
            for m in data.get("models", [])
        ]
        return {"status": "online", "models": models, "host": host}
    except requests.ConnectionError:
        return {"status": "offline", "error": f"Cannot reach Ollama at {host}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_security_report() -> dict:
    """Get the latest security scan summary."""
    try:
        from scripts.security_monitor import get_latest_report
        return get_latest_report()
    except Exception as e:
        return {"error": str(e)}


def get_uptime() -> dict:
    """Get system uptime."""
    try:
        import psutil
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        return {
            "boot_time": boot_time.isoformat(),
            "uptime_hours": round(uptime.total_seconds() / 3600, 1),
            "uptime_human": str(uptime).split(".")[0],
        }
    except ImportError:
        return {"error": "psutil not installed"}


# MCP Tool Registry — maps tool names to functions
TOOLS = {
    "get_system_info": {
        "function": get_system_info,
        "description": "Get current system CPU, RAM, and disk usage",
        "parameters": {},
    },
    "get_ollama_status": {
        "function": get_ollama_status,
        "description": "Check Ollama status and available models",
        "parameters": {},
    },
    "get_security_report": {
        "function": get_security_report,
        "description": "Get the latest nightly security scan summary",
        "parameters": {},
    },
    "get_uptime": {
        "function": get_uptime,
        "description": "Get system uptime since last boot",
        "parameters": {},
    },
}


def call_tool(name: str, arguments: dict = None) -> dict:
    """
    Call a registered tool by name.
    Used by Ruflo MCP bridge or direct invocation.
    """
    if name not in TOOLS:
        return {"error": f"Unknown tool: {name}. Available: {list(TOOLS.keys())}"}

    func = TOOLS[name]["function"]
    try:
        return func(**(arguments or {}))
    except Exception as e:
        return {"error": f"Tool {name} failed: {str(e)}"}


def list_tools() -> list[dict]:
    """List all available tools with descriptions."""
    return [
        {
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"],
        }
        for name, info in TOOLS.items()
    ]


if __name__ == "__main__":
    # CLI mode — run any tool directly
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
        result = call_tool(tool_name)
        print(json.dumps(result, indent=2))
    else:
        print("J.A.R.V.I.S System Tools")
        print("========================")
        for tool in list_tools():
            print(f"  {tool['name']}: {tool['description']}")
        print(f"\nUsage: python -m tools.system_mcp <tool_name>")
        print(f"Example: python -m tools.system_mcp get_system_info")
