import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from ollama import AsyncClient

logger = logging.getLogger("jarvis.semantic_router")

class SemanticRouter:
    """
    Semantic Intent Router using local embeddings.
    Maps user speech to system intents by calculating cosine similarity 
    between the query embedding and pre-defined intent clusters.
    """
    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self.client = AsyncClient()
        self.threshold = 0.80  # Minimum similarity to trigger a skill
        
        # Define intent clusters with example phrases
        self.intents: Dict[str, List[str]] = {
            "GET_WEATHER": [
                "what is the weather like",
                "is it raining outside",
                "tell me the temperature",
                "weather forecast for today",
                "how is the climate in Mumbai"
            ],
            "PLAY_YOUTUBE": [
                "play some music on youtube",
                "open youtube and search for songs",
                "i want to watch a video of",
                "start playing",
                "youtube play"
            ],
            "GET_NEWS": [
                "what are the top headlines",
                "tell me the latest news",
                "anything interesting in the news today",
                "current events report",
                "news updates"
            ],
            "WEB_SEARCH": [
                "search google for",
                "find information about",
                "google search",
                "tell me about",
                "who is",
                "what is"
            ],
            "SYSTEM_STATUS": [
                "how are the systems looking",
                "run a system check",
                "show me the diagnostic report",
                "check server health",
                "are you fully operational"
            ],
            "TERMINAL_COMMAND": [
                "run a command in terminal",
                "execute bash script",
                "open terminal and",
                "debug the current folder",
                "create a new file named"
            ],
            "SHUTDOWN": [
                "deactivate all systems",
                "shut down",
                "go to sleep",
                "terminate session"
            ],
            "ENROLL_VOICE": [
                "start voice enrollment",
                "setup my voice print",
                "enroll my voice signature",
                "identify my voice",
                "voice setup"
            ],
            "IDENTIFY_ME": [
                "identify me",
                "who am i",
                "do you know who i am",
                "verify my identity",
                "who is speaking"
            ],
            "CODE_MODIFICATION": [
                "modify the code for",
                "add a new feature to the system",
                "create a new skill for",
                "edit the main logic",
                "change how you process commands",
                "update your source code"
            ],
            "DEBUG_SYSTEM": [
                "debug the enrollment process",
                "why is something not working",
                "troubleshoot the voice engine",
                "find bugs in the system",
                "fix the neural errors"
            ]
        }
        
        # Cache for intent embeddings
        self.intent_vectors: Dict[str, np.ndarray] = {}

    async def initialize(self):
        """Pre-compute embeddings for all intent examples."""
        logger.info(f"Initializing Semantic Router with model: {self.model}")
        try:
            for intent_name, examples in self.intents.items():
                vectors = []
                for example in examples:
                    resp = await self.client.embeddings(model=self.model, prompt=example)
                    vectors.append(resp['embedding'])
                
                # Store the centroid (mean vector) for the intent cluster
                self.intent_vectors[intent_name] = np.mean(vectors, axis=0)
            
            logger.info("Semantic Router initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Semantic Router: {e}")
            return False

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        return dot_product / (norm_v1 * norm_v2)

    async def route(self, query: str) -> Tuple[str, float]:
        """
        Routes the query to the best-matching intent.
        Returns (intent_name, score). Returns ('CONVERSATION', 0.0) if no match.
        """
        if not self.intent_vectors:
            # Fallback if not initialized
            return "CONVERSATION", 0.0

        try:
            # 1. Embed the query
            resp = await self.client.embeddings(model=self.model, prompt=query)
            query_vector = np.array(resp['embedding'])
            
            # 2. Find best match
            best_intent = "CONVERSATION"
            best_score = 0.0
            
            for intent_name, intent_vector in self.intent_vectors.items():
                score = self._cosine_similarity(query_vector, intent_vector)
                if score > best_score:
                    best_score = score
                    best_intent = intent_name
            
            if best_score < self.threshold:
                logger.info(f"Low confidence match ({best_score:.2f}) for '{best_intent}'. Falling back to Brain.")
                return "CONVERSATION", best_score
                
            logger.info(f"Detected intent: {best_intent} (Confidence: {best_score:.2f})")
            return best_intent, best_score

        except Exception as e:
            logger.error(f"Semantic Routing error: {e}")
            return "CONVERSATION", 0.0
