#!/usr/bin/env python3
"""
J.A.R.V.I.S Autonomous Learner
================================
Runs nightly at 1 AM IST (19:30 UTC) via cron.
Fetches from FREE public sources only (RSS/Atom feeds).
Stores everything in Cognee's local knowledge graph.

Zero API keys needed. Zero billing. Fully offline-safe.

Usage:
    python -m skills.autonomous_learner        # manual run
    # Or via cron: 30 19 * * * cd /home/rudrapratap/Desktop/J.A.R.V.I.S && bin/python -m skills.autonomous_learner
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("jarvis.learner")
logs_dir = Path(__file__).parent.parent / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            logs_dir / "learner.log",
            mode="a"
        ),
    ]
)

# 100% free sources — no API keys, no billing
SOURCES = {
    "arxiv_ai": {
        "url": "https://arxiv.org/rss/cs.AI",
        "description": "AI research papers",
        "max_entries": 5,
    },
    "arxiv_ml": {
        "url": "https://arxiv.org/rss/cs.LG",
        "description": "Machine learning papers",
        "max_entries": 5,
    },
    "hacker_news": {
        "url": "https://hnrss.org/frontpage?points=100",
        "description": "Top HN posts (100+ upvotes)",
        "max_entries": 5,
    },
    "local_llama": {
        "url": "https://www.reddit.com/r/LocalLLaMA/.rss",
        "description": "Local LLM community",
        "max_entries": 5,
    },
    "linux_security": {
        "url": "https://www.linuxsecurity.com/linuxsecurity_advisories.rdf",
        "description": "Linux security advisories",
        "max_entries": 3,
    },
}


async def fetch_and_learn():
    """
    Fetch from all sources and store in Cognee.
    Designed to run unattended — catches all errors gracefully.
    """
    try:
        import feedparser
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")
        return 0, 1

    from memory.cognee_bridge import memory

    await memory.initialize()

    total_learned = 0
    errors = 0

    for name, source in SOURCES.items():
        try:
            logger.info(f"Fetching: {name} ({source['description']})")
            feed = feedparser.parse(source["url"])

            if feed.bozo and not feed.entries:
                logger.warning(f"Feed error for {name}: {feed.bozo_exception}")
                errors += 1
                continue

            for entry in feed.entries[:source["max_entries"]]:
                title = entry.get("title", "Untitled")
                summary = entry.get("summary", "")[:1500]  # Cap length
                link = entry.get("link", "")
                published = entry.get("published", "")

                content = (
                    f"[{name.upper()}] {title}\n"
                    f"Source: {link}\n"
                    f"Date: {published}\n"
                    f"Summary: {summary}"
                )

                await memory.remember(
                    content,
                    metadata={
                        "type": "autonomous_learning",
                        "source": name,
                        "category": source["description"],
                        "url": link,
                        "learned_at": datetime.now().isoformat(),
                    }
                )
                total_learned += 1

        except Exception as e:
            logger.error(f"Failed source {name}: {e}")
            errors += 1

    # Consolidate knowledge graph after batch ingestion
    if total_learned > 0:
        logger.info("Consolidating knowledge graph...")
        await memory.improve()

    # Write summary log
    ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
    summary = (
        f"[JARVIS Autonomous Learning] {ist_now.strftime('%Y-%m-%d %H:%M IST')}\n"
        f"  Items learned: {total_learned}\n"
        f"  Errors: {errors}\n"
        f"  Sources checked: {len(SOURCES)}"
    )
    logger.info(summary)

    # Save summary as a memory too (so JARVIS can report it in morning)
    await memory.remember(
        summary,
        metadata={
            "type": "learning_report",
            "date": datetime.now().isoformat(),
        }
    )

    return total_learned, errors


if __name__ == "__main__":
    print(f"[JARVIS Learner] Starting at {datetime.now()}")
    learned, errs = asyncio.run(fetch_and_learn())
    print(f"[JARVIS Learner] Done. Learned: {learned}, Errors: {errs}")
