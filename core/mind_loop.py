import asyncio
import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from skills.dynamic_monitor import monitor_skill
from memory.cognee_bridge import memory
from skills.engineer_skill import engineer_skill

logger = logging.getLogger("jarvis.mind")

try:
    if os.name == "nt":
        from win10toast import ToastNotifier
    else:
        ToastNotifier = None
except Exception:
    ToastNotifier = None

class MindLoop:
    """
    The background heartbeat of J.A.R.V.I.S.
    Handles proactive tasks, monitoring, and autonomous decisions.
    """
    def __init__(self):
        self.toaster = ToastNotifier() if ToastNotifier else None
        self.is_running = False
        self.interval = int(os.getenv("JARVIS_MIND_INTERVAL", "600"))
        self.loop_count = 0
        self.last_alerts = {}  # Cache to prevent notification spam

    def notify_desktop(self, title: str, message: str):
        """Send a clear Windows notification via PowerShell (more reliable than win10toast)."""
        import subprocess
        
        # Whitelist for Git projects to ignore (prevents noise)
        ignore_projects = os.getenv("JARVIS_IGNORE_GIT_PROJECTS", "insights360-source").split(",")
        if any(proj in message for proj in ignore_projects):
            return

        logger.info(f"Sending Desktop Notification: {title}")
        
        powershell_cmd = f"New-BurntToastNotification -Text '{title}', '{message}'"
        # Fallback to standard msgbox if BurntToast isn't installed
        fallback_cmd = f"$wshell = New-Object -ComObject WScript.Shell; $wshell.Popup('{message}', 0, '{title}', 64)"
        
        try:
            # We use the standard shell popup for maximum compatibility without extra PS modules
            subprocess.Popen(["powershell", "-Command", fallback_cmd], shell=True)
        except Exception as e:
            logger.error(f"Desktop notification failed: {e}")

    async def notify_email(self, title: str, message: str):
        """Send email notification via standard SMTP using JARVIS identity."""
        if os.getenv("JARVIS_EMAIL_ENABLED", "false").lower() != "true":
            return

        recipient = os.getenv("NOTIFY_EMAIL_RECIPIENT")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        # Prioritize JARVIS Identity for the sender
        smtp_user = os.getenv("JARVIS_EMAIL") or os.getenv("SMTP_USER")
        smtp_pass = os.getenv("JARVIS_EMAIL_PASS") or os.getenv("SMTP_PASS")

        if not all([smtp_server, smtp_user, smtp_pass, recipient]):
            logger.warning("Email notification skipped: Missing SMTP configuration.")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = recipient
            msg['Subject'] = title
            msg.attach(MIMEText(message, 'plain'))

            # Run SMTP in executor to avoid blocking the event loop
            def _send_smtp():
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)

            await asyncio.get_running_loop().run_in_executor(None, _send_smtp)
            logger.info(f"Email notification sent from {smtp_user} to {recipient}")
        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    async def notify_autonomous_action(self, reason: str, action: str, method: str):
        """
        Specific notification format for autonomous actions.
        """
        # Throttling to prevent spam
        alert_id = f"{reason}_{action}"
        now = datetime.now().timestamp()
        if alert_id in self.last_alerts and (now - self.last_alerts[alert_id]) < 3600:
            return

        title = "🤖 JARVIS Autonomous Action"
        message = f"WHY: {reason}\nWHAT: {action}\nHOW: {method}"
        
        # Check ignore list
        ignore_projects = os.getenv("JARVIS_IGNORE_GIT_PROJECTS", "insights360-source").split(",")
        if any(proj in message for proj in ignore_projects):
            return
        
        logger.info(f"AUTONOMOUS ACTION: {reason}")
        self.notify_desktop(title, message)
        await self.notify_email(title, message)
        
        self.last_alerts[alert_id] = now

    async def start(self):
        """Start the background consciousness loop."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("J.A.R.V.I.S Mind Loop started.")
        
        while self.is_running:
            try:
                self.loop_count += 1
                self.interval = int(os.getenv("JARVIS_MIND_INTERVAL", "600"))
                logger.info(f"Mind Loop Cycle #{self.loop_count} starting...")
                
                # 1. System Health Check
                health, alerts = await monitor_skill.check_system_health()
                if alerts:
                    await self.notify_autonomous_action(
                        reason="Detected system performance issues.",
                        action=f"Monitoring resource usage: {', '.join(alerts)}",
                        method="System telemetry via psutil"
                    )
                
                # 2. Git Monitoring
                git_changes = await monitor_skill.check_git_status()
                if git_changes:
                    change = git_changes[0]
                    await self.notify_autonomous_action(
                        reason=f"Detected uncommitted changes in project '{change['project']}'.",
                        action="Scanning project structure for potential updates or build tasks.",
                        method="Claw Brain workspace analysis"
                    )
                    
                # 3. Memory Ingestion (Proactive)
                if self.loop_count % 5 == 0:
                    logger.info("Mind Loop: Proactively improving memory graph...")
                    await memory.improve()

                # 4. Proactive Error Patching
                log_errors = await monitor_skill.check_logs_for_errors()
                if log_errors:
                    error_summary = log_errors[0]
                    await self.notify_autonomous_action(
                        reason=f"Detected critical error in logs: {error_summary[:100]}",
                        action="Self-diagnostic and patch proposal initiated.",
                        method="Engineer Skill via Claw Brain"
                    )
                    # Trigger autonomous fix
                    await engineer_skill.execute(f"The system logs show a critical error: {error_summary}. Please investigate and fix.")

                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"Error in Mind Loop: {e}")
                await asyncio.sleep(60)

    def stop(self):
        self.is_running = False
        logger.info("J.A.R.V.I.S Mind Loop stopped.")

mind_loop = MindLoop()
