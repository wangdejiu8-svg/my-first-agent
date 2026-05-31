from dataclasses import asdict, dataclass
from pathlib import Path
import re

from apps.chat.models import KnowledgeDocument, Message


FAST_SKIP_UPLOAD_PATTERN = re.compile(r"上传了\d+个文件")
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}")
EXPLICIT_DOCUMENT_PHRASES = (
    "这份文档",
    "这个文档",
    "附件里",
    "附件中",
    "文档里",
    "文件里",
    "文件中",
    "材料里",
    "上传的文件",
    "刚上传",
    "根据文档",
    "根据附件",
    "根据上面的文件",
    "根据上面的文档",
    "pdf里",
    "文档主要讲什么",
    "文档讲什么",
    "附件主要讲什么",
    "附件讲什么",
    "整理刚上传的内容",
    "总结刚上传的内容",
)
FOLLOW_UP_DOCUMENT_TERMS = ("上面", "这份", "刚上传", "上述")


@dataclass(frozen=True)
class RetrievalDecision:
    action: str
    relatedness: str
    reason: str
    router_label: str = ""
    probe_score: float | None = None
    probe_used: bool = False
    judge_used: bool = False
    decision_version: str = "v1-fast-probe"
    degraded_reason: str = ""

    def to_metadata(self):
        return asdict(self)


def decide_phase_one_retrieval(*, conversation, normalized_query, raw_query, skip_messages):
    if not normalized_query:
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="fast_skip_empty",
        )
    if normalized_query in skip_messages:
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="fast_skip_small_talk",
        )
    if FAST_SKIP_UPLOAD_PATTERN.fullmatch(normalized_query):
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="fast_skip_upload_notice",
        )

    knowledge_state = _build_knowledge_state(conversation=conversation)
    if not knowledge_state.has_documents:
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="no_completed_documents",
        )

    if _has_explicit_document_reference(raw_query):
        return RetrievalDecision(
            action="retrieve",
            relatedness="related",
            reason="explicit_document_reference",
        )
    if _query_overlaps_attachment_name(
        raw_query=raw_query,
        attachment_names=knowledge_state.attachment_names,
    ):
        return RetrievalDecision(
            action="retrieve",
            relatedness="related",
            reason="attachment_name_overlap",
        )
    if _looks_like_document_follow_up(
        raw_query=raw_query,
        recent_messages=knowledge_state.recent_messages,
    ):
        return RetrievalDecision(
            action="retrieve",
            relatedness="related",
            reason="document_follow_up",
        )

    return RetrievalDecision(
        action="probe",
        relatedness="uncertain",
        reason="conversation_has_documents",
        probe_used=True,
    )


def finalize_probe_decision(*, base_decision, probe_result):
    if not probe_result.top_hits:
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="probe_reject_no_hits",
            probe_used=True,
            probe_score=0.0,
            decision_version=base_decision.decision_version,
        )

    top_score = round(probe_result.top_score or 0.0, 4)
    if probe_result.top_score < 0.35 and not probe_result.has_lexical_match:
        return RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="probe_reject_low_signal",
            probe_used=True,
            probe_score=top_score,
            decision_version=base_decision.decision_version,
        )
    if probe_result.top_score >= 0.72 or (
        probe_result.top_score >= 0.5 and probe_result.has_lexical_match
    ):
        return RetrievalDecision(
            action="retrieve",
            relatedness="related" if probe_result.has_lexical_match else "uncertain",
            reason="probe_accept",
            probe_used=True,
            probe_score=top_score,
            decision_version=base_decision.decision_version,
        )
    return RetrievalDecision(
        action="skip",
        relatedness="uncertain",
        reason="probe_reject_mid_signal",
        probe_used=True,
        probe_score=top_score,
        decision_version=base_decision.decision_version,
    )


@dataclass(frozen=True)
class _KnowledgeState:
    has_documents: bool
    attachment_names: list[str]
    recent_messages: list[dict]


def _build_knowledge_state(*, conversation):
    queryset = (
        KnowledgeDocument.objects.filter(
            conversation=conversation,
            index_status=KnowledgeDocument.STATUS_COMPLETED,
        )
        .select_related("attachment")
        .order_by("-indexed_at", "-id")
    )
    attachment_names = [document.title for document in queryset]
    recent_messages = [
        {
            "role": role,
            "content": content,
            "metadata_json": metadata_json or {},
        }
        for role, content, metadata_json in conversation.messages.order_by("-created_at", "-id")
        .values_list("role", "content", "metadata_json")[:3]
    ]
    return _KnowledgeState(
        has_documents=bool(attachment_names),
        attachment_names=attachment_names,
        recent_messages=recent_messages,
    )


def _has_explicit_document_reference(raw_query):
    normalized = _normalize_phrase(raw_query)
    return any(phrase in normalized for phrase in EXPLICIT_DOCUMENT_PHRASES)


def _query_overlaps_attachment_name(*, raw_query, attachment_names):
    normalized_query = _normalize_phrase(raw_query)
    query_tokens = set(TOKEN_PATTERN.findall(normalized_query))
    if not normalized_query:
        return False

    for attachment_name in attachment_names:
        normalized_name = _normalize_phrase(Path(attachment_name).stem)
        if not normalized_name:
            continue
        if normalized_query in normalized_name or normalized_name in normalized_query:
            return True
        attachment_tokens = set(TOKEN_PATTERN.findall(normalized_name))
        if query_tokens and query_tokens.intersection(attachment_tokens):
            return True
    return False


def _looks_like_document_follow_up(*, raw_query, recent_messages):
    normalized = _normalize_phrase(raw_query)
    if not any(term in normalized for term in FOLLOW_UP_DOCUMENT_TERMS):
        return False

    for message in recent_messages:
        metadata = message.get("metadata_json") or {}
        if metadata.get("is_rag_answer"):
            return True
        if _has_explicit_document_reference(message.get("content") or ""):
            return True
        if message.get("role") == Message.ROLE_ASSISTANT and metadata.get("sources"):
            return True
    return False


def _normalize_phrase(text):
    return re.sub(r"\s+", "", str(text or "").lower()).strip()
