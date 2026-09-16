"""
Local Embedding service using sentence-transformers.
Uses 'all-MiniLM-L6-v2' for fast, local embedding generation.
"""
from typing import List
import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger(__name__)

class EmbeddingService:
    _instance = None
    _model = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name

    def _load_model(self):
        if self._model is None:
            logger.info("embedding.loading_model", model=self.model_name)
            self._model = SentenceTransformer(self.model_name)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts.
        Uses run_in_executor if necessary, but here we just call synchronously as
        it runs reasonably fast for all-MiniLM-L6-v2. For production, consider using asyncio.to_thread.
        """
        import asyncio
        self._load_model()
        
        def _encode():
            # Return as list of lists of floats
            return self._model.encode(texts, show_progress_bar=False).tolist()
            
        embeddings = await asyncio.to_thread(_encode)
        return embeddings

def get_embedder() -> EmbeddingService:
    return EmbeddingService.get_instance()
