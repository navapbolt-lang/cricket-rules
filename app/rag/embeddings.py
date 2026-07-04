"""Embedding client using Gemini API (no local model needed)."""

from app.config import settings


class EmbeddingClient:
    """Embedding client using Gemini API for embeddings."""

    def __init__(self):
        self._dim = 768  # Gemini embedding dimension

    def embed(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
            )
            return result["embedding"]
        except Exception as e:
            # Fallback: return zero vector (will degrade search quality)
            print(f"Embedding API failed: {e}")
            return [0.0] * self._dim

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts."""
        return [self.embed(text) for text in texts]
