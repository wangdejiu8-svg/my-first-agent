import hashlib
import math
import re

from django.conf import settings
from openai import OpenAI


LOCAL_EMBEDDING_DIMENSION = 256
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+")


def embed_text(text):
    return embed_texts([text])[0]


def embed_text_with_backend(text):
    embeddings, backend_name = embed_texts_with_backend([text])
    return embeddings[0], backend_name


def embed_texts(texts):
    normalized_texts = [str(text or "") for text in texts]
    if settings.OPENAI_EMBEDDING_API_KEY:
        try:
            return _embed_with_openai(normalized_texts)
        except Exception:
            # Keep MVP available even when the remote embedding backend is flaky.
            pass
    return [_embed_with_hashing(text) for text in normalized_texts]


def get_embedding_backend_name():
    return "openai" if settings.OPENAI_EMBEDDING_API_KEY else "local-hash"


def get_available_embedding_backends():
    backends = ["local-hash"]
    if settings.OPENAI_EMBEDDING_API_KEY:
        backends.insert(0, "openai")
    return backends


def embed_texts_with_backend(texts):
    normalized_texts = [str(text or "") for text in texts]
    if settings.OPENAI_EMBEDDING_API_KEY:
        try:
            return _embed_with_openai(normalized_texts), "openai"
        except Exception:
            pass
    return [_embed_with_hashing(text) for text in normalized_texts], "local-hash"


def embed_texts_for_backend(texts, backend_name):
    normalized_texts = [str(text or "") for text in texts]
    if backend_name == "openai":
        if not settings.OPENAI_EMBEDDING_API_KEY:
            raise RuntimeError("OPENAI_EMBEDDING_API_KEY is not configured for openai embeddings.")
        return _embed_with_openai(normalized_texts)
    if backend_name == "local-hash":
        return [_embed_with_hashing(text) for text in normalized_texts]
    raise ValueError(f"Unsupported embedding backend: {backend_name}")


def _embed_with_openai(texts):
    client_kwargs = {"api_key": settings.OPENAI_EMBEDDING_API_KEY}
    if settings.OPENAI_EMBEDDING_BASE_URL:
        client_kwargs["base_url"] = settings.OPENAI_EMBEDDING_BASE_URL

    client = OpenAI(**client_kwargs)
    response = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [list(item.embedding) for item in response.data]


def _embed_with_hashing(text):
    vector = [0.0] * LOCAL_EMBEDDING_DIMENSION
    for token in TOKEN_PATTERN.findall((text or "").lower()):
        bucket = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % LOCAL_EMBEDDING_DIMENSION
        vector[bucket] += 1.0
    return _normalize(vector)


def _normalize(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]
