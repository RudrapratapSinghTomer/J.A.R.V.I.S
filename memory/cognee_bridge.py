"""
J.A.R.V.I.S Memory Bridge — Cognee Integration
================================================
Single source of truth for all persistent memory.
Uses Cognee's knowledge graph + vector search locally.

No external APIs. All data stored in ./data/cognee_db/
"""

import asyncio
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("jarvis.memory")

# Optional dependency probe: never fail module import if transformers/torch stack is unstable.
try:
    from transformers import AutoTokenizer  # noqa: F401
    logger.info("Transformers AutoTokenizer pre-loaded successfully.")
except Exception as e:
    logger.warning(f"Transformers preload skipped: {e}")

# Force local dummy keys for Cognee/LiteLLM validation
os.environ["OPENAI_API_KEY"] = "sk-dummy"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"
os.environ["OLLAMA_API_KEY"] = "sk-dummy"
os.environ["LLM_API_KEY"] = "sk-dummy"
os.environ["COGNEE_LLM_PROVIDER"] = "ollama"
os.environ["HUGGINGFACE_TOKENIZER"] = "gpt2"
os.environ["COGNEE_HUGGINGFACE_TOKENIZER"] = "gpt2" # Try both variations
os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true" # Avoid timeouts if Ollama is slow loading models

# Paths — everything inside J.A.R.V.I.S folder
BASE_DIR = Path(__file__).parent.parent
CONTEXT_DIR = BASE_DIR / "context"
COGNEE_DB_DIR = BASE_DIR / "data" / "cognee_db"


class JarvisMemory:
    """
    Unified memory interface for J.A.R.V.I.S.
    
    Wraps Cognee to provide:
    - remember(text)  → store to knowledge graph
    - recall(query)   → semantic search over all memories
    - forget(query)   → remove specific memories
    - improve()       → consolidate/optimize knowledge graph
    - load_context()  → ingest personal .md files on startup
    - record_reflection(task, outcome) → store internal learnings
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(COGNEE_DB_DIR)
        self._initialized = False
        self._context_loaded = False

    async def initialize(self):
        """
        Initialize Cognee with local-only settings.
        Must be called once on startup before any other operation.
        """
        if self._initialized:
            return

        try:
            # Configure Cognee for fully local operation
            import cognee
            
            print("Initializing J.A.R.V.I.S Memory (this may take a moment)...")

            # 1. Set Providers first
            cognee.config.set_llm_provider("ollama")
            cognee.config.set_embedding_provider("ollama") # Added to ensure embedding doesn't trigger OpenAI check
            
            # 2. Set Model (prefixed for LiteLLM)
            model_name = os.getenv("OLLAMA_MODEL", "qwen3.5:397b-cloud")
            if not model_name.startswith("ollama/"):
                model_name = f"ollama/{model_name}"
            
            cognee.config.set_llm_model(model_name)
            cognee.config.set_embedding_model(model_name)
            
            # 3. Set Endpoint
            ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
            cognee.config.set_llm_endpoint(ollama_host)
            cognee.config.set_embedding_endpoint(ollama_host)
            cognee.config.set_llm_api_key("sk-dummy") # Mandatory for Cognee 1.x even for Ollama
            cognee.config.set_embedding_api_key("sk-dummy")
            
            # 4. Storage
            cognee.config.set_vector_db_provider("lancedb")
            cognee.config.set_vector_db_url(self.db_path)

            # 5. Fix: Set explicit tokenizer to avoid HF search for local Ollama names
            cognee.config.set_embedding_config({
                "huggingface_tokenizer": "gpt2"
            })

            self._initialized = True
            logger.info(f"Memory initialized. DB: {self.db_path}")

        except ImportError as e:
            logger.error(f"Cognee import failed: {e}. Run: pip install cognee")
        except Exception as e:
            logger.error(f"Memory init failed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def load_context(self):
        """
        Load all personal context .md files into memory on startup.
        Files: memory.md, personality.md, skills.md, projects.md, tasks.md
        
        Only runs once per session. Files are loaded as persistent knowledge.
        """
        if self._context_loaded:
            logger.info("Context already loaded this session.")
            return

        if not self._initialized:
            await self.initialize()

        context_files = list(CONTEXT_DIR.glob("*.md"))
        if not context_files:
            logger.warning(f"No context files found in {CONTEXT_DIR}")
            return

        loaded = 0
        import cognee
        
        # Batch add all files first (lightweight)
        for md_file in context_files:
            try:
                content = md_file.read_text(encoding="utf-8").strip()
                if not content:
                    logger.warning(f"Skipping empty context file: {md_file.name}")
                    continue
                await cognee.add(content)
                loaded += 1
                logger.info(f"Buffered context: {md_file.name}")
            except Exception as e:
                logger.error(f"Failed to buffer {md_file.name}: {e}")

        # Run cognify once for all files (heavy)
        if loaded > 0:
            logger.info(f"Cognifying {loaded} files. This may take a moment, Sir...")
            await cognee.cognify()
            logger.info("Knowledge graph built successfully.")

        self._context_loaded = True
        logger.info(f"Context fully loaded into memory.")

    async def remember(self, text: str, metadata: Optional[dict] = None):
        """
        Store information in the knowledge graph.
        
        Args:
            text: The content to remember
            metadata: Optional dict with source, type, date etc.
        """
        if not self._initialized:
            await self.initialize()

        try:
            if not text or not text.strip():
                return
            import cognee
            await cognee.add(text)
            # In V1, we should not cognify on every single 'remember' 
            # unless it's a one-off command. For startup, we batch it.
            logger.debug(f"Remembered (buffered): {text[:80]}...")
        except ImportError as e:
            logger.warning(f"[FALLBACK] Cognee not available: {e}")
        except Exception as e:
            logger.error(f"Remember failed: {e}")

    async def recall(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Semantic search over all memories with Keyword Fallback.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            
        Returns:
            List of dicts with 'text' and 'score' keys
        """
        if not self._initialized:
            await self.initialize()

        formatted = []
        try:
            import cognee
            results = await cognee.search("similarity", query=query)
            
            # Normalize results to consistent format
            for r in results[:top_k]:
                formatted.append({
                    "text": str(r.get("text", r)),
                    "score": r.get("score", 0.8) if isinstance(r, dict) else 0.7,
                    "source": "cognee_graph"
                })

        except Exception as e:
            logger.warning(f"Cognee recall failed: {e}. Falling back to Keyword search.")

        # KEYWORD FALLBACK: Search context files directly for direct matches
        if not formatted or len(formatted) < 2:
            try:
                keywords = [w.lower() for w in query.split() if len(w) > 3]
                context_files = list(CONTEXT_DIR.glob("*.md"))
                
                for md_file in context_files:
                    content = md_file.read_text(encoding="utf-8")
                    if any(kw in content.lower() for kw in keywords):
                        # Find relevant paragraph
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if any(kw in line.lower() for kw in keywords):
                                chunk = "\n".join(lines[max(0, i-2):min(len(lines), i+3)])
                                formatted.append({
                                    "text": f"[Keyword Match in {md_file.name}]: {chunk}",
                                    "score": 0.5,
                                    "source": "file_scan"
                                })
                                if len(formatted) >= top_k: break
                    if len(formatted) >= top_k: break
            except Exception as e:
                logger.error(f"Keyword fallback failed: {e}")

        return formatted

    async def record_reflection(self, task: str, outcome: str, reflection: str = ""):
        """
        Store a self-journaled insight into the knowledge graph and mind_journal.md.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"\n## [{timestamp}] Task: {task}\n"
            f"**Outcome:** {outcome}\n"
            f"**Reflection:** {reflection}\n"
        )
        
        # 1. Update the persistent file
        journal_file = CONTEXT_DIR / "mind_journal.md"
        try:
            with open(journal_file, "a", encoding="utf-8") as f:
                f.write(entry)
            logger.info(f"Self-reflection recorded in {journal_file.name}")
        except Exception as e:
            logger.error(f"Failed to write reflection to file: {e}")

        # 2. Add to active memory
        await self.remember(entry, metadata={"type": "reflection", "task": task})

    async def forget(self, query: str):
        """Remove specific memories matching the query."""
        if not self._initialized:
            await self.initialize()

        normalized = (query or "").strip().lower()
        if not normalized:
            logger.warning("Forget skipped: empty query.")
            return

        try:
            import cognee
            if normalized in {"all", "*", "everything"}:
                await cognee.prune.prune_system() # Cognee 1.x prune API
                logger.warning("Pruned full memory graph via explicit forget-all request.")
                return

            # Cognee currently does not expose a stable selective-delete API here.
            logger.warning(
                "Selective forget is not supported by current Cognee bridge. "
                f"Requested query retained: '{query}'."
            )
        except Exception as e:
            logger.error(f"Forget failed: {e}")

    async def improve(self):
        """
        Consolidate and optimize the knowledge graph.
        Run this after batch operations (e.g., nightly learning).
        """
        if not self._initialized:
            await self.initialize()

        try:
            import cognee
            await cognee.cognify()
            logger.info("Knowledge graph improved/consolidated.")
        except Exception as e:
            logger.error(f"Improve failed: {e}")

    def recall_sync(self, query: str, top_k: int = 5) -> list[dict]:
        """Synchronous wrapper for recall."""
        try:
            return asyncio.run(self.recall(query, top_k))
        except Exception as e:
            logger.error(f"Sync recall error: {e}")
            return []

    def remember_sync(self, text: str, metadata: Optional[dict] = None):
        """
        NON-BLOCKING synchronous wrapper for remember.
        Pushes to a background thread to prevent JARVIS from hanging.
        """
        import threading
        def _bg_remember():
            try:
                asyncio.run(self.remember(text, metadata))
            except Exception as e:
                logger.error(f"Background memory error: {e}")
        
        threading.Thread(target=_bg_remember, daemon=True).start()
        logger.debug(f"Backgrounding memory storage for: {text[:50]}...")


# Singleton instance — import this in other modules
memory = JarvisMemory()
