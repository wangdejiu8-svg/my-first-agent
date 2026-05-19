from django.conf import settings
from langchain_openai import ChatOpenAI


def get_chat_model():
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 未配置。")

    kwargs = {
        "model": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
        "temperature": 0.2,
        "max_retries": 2,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    if _is_deepseek_backend():
        # DeepSeek enables thinking mode by default. In the current LangGraph tool
        # loop this can trigger 400 errors that require reasoning_content to be
        # echoed back on follow-up calls, so disable thinking explicitly.
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    return ChatOpenAI(**kwargs)


def _is_deepseek_backend():
    base_url = (settings.OPENAI_BASE_URL or "").lower()
    model = (settings.OPENAI_MODEL or "").lower()
    return "deepseek" in base_url or model.startswith("deepseek")
