from sentence_transformers import SentenceTransformer
from app.config import settings


_models: dict[str, SentenceTransformer] = {}


def _get_model() -> SentenceTransformer:
    if settings.embedding_model not in _models:
        _models[settings.embedding_model] = SentenceTransformer(settings.embedding_model)
    return _models[settings.embedding_model]


class EmbeddingClient:
    def __init__(self):
        self._model = _get_model()
        self._dim = self._model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        return self._model.encode(text).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, show_progress_bar=False).tolist()
