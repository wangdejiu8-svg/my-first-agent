import re
import time
import uuid
from dataclasses import dataclass, field

from django.conf import settings

from ai.retrieval import (
    RetrievalResult,
    log_retrieval_event,
    probe_current_conversation_knowledge,
    search_current_conversation_knowledge,
)
from ai.retrieval_gate import RetrievalDecision, decide_phase_one_retrieval, finalize_probe_decision
from ai.runtime import invoke_chat_agent, invoke_chat_agent_stream

from .models import AgentRun


RETRIEVAL_SKIP_MESSAGES = {
    "hi",
    "hello",
    "helloagain",
    "ok",
    "okay",
    "thanks",
    "thankyou",
    "你好",
    "您好",
    "在吗",
    "在么",
    "收到",
    "好的",
    "谢谢",
    "谢谢你",
    "谢了",
    "早上好",
    "中午好",
    "下午好",
    "晚上好",
    "晚安",
    "再见",
    "拜拜",
    "继续",
    "继续吧",
}


@dataclass(frozen=True)
class AssistantReply:
    content: str
    metadata: dict = field(default_factory=dict)
    status: str = "langgraph_completed"
    error: str = ""


@dataclass(frozen=True)
class RetrievalEnvelope:
    result: RetrievalResult
    decision: RetrievalDecision


def generate_assistant_reply(conversation, user, user_content):
    started_at = time.perf_counter()
    model = settings.OPENAI_MODEL
    status = "langgraph_completed"
    error = ""
    metadata = _empty_rag_metadata()

    try:
        retrieval_envelope = _get_retrieval_result(
            conversation=conversation,
            user=user,
            user_content=user_content,
        )
        retrieval_result = retrieval_envelope.result
        metadata = _build_reply_metadata(
            retrieval_result=retrieval_result,
            decision=retrieval_envelope.decision,
        )
        reply = invoke_chat_agent(
            user=user,
            conversation=conversation,
            request_id=str(uuid.uuid4()),
            retrieval_reference_block=retrieval_result.build_reference_block(),
        )
    except Exception as exc:
        status = "fallback"
        error = str(exc)
        metadata = _empty_rag_metadata()
        reply = _build_fallback_reply(exc)

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    AgentRun.objects.create(
        owner=user,
        conversation=conversation,
        request=user_content,
        response=reply,
        model=model,
        status=status,
        error=error,
        latency_ms=latency_ms,
    )
    return AssistantReply(
        content=reply,
        metadata=metadata,
        status=status,
        error=error,
    )


def generate_assistant_reply_stream(conversation, user, user_content):
    status = "langgraph_completed"
    error = ""
    metadata = _empty_rag_metadata()
    chunks = []

    try:
        retrieval_envelope = _get_retrieval_result(
            conversation=conversation,
            user=user,
            user_content=user_content,
        )
        retrieval_result = retrieval_envelope.result
        metadata = _build_reply_metadata(
            retrieval_result=retrieval_result,
            decision=retrieval_envelope.decision,
        )
        for chunk in invoke_chat_agent_stream(
            user=user,
            conversation=conversation,
            request_id=str(uuid.uuid4()),
            retrieval_reference_block=retrieval_result.build_reference_block(),
        ):
            if chunk:
                chunks.append(chunk)
                yield chunk
        reply = "".join(chunks)
    except Exception as exc:
        status = "fallback"
        error = str(exc)
        metadata = _empty_rag_metadata()
        reply = _build_fallback_reply(exc)
        for chunk in _split_text_for_stream(reply):
            yield chunk

    return AssistantReply(
        content=reply,
        metadata=metadata,
        status=status,
        error=error,
    )


def _get_retrieval_result(*, conversation, user, user_content):
    try:
        decision = decide_phase_one_retrieval(
            conversation=conversation,
            normalized_query=_normalize_retrieval_message(user_content),
            raw_query=user_content,
            skip_messages=RETRIEVAL_SKIP_MESSAGES,
        )
        return _execute_retrieval_decision(
            decision=decision,
            conversation=conversation,
            user=user,
            user_content=user_content,
        )
    except Exception as exc:
        return _get_legacy_retrieval_result(
            conversation=conversation,
            user=user,
            user_content=user_content,
            degraded_reason=f"phase1_gate_failed:{exc.__class__.__name__}",
        )


def _execute_retrieval_decision(*, decision, conversation, user, user_content):
    if decision.action == "skip":
        _log_skip_decision(
            decision=decision,
            conversation=conversation,
            user=user,
            user_content=user_content,
        )
        return RetrievalEnvelope(
            result=RetrievalResult(used_chunks=[], sources=[]),
            decision=decision,
        )

    if decision.action == "retrieve":
        retrieval_result = search_current_conversation_knowledge(
            user=user,
            conversation=conversation,
            query=user_content,
            top_k=settings.RAG_TOP_K,
            log_metadata=decision.to_metadata(),
        )
        return RetrievalEnvelope(result=retrieval_result, decision=decision)

    try:
        probe_result = probe_current_conversation_knowledge(
            user=user,
            conversation=conversation,
            query=user_content,
            top_k=settings.RAG_TOP_K,
        )
    except Exception as exc:
        return _get_legacy_retrieval_result(
            conversation=conversation,
            user=user,
            user_content=user_content,
            degraded_reason=f"phase1_probe_failed:{exc.__class__.__name__}",
        )

    final_decision = finalize_probe_decision(
        base_decision=decision,
        probe_result=probe_result,
    )
    if final_decision.action == "retrieve":
        retrieval_result = search_current_conversation_knowledge(
            user=user,
            conversation=conversation,
            query=user_content,
            top_k=settings.RAG_TOP_K,
            search_execution=probe_result.search_execution,
            log_metadata=final_decision.to_metadata(),
        )
        return RetrievalEnvelope(result=retrieval_result, decision=final_decision)

    _log_skip_decision(
        decision=final_decision,
        conversation=conversation,
        user=user,
        user_content=user_content,
    )
    return RetrievalEnvelope(
        result=RetrievalResult(used_chunks=[], sources=[]),
        decision=final_decision,
    )


def _get_legacy_retrieval_result(*, conversation, user, user_content, degraded_reason):
    normalized = _normalize_retrieval_message(user_content)
    if not _should_retrieve_for_message(user_content):
        decision = RetrievalDecision(
            action="skip",
            relatedness="unrelated",
            reason="legacy_skip",
            decision_version="legacy-fallback",
            degraded_reason=degraded_reason,
        )
        _log_skip_decision(
            decision=decision,
            conversation=conversation,
            user=user,
            user_content=user_content,
        )
        return RetrievalEnvelope(
            result=RetrievalResult(used_chunks=[], sources=[]),
            decision=decision,
        )

    decision = RetrievalDecision(
        action="retrieve",
        relatedness="uncertain" if normalized else "unrelated",
        reason="legacy_retrieve",
        decision_version="legacy-fallback",
        degraded_reason=degraded_reason,
    )
    retrieval_result = search_current_conversation_knowledge(
        user=user,
        conversation=conversation,
        query=user_content,
        top_k=settings.RAG_TOP_K,
        log_metadata=decision.to_metadata(),
    )
    return RetrievalEnvelope(result=retrieval_result, decision=decision)


def _log_skip_decision(*, decision, conversation, user, user_content):
    try:
        log_retrieval_event(
            user=user,
            conversation=conversation,
            query=user_content,
            top_k=0,
            matched_chunk_ids=[],
            metadata=decision.to_metadata(),
        )
    except Exception:
        return


def _should_retrieve_for_message(user_content):
    normalized = _normalize_retrieval_message(user_content)
    if not normalized:
        return False
    if normalized in RETRIEVAL_SKIP_MESSAGES:
        return False
    return not bool(re.fullmatch(r"上传了\d+个文件", normalized))


def _normalize_retrieval_message(user_content):
    normalized = re.sub(r"[\W_]+", "", str(user_content or "").lower())
    return normalized.strip()


def _empty_rag_metadata():
    return {
        "sources": [],
        "used_chunks": [],
        "is_rag_answer": False,
        "rag_score": None,
        "retrieval_decision": "skip",
        "retrieval_reason": "fallback",
        "retrieval_router_label": "",
        "retrieval_relatedness": "unrelated",
        "retrieval_probe_score": None,
        "retrieval_judge_used": False,
        "retrieval_decision_version": "fallback",
    }


def _build_reply_metadata(*, retrieval_result, decision):
    return {
        "sources": retrieval_result.sources,
        "used_chunks": retrieval_result.used_chunks,
        "is_rag_answer": retrieval_result.is_rag_answer,
        "rag_score": retrieval_result.rag_score,
        "retrieval_decision": decision.action,
        "retrieval_reason": decision.reason,
        "retrieval_router_label": decision.router_label,
        "retrieval_relatedness": decision.relatedness,
        "retrieval_probe_score": decision.probe_score,
        "retrieval_judge_used": decision.judge_used,
        "retrieval_decision_version": decision.decision_version,
    }


def _build_fallback_reply(exc):
    message = str(exc)
    if "reasoning_content" in message or "thinking mode" in message:
        return "消息已保存，但模型推理模式兼容失败。已在 DeepSeek 关闭 thinking mode 后再试。"
    if "OPENAI_API_KEY" in message:
        return "消息已保存，但后端未配置 API Key。请检查 `backend/.env`。"
    return "消息已保存，但 AI 调用失败，请稍后重试。"

def _split_text_for_stream(text, chunk_size=18):
    normalized = str(text or "")
    if not normalized:
        return []
    return [
        normalized[index:index + chunk_size]
        for index in range(0, len(normalized), chunk_size)
    ]
