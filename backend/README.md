# 后端服务

这是 AI 对话应用的 Django 后端 API，负责用户认证、设置管理、会话历史、消息持久化和 LangGraph Agent 调用。

## 目录结构

```text
backend/
├── ai/                         # LangGraph 编排层，不注册为 Django app
│   ├── tools/
│   │   ├── __init__.py
│   │   └── chat.py             # 当前用户会话、消息、设置工具
│   ├── context.py              # Agent 调用上下文
│   ├── graph.py                # StateGraph + ToolNode
│   ├── llms.py                 # OpenAI-compatible 模型客户端
│   ├── prompts.py              # 系统提示词
│   ├── document_readers.py      # Word/PDF 文本提取
│   └── runtime.py              # 统一 Agent 调用入口
├── apps/
│   ├── accounts/               # 注册、登录、设置、改密
│   └── chat/                   # 会话、消息、附件、AgentRun
├── config/                     # Django settings/urls/asgi/wsgi
├── manage.py
├── requirements.txt
└── requirements.lock
```

## 本地启动

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 8000
```

前端默认请求地址是：

```text
http://localhost:8000/api
```

## 常用命令

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 8000
```

## API 接口

- `POST /api/auth/register/`：注册
- `POST /api/auth/login/`：登录
- `POST /api/auth/logout/`：退出登录
- `GET /api/auth/me/`：获取当前用户
- `GET /api/settings/`：获取用户设置
- `PATCH /api/settings/`：更新用户设置
- `GET /api/conversations/`：获取会话列表
- `POST /api/conversations/`：创建会话
- `PATCH /api/conversations/{id}/`：更新会话
- `DELETE /api/conversations/{id}/`：删除会话
- `GET /api/conversations/{id}/messages/`：获取会话消息
- `POST /api/chat/send/`：发送消息并获取 AI 回复
- `POST /api/files/upload/`：上传附件

## 数据库

当前本地开发使用 SQLite：

```text
backend/db.sqlite3
```

生产环境建议迁移到 PostgreSQL。

## LangGraph Agent

当前 AI 调用链路：

```text
ChatView -> apps.chat.services.generate_assistant_reply()
         -> ai.runtime.invoke_chat_agent()
         -> ai.graph.build_chat_graph()
         -> DeepSeek-compatible LLM
         -> ai.tools.chat
         -> Django ORM
```

Agent 当前可调用的工具：

- `list_user_conversations`：读取当前登录用户最近的历史会话。
- `get_current_conversation_messages`：读取当前会话最近消息。
- `get_user_settings`：读取当前登录用户的设置。
- `read_current_conversation_documents`：读取当前会话最近上传的 Word/PDF 附件文本。
- `read_uploaded_document`：按附件 ID 读取当前会话中的 Word/PDF 附件文本。

工具全部在服务端绑定 `request.user` 和 `conversation`，不会信任前端传入的用户 ID。

文件读取依赖：

- `.docx`：`python-docx`
- `.pdf`：`pypdf`

扫描版 PDF 暂时只能返回空文本，后续需要接入 OCR。

## AI 回复配置

如果 `OPENAI_API_KEY` 为空，`/api/chat/send/` 会返回中文 fallback 回复，但仍然会保存用户消息、AI 消息和 `AgentRun` 记录。

如果使用 DeepSeek 这类 OpenAI-compatible 服务，需要同时配置 API 地址和模型名：

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
```

修改 `.env` 后需要重启后端服务。

## 代码约束

- 认证、会话归属和附件归属必须在服务端校验。
- `views.py` 只做入口层，复杂逻辑放在 `services.py` 或 `ai/`。
- `OPENAI_*` 配置只从后端环境读取，不从前端透传。
- 发送消息链路必须保持用户消息、AI 消息和 `AgentRun` 的完整落库。
- 修改模型、API、环境变量或 Agent 工具后，要同步更新 `backend/.env.example`、`docs/backend-contract.md` 和本文件。

## 验证命令

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
```

## 2026-05-20 安全加固

- 认证仍然使用 DRF token，但浏览器侧通过 HttpOnly Cookie 承载认证态；前端非只读请求需要同时携带 `X-CSRFToken`。
- 登录成功后后端会同时签发 `authToken` 和 `csrftoken`，登出与改密会清理两者。
- 管理后台权限边界已收紧：普通 `staff` 只能管理非特权账号，只有 `superuser` 可以修改 `is_staff` 和 `is_superuser`。
- 附件上传增加了服务端文件头和文档结构校验，文档解析失败会返回稳定业务错误，不再直接暴露底层解析器异常。
