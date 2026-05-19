import time
import uuid

from django.conf import settings

from ai.runtime import invoke_chat_agent

from .models import AgentRun


def generate_assistant_reply(conversation, user, user_content):
    started_at = time.perf_counter()
    model = settings.OPENAI_MODEL
    status = "langgraph_completed"
    error = ""

    try:
        reply = invoke_chat_agent(
            user=user,
            conversation=conversation,
            request_id=str(uuid.uuid4()),
        )
    except Exception as exc:
        status = "fallback"
        error = str(exc)
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
    return reply


def _build_fallback_reply(exc):
    message = str(exc)
    if "reasoning_content" in message or "thinking mode" in message:
        return "消息已保存，但模型推理模式兼容失败。已为 DeepSeek 关闭 thinking mode 后再试。"
    if "OPENAI_API_KEY" in message:
        return "消息已保存，但后端未配置 API Key。请检查 `backend/.env`。"
    return "消息已保存，但 AI 调用失败，请稍后重试。"
