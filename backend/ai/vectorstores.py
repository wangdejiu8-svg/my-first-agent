from dataclasses import dataclass
import math
import re

from django.conf import settings

from apps.chat.models import KnowledgeChunk, KnowledgeDocument


@dataclass(frozen=True)
class VectorSearchHit:
    chunk: KnowledgeChunk
    score: float
    vector_score: float
    lexical_match: bool


def search_chunks(
    *,
    owner,
    query_embedding,
    query_text="",
    prefer_lexical=False,
    conversation=None,
    attachment=None,
    embedding_backend=None,
    top_k=5,
):
    queryset = KnowledgeChunk.objects.select_related("attachment", "document").filter(
        owner=owner,
        document__index_status=KnowledgeDocument.STATUS_COMPLETED,
    )
    if conversation is not None:
        queryset = queryset.filter(conversation=conversation)
    if attachment is not None:
        queryset = queryset.filter(attachment=attachment)
    if embedding_backend:
        queryset = queryset.filter(document__embedding_backend=embedding_backend)

    hits = []
    for chunk in queryset:
        embedding = list(chunk.embedding_json or [])
        vector_score = cosine_similarity(query_embedding, embedding) if embedding else 0.0
        lexical_bonus, lexical_match = _score_lexical_match(chunk=chunk, query_text=query_text)
        if not _should_keep_chunk(
            vector_score=vector_score,
            lexical_match=lexical_match,
            prefer_lexical=prefer_lexical,
        ):
            continue
        score = _blend_scores(
            vector_score=vector_score,
            lexical_bonus=lexical_bonus,
            prefer_lexical=prefer_lexical,
        )
        hits.append(
            VectorSearchHit(
                chunk=chunk,
                score=score,
                vector_score=vector_score,
                lexical_match=lexical_match,
            )
        )

    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[: max(int(top_k or 5), 1)]


def cosine_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _should_keep_chunk(*, vector_score, lexical_match, prefer_lexical):
    if prefer_lexical:
        return lexical_match
    if vector_score <= 0:
        return False
    return vector_score >= settings.RAG_MIN_SCORE


def _blend_scores(*, vector_score, lexical_bonus, prefer_lexical):
    score = max(vector_score, 0.0)
    if lexical_bonus:
        weight = 1.0 if prefer_lexical else 0.55
        score += lexical_bonus * weight
    return min(score, 1.0)


def _score_lexical_match(*, chunk, query_text):
    normalized_query = _normalize_lexical_text(query_text)
    if not normalized_query:
        return 0.0, False

    chunk_text = str(chunk.text or "")
    attachment_name = str(chunk.attachment.original_name or "")
    normalized_chunk = _normalize_lexical_text(chunk_text)
    normalized_attachment = _normalize_lexical_text(attachment_name)

    bonus = 0.0
    matched = False

    if normalized_query in normalized_attachment:
        bonus += 0.22
        matched = True
    if normalized_query in normalized_chunk:
        bonus += 0.18
        matched = True
        if normalized_query in _normalize_lexical_text(chunk_text[:180]):
            bonus += 0.10
        occurrences = normalized_chunk.count(normalized_query)
        if occurrences > 1:
            bonus += min((occurrences - 1) * 0.03, 0.09)
        if chunk.chunk_index == 0:
            bonus += 0.05

    return min(bonus, 0.42), matched


def _normalize_lexical_text(text):
    return re.sub(r"\s+", "", str(text or "").lower())
