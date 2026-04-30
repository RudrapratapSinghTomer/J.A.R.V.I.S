import os
import psutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("jarvis.skills.monitor")

class DynamicMonitor:
    """
    Skill for proactively monitoring system health, security, and project status.
    """
    def __init__(self):
        self.workspace_root = Path(__file__).parent.parent
        self.last_git_status = {}

    async def check_system_health(self):
        """Monitor CPU, RAM, and Battery."""
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        battery = psutil.sensors_battery()
        
        disk = psutil.disk_usage('/').percent
        
        status = {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "battery_percent": battery.percent if battery else "N/A",
            "power_plugged": battery.power_plugged if battery else "N/A"
        }
        
        alerts = []
        if cpu > 90: alerts.append(f"High CPU usage: {cpu}%")
        if ram > 90: alerts.append(f"High RAM usage: {ram}%")
        if disk > 95: alerts.append(f"Critical Disk Space: {disk}%")
        
        # Monitor for memory-hogging processes
        for proc in psutil.process_iter(['name', 'memory_percent']):
            try:
                if proc.info['memory_percent'] > 20:
                    alerts.append(f"Heavy process detected: {proc.info['name']} ({proc.info['memory_percent']:.1f}%)")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            
        return status, alerts

    async def check_git_status(self):
        """Scan projects on Desktop for uncommitted changes or build errors."""
        desktop_path = Path(os.path.expanduser("~/Desktop"))
        changes_detected = []
        if not desktop_path.exists():
            logger.warning(f"Desktop path does not exist: {desktop_path}")
            return changes_detected
        
        # Simple scan for git directories on desktop
        for item in desktop_path.iterdir():
            if item.is_dir() and (item / ".git").exists():
                try:
                    # Run 'git status' to see if there are changes
                    proc = await asyncio.create_subprocess_exec(
                        "git", "status", "--short",
                        cwd=str(item),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, _ = await proc.communicate()
                    status_output = stdout.decode().strip()
                    
                    if status_output:
                        changes_detected.append({
                            "project": item.name,
                            "summary": status_output,
                            "path": str(item)
                        })
                except Exception as e:
                    logger.error(f"Failed to check git status for {item.name}: {e}")
                    
        return changes_detected

    async def check_security(self):
        """Invoke the Enhanced Security Scanner and return findings."""
        try:
            from scripts.security_monitor import get_latest_report
            report = get_latest_report()
            return report["warnings"]
        except Exception as e:
            logger.error(f"Security skill failed to get report: {e}")
            return ["Security Monitor connection failed."]

    async def check_logs_for_errors(self):
        """Scan the primary JARVIS logs for critical errors."""
        # Check both synchronous and asynchronous logs
        log_files = [
            self.workspace_root / "logs" / "jarvis.log",
            self.workspace_root / "logs" / "jarvis_async.log"
        ]
        
        errors = []
        for log_file in log_files:
            if not log_file.exists():
                continue
            
            try:
                # Only read the last 50 lines to avoid overhead
                import collections
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    last_lines = collections.deque(f, 50)
                    
                for line in last_lines:
                    if "CRITICAL" in line or "ERROR" in line:
                        # Filter out known non-breaking errors
                        if any(w in line for w in ["Recall failed", "Connection reset", "Security Monitor"]):
                            continue
                        errors.append(line.strip())
            except Exception as e:
                logger.error(f"Failed to scan log {log_file.name}: {e}")
            
        return list(set(errors)) # Deduplicate

monitor_skill = DynamicMonitor()
