# Django + LangGraph AI Agent 后端架构实施规范

本文档基于 `django-ai-agent` 的实际实现整理，但目标不是复述教程，而是提供一份可迁移、可实施、可交给 AI 执行的后端架构规格。

适用场景：

- 在现有 Django 项目中接入 AI Agent。
- 新建 Django 后端，并用 LangGraph 编排 Agent。
- 希望 AI 按文档直接生成可运行骨架，而不是只写概念代码。

---

## 一、目标

第一版必须满足 4 个目标：

1. Django 仍然是业务数据的唯一权威来源。
2. AI 只能通过工具访问数据，不能绕过权限直接操作模型。
3. 用户上下文必须贯穿 Agent 调用链路。
4. 同一套模式可以复用到别的业务域，而不只适用于“文档 + 电影”示例。

非目标：

- 向量数据库
- 前端页面
- 复杂工作流平台
- 私有模型训练

---

## 二、核心原则

### 1. Django 负责数据与业务规则

- 模型、迁移、事务、认证体系由 Django 承担。
- Agent 不是系统主干，只是一个受控入口。

### 2. LangGraph 负责编排，不负责权限

- LangGraph 用来组合 Agent、工具和记忆。
- 真正的权限检查必须发生在工具层和查询层。

### 3. 工具是唯一的数据访问入口

- Agent 读写业务数据时，必须走 `ai/tools/`。
- 不允许在 Agent 定义里直接操作 Django Model。

### 4. 权限必须覆盖全局权限和对象权限

- “能不能查看 document” 与 “能不能查看 document:123” 不是一回事。
- 列表、搜索、详情、创建、更新、删除都要分别定义动作。

---

## 三、推荐目录结构

```text
src/
├── manage.py
├── .env.sample
├── cfehome/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── documents/
│   ├── apps.py
│   ├── admin.py
│   ├── models.py
│   ├── services.py
│   ├── queries.py
│   ├── api.py
│   ├── tests.py
│   └── migrations/
├── ai/
│   ├── llms.py
│   ├── context.py
│   ├── agents.py
│   ├── supervisors.py
│   ├── runtime.py
│   └── tools/
│       ├── __init__.py
│       ├── documents.py
│       └── movie_discovery.py
├── mypermit/
│   └── client.py
└── tmdb/
    └── client.py
```

说明：

- `documents` 是 Django app。
- `ai` 是普通 Python package，不一定要注册到 `INSTALLED_APPS`。
- `api.py` 提供 HTTP 入口。
- `runtime.py` 统一组装 graph、checkpointer、配置注入。

---

## 四、运行前提与版本约束

### 1. Python

当前参考仓库在 Python `3.14.0` 下出现了 `permit` 导入异常，因此不应把 Python 3.14 当作默认可用环境。

实施要求：

- 第一版建议固定 Python `3.11` 或 `3.12`。
- 在配置文件和部署文档里写明版本范围。

### 2. 依赖

最小依赖：

```txt
Django>=5.0,<6.0
jupyter
langchain-openai
langgraph
langgraph-supervisor
python-decouple
permit
requests
```

实施要求：

- 不能只保留裸 `requirements.txt`。
- 必须补一份锁文件，例如 `requirements.lock`。

### 3. 环境变量

`.env.sample` 至少包含：

```env
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
TMDB_API_KEY=your_tmdb_api_key
PERMIT_API_KEY=your_permit_api_key
PERMIT_PDP_URL=https://cloudpdp.api.permit.io
```

---

## 五、Django 基础配置

`settings.py` 至少需要：

```python
from decouple import config
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "documents",
]

OPENAI_API_KEY = config("OPENAI_API_KEY", default=None)
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")
TMDB_API_KEY = config("TMDB_API_KEY", default=None)
PERMIT_API_KEY = config("PERMIT_API_KEY", default=None)
PERMIT_PDP_URL = config("PERMIT_PDP_URL", default="https://cloudpdp.api.permit.io")
```

本地开发可用 SQLite，生产环境建议 PostgreSQL。

---

## 六、核心数据模型

第一版的 `Document` 需要支持用户归属、软删除、时间戳和查询复用：

```python
from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class DocumentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True)

    def owned_by(self, user_id):
        return self.filter(owner_id=user_id)


class Document(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=120, default="Untitled")
    content = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    active_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DocumentQuerySet.as_manager()

    def save(self, *args, **kwargs):
        self.active_at = (self.active_at or timezone.now()) if self.active else None
        super().save(*args, **kwargs)

    def soft_delete(self):
        self.active = False
        self.save(update_fields=["active", "active_at", "updated_at"])
```

实施要求：

- `CharField` 必须显式设置 `max_length`。
- 如果文档声称是软删除，删除工具就不能直接 `obj.delete()`。

---

## 七、用户上下文与调用契约

Agent 调用必须采用统一 `config` 结构：

```python
config = {
    "configurable": {
        "user_id": "42",
        "thread_id": "session-3b4e1c9c",
        "request_id": "req-7f8a",
    },
    "metadata": {
        "source": "api",
    },
}
```

硬要求：

- `user_id` 必填。
- `thread_id` 必填。
- `user_id` 必须来自 Django 已认证用户。
- 服务端必须校验 `thread_id`，不能完全信任客户端。

建议统一封装在 `ai/context.py`：

```python
from dataclasses import dataclass


@dataclass
class AgentContext:
    user_id: str
    thread_id: str
    request_id: str | None = None


def get_agent_context(config):
    config = config or {}
    configurable = config.get("configurable") or {}
    user_id = configurable.get("user_id")
    thread_id = configurable.get("thread_id")

    if not user_id:
        raise ValueError("Missing user_id")
    if not thread_id:
        raise ValueError("Missing thread_id")

    return AgentContext(
        user_id=str(user_id),
        thread_id=str(thread_id),
        request_id=configurable.get("request_id"),
    )
```

---

## 八、权限模型

### 1. 动作定义

对 `document` 资源至少定义：

- `list`
- `search`
- `read`
- `create`
- `update`
- `delete`

### 2. 查询隔离规则

这是实施硬要求：

- `list_documents` 只能返回当前用户自己的文档。
- `search_documents` 只能搜索当前用户自己的文档。
- `get_document`、`update_document`、`delete_document` 必须同时做对象查询隔离和对象级权限判断。

下面这种查询不能作为通用实现：

```python
Document.objects.filter(active=True)
```

它缺少用户隔离，容易造成跨用户数据暴露。

### 3. Permit 客户端

不要在模块导入时直接实例化全局客户端。建议延迟加载：

```python
from functools import lru_cache
from django.conf import settings
from permit import Permit


@lru_cache(maxsize=1)
def get_permit_client():
    if not settings.PERMIT_API_KEY:
        raise ValueError("PERMIT_API_KEY was not set.")
    return Permit(
        pdp=settings.PERMIT_PDP_URL,
        token=settings.PERMIT_API_KEY,
    )
```

这样可以减少导入阶段因为环境变量或 SDK 问题导致整个 `ai` 包无法加载。

---

## 九、LLM、Agent 与工具

### 1. LLM 工厂

```python
from django.conf import settings
from langchain_openai import ChatOpenAI


def get_openai_model(model=None):
    model_name = model or settings.OPENAI_MODEL
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY was not set.")
    return ChatOpenAI(
        model=model_name,
        temperature=0,
        max_retries=2,
        api_key=settings.OPENAI_API_KEY,
    )
```

### 2. Agent 划分

- `document-assistant`：处理文档 CRUD 与搜索。
- `movie-discovery-assistant`：处理 TMDB 查询。
- `supervisor`：只负责路由，不直接操作业务数据。

### 3. 工具实现要求

- 每个工具都要解析统一上下文。
- 每个工具都要做权限检查。
- 每个工具都要做查询隔离。
- 每个工具都要返回结构化数据。
- `config` 不要写成可变默认值。

文档工具参考实现：

```python
from asgiref.sync import async_to_sync
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from django.db.models import Q

from ai.context import get_agent_context
from documents.models import Document
from mypermit.client import get_permit_client


@tool
def list_documents(limit: int = 5, config: RunnableConfig | None = None):
    ctx = get_agent_context(config)
    limit = min(max(limit, 1), 25)

    permit = get_permit_client()
    if not async_to_sync(permit.check)(ctx.user_id, "list", "document"):
        raise PermissionError("No permission to list documents.")

    qs = (
        Document.objects.active()
        .owned_by(ctx.user_id)
        .order_by("-created_at")[:limit]
    )
    return [{"id": obj.id, "title": obj.title} for obj in qs]


@tool
def search_documents(query: str, limit: int = 5, config: RunnableConfig | None = None):
    ctx = get_agent_context(config)
    limit = min(max(limit, 1), 25)

    permit = get_permit_client()
    if not async_to_sync(permit.check)(ctx.user_id, "search", "document"):
        raise PermissionError("No permission to search documents.")

    qs = (
        Document.objects.active()
        .owned_by(ctx.user_id)
        .filter(Q(title__icontains=query) | Q(content__icontains=query))
        .order_by("-created_at")[:limit]
    )
    return [{"id": obj.id, "title": obj.title} for obj in qs]
```

---

## 十、第三方 API 集成

`TMDB` 只是示例，重点在模式：

- 外部 API 必须放在独立客户端模块。
- 工具层只调用客户端，不直接写网络请求。
- 客户端必须设置超时并处理错误。

示例：

```python
import requests
from django.conf import settings


def search_movie(query: str, page: int = 1):
    response = requests.get(
        "https://api.themoviedb.org/3/search/movie",
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {settings.TMDB_API_KEY}",
        },
        params={"query": query, "page": page, "include_adult": False, "language": "en-US"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
```

---

## 十一、API 入口

参考仓库更像 notebook 教学项目，不是完整服务。迁移到另一个项目时，必须补上 HTTP 入口。

推荐接口：

`POST /api/agent/chat`

请求体：

```json
{
  "messages": [{"role": "user", "content": "列出我最近的 5 条文档"}],
  "thread_id": "session-3b4e1c9c",
  "agent": "supervisor"
}
```

服务端流程：

1. 校验 Django 登录态或 API Token。
2. 从 `request.user` 提取真实用户 ID。
3. 生成或校验 `thread_id`。
4. 组装 LangGraph `config`。
5. 选择 graph 并执行 `invoke()`。
6. 返回结果与 `thread_id`。

伪代码：

```python
import uuid
from django.http import JsonResponse

from ai.runtime import get_chat_graph


def agent_chat_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Unauthorized"}, status=401)

    payload = request.json()
    thread_id = payload.get("thread_id") or f"session-{uuid.uuid4()}"
    graph = get_chat_graph(agent_name=payload.get("agent") or "supervisor")

    config = {
        "configurable": {
            "user_id": str(request.user.id),
            "thread_id": thread_id,
            "request_id": str(uuid.uuid4()),
        },
        "metadata": {"source": "api"},
    }

    result = graph.invoke({"messages": payload.get("messages") or []}, config=config)
    return JsonResponse({"thread_id": thread_id, "result": result})
```

---

## 十二、记忆与 Runtime

开发环境可以使用 `InMemorySaver`，生产环境不能只用内存 checkpointer。

建议统一在 `ai/runtime.py` 中组装 graph：

```python
from langgraph.checkpoint.memory import InMemorySaver

from ai.agents import get_document_agent, get_movie_discovery_agent
from ai.supervisors import get_supervisor


_checkpointer = InMemorySaver()


def get_chat_graph(agent_name="supervisor"):
    if agent_name == "document":
        return get_document_agent(checkpointer=_checkpointer)
    if agent_name == "movie":
        return get_movie_discovery_agent(checkpointer=_checkpointer)
    return get_supervisor(checkpointer=_checkpointer)
```

硬要求：

- 不要把 graph 实例化逻辑散落在 notebook、view 和脚本里。
- 生产环境必须替换成持久化 checkpointer。

---

## 十三、实施步骤

1. 初始化 Django 项目与 `documents` app。
2. 安装依赖并生成锁文件。
3. 补全 `.env`。
4. 实现 `Document` 模型并执行迁移。
5. 实现 `ai/context.py` 与 `mypermit/client.py`。
6. 实现 `ai/tools/` 下的文档与第三方 API 工具。
7. 实现 `ai/llms.py`、`ai/agents.py`、`ai/supervisors.py`、`ai/runtime.py`。
8. 暴露 `POST /api/agent/chat`。
9. 编写测试并做端到端冒烟验证。

---

## 十四、测试与验收标准

最低验收要求：

- `python manage.py check` 通过。
- `python manage.py test` 通过。
- 导入 `ai.agents`、`ai.supervisors`、`ai.tools.documents` 不报错。
- 未配置关键环境变量时，错误信息可读。
- 不存在跨用户数据泄露。

必须覆盖的测试：

- `test_list_documents_only_returns_current_users_documents`
- `test_get_document_denies_access_to_other_users_document`
- `test_delete_document_uses_soft_delete`
- `test_agent_chat_injects_authenticated_user_context`
- `test_supervisor_can_route_to_document_agent`

---

## 十五、给 AI 执行时的硬约束

如果把本文档直接交给 AI 生成代码，建议同时附带以下约束：

1. 不允许省略 API 入口。
2. 不允许省略测试。
3. 不允许在列表或搜索查询中缺少用户隔离。
4. 不允许把删除实现成硬删除，除非业务明确要求。
5. 不允许把 Permit 客户端写成导入即初始化的全局副作用。
6. 不允许只交付 notebook 演示，不交付后端服务入口。

---

## 十六、总结

这套架构真正可复用的核心链路是：

`认证用户 -> 服务端注入上下文 -> Agent -> 工具 -> 权限检查 -> Django ORM -> 结构化结果`

只要这条链路稳定，你就可以把当前的“文档助手 + 电影助手”扩展为任意领域型 AI 后端。

如果要迁移到另一个项目，最重要的不是先加更多 Agent，而是先确保以下 4 点已经成立：

1. API 入口明确。
2. 用户隔离明确。
3. 权限模型明确。
4. 测试与版本边界明确。
