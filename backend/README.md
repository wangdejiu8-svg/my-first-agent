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
│   ├── chunking.py             # 文档切片
│   ├── embeddings.py           # embedding 抽象与本地 fallback
│   ├── retrieval.py            # 会话级检索与来源组装
│   ├── graph.py                # StateGraph + ToolNode
│   ├── llms.py                 # OpenAI-compatible 模型客户端
│   ├── prompts.py              # 系统提示词
│   ├── document_readers.py     # Word/PDF 文本提取
│   └── runtime.py              # 统一 Agent 调用入口
├── apps/
│   ├── accounts/               # 注册、登录、设置、改密
│   └── chat/                   # 会话、消息、附件、AgentRun、知识索引
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
- `POST /api/chat/send/`：发送消息并获取完整 AI 回复
- `POST /api/chat/send-stream/`：发送消息并以 NDJSON 流式返回 AI 回复增量
- `POST /api/files/upload/`：上传附件

## 数据库

当前本地开发使用 SQLite：

```text
backend/db.sqlite3
```

生产环境建议迁移到 PostgreSQL。

新增的 RAG 相关表：

- `KnowledgeDocument`：每个附件一条索引文档记录，带 `pending/processing/completed/failed` 状态。
- `KnowledgeChunk`：切片文本、元数据和向量。
- `RetrievalLog`：每次检索命中的 chunk 记录。

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
- `search_current_conversation_knowledge_tool`：检索当前会话内最相关的知识片段。
- `get_attachment_chunk_context`：检索当前会话内指定附件的相关片段。
- `read_current_conversation_documents`：读取当前会话最近上传的 Word/PDF 附件文本。
- `read_uploaded_document`：按附件 ID 读取当前会话中的 Word/PDF 附件文本。

工具全部在服务端绑定 `request.user` 和 `conversation`，不会信任前端传入的用户 ID。

文件读取依赖：

- `.docx`：`python-docx`
- `.pdf`：优先 `pypdf`，提取不到文本时回退 `pymupdf`

如果环境里可用 `tesseract` 或配置了 `TESSDATA_PREFIX`，扫描版 PDF 会继续尝试 OCR fallback；否则仍可能返回空文本。

## RAG MVP 说明

- 上传 `.docx` / `.pdf` 后会同步创建 `KnowledgeDocument` 并尝试索引。
- 索引流程是：解析文本 -> 固定长度 chunk -> 生成 embedding -> 保存 `KnowledgeChunk`。
- 有可用的 embedding 配置时优先调用远程 embedding；不可用时会退回本地哈希向量，保证 MVP 可运行。
- PDF 文本提取现在会按 `pypdf -> pymupdf -> OCR fallback` 的顺序尝试，减少“PDF 文件有效但提取不到文本”的情况。
- 消息发送时现在先走 Phase 1 检索 gate：`skip / retrieve / probe`。
- 明显寒暄/感谢/上传提示类短消息会直接 `skip`；明显文档引用或附件名重叠的消息会直接 `retrieve`；其余“当前会话有可用知识文档”的消息先做 `probe`。
- `probe` 与正式 `retrieve` 复用同一批 hits，避免同一轮消息重复 embedding / 重复扫描。
- 检索结果会应用 `RAG_MIN_SCORE` 阈值，低于阈值的弱相关 chunk 不进入 `used_chunks`。
- 对 `1-4` 个汉字或极短单 token 的短 query，检索层会额外要求词面命中；没有词面命中的结果不会进入 `used_chunks`，也不会显示 `Sources used`。
- assistant 消息会持久化 `sources`、`used_chunks`、`is_rag_answer`、`rag_score`，以及 `retrieval_decision` / `retrieval_reason` / `retrieval_relatedness` / `retrieval_probe_score` / `retrieval_decision_version`。
- `RetrievalLog` 现在还会记录本次决策的 metadata，便于后续评估误检索和 probe 效果。
- 索引失败不会影响附件保存，只会把文档状态标记为 `failed`。

## AI 回复配置

如果 `OPENAI_API_KEY` 为空，`/api/chat/send/` 和 `/api/chat/send-stream/` 都会返回 fallback 回复，但仍然会保存用户消息、AI 消息和 `AgentRun` 记录。

如果使用 DeepSeek 这类 OpenAI-compatible 服务，需要同时配置聊天模型的 API 地址和模型名：

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
OPENAI_EMBEDDING_API_KEY=你的向量密钥
OPENAI_EMBEDDING_BASE_URL=https://你的-embedding-服务
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=900
RAG_CHUNK_OVERLAP=120
RAG_TOP_K=5
RAG_MIN_SCORE=0.5
RAG_INDEX_MAX_CHARS=120000
PDF_OCR_LANGUAGE=auto
PDF_OCR_DPI=300
```

如果不填写 `OPENAI_EMBEDDING_API_KEY` / `OPENAI_EMBEDDING_BASE_URL`，embedding 会默认回退复用 `OPENAI_API_KEY` / `OPENAI_BASE_URL`。
如果要让扫描版 PDF 参与 OCR fallback，还需要在运行环境安装 `tesseract`，并根据文档语言准备对应语言包。

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
## 2026-05-20 RAG 修复

- 上传接口现在只创建 `KnowledgeDocument` 记录并返回 `knowledge_index_status` / `knowledge_index_error`，不再把文档解析和 embedding 阻塞在 `/api/files/upload/` 请求里。
- 当前会话第一次检索时会按需补索引 `pending` 或历史缺失的文档记录，避免老附件必须重新上传才能参与 RAG。
- 检索片段会作为用户消息里的非可信参考材料注入，明确禁止把文档内容当成系统指令执行。
- 查询阶段会按 `embedding_backend` 分组检索并合并结果，避免 OpenAI 向量和本地 hash 向量混用时静默失效。

## 2026-05-20 会话删除语义

- `DELETE /api/conversations/{id}/` 现在执行硬删除，不再只是写 `deleted_at`。
- 删除会话时会级联清理其 `Message`、`Attachment`、`AgentRun`、`KnowledgeDocument`、`KnowledgeChunk`、`RetrievalLog`。
- 关联附件文件也会从 `backend/media/` 中同步删除，避免磁盘残留孤儿文件。
## 2026-05-21 流式回复

- 新增 `POST /api/chat/send-stream/`，服务端会先落库用户消息、assistant 占位消息和 `AgentRun`，再把 assistant 文本以 NDJSON 增量推给前端。
- 前端消费 `start` / `delta` / `done` 事件，因此聊天区可以跟随 assistant 文本实时增长，而不是只能等整段回复结束后一次性显示。

## 2026-05-21 用户名校验一致性

- 注册、用户设置改名、管理员改名现在统一使用大小写敏感的用户名占用校验。
- 完全相同的用户名仍然会被拒绝，但 `anan` 和 `Anan` 会被视为两个不同用户名。

## 2026-05-25 RAG 检索收敛

- 服务层增加了轻量检索前置判断，明显寒暄、感谢、确认类短消息会直接跳过 RAG，避免“你好”“谢谢”这类消息也出现 `Sources used`。
- 新增 `RAG_MIN_SCORE` 配置项，默认 `0.5`，弱相关 chunk 不再进入 `used_chunks`。
- 检索层新增短 query 收紧和轻量混合复排：短 query 会放大候选池，再按 exact substring、附件名命中、前部命中、首块命中加权；无词面命中的短 query 结果会被直接拦下。
- assistant 消息现在会额外保存本次命中的实际 `rag_score`（当前为 `used_chunks` 里的最高分），前端会和来源区块一起展示。
- 当前会话没有 `completed` 索引时，检索层会直接返回空结果，不再白做一次 query embedding 计算。

## 2026-05-27 OCR 修复

- PDF OCR fallback 现在会优先按 `PDF_OCR_LANGUAGE=auto` 解析本机 `tesseract` 语言包；同时存在 `chi_sim` 和 `eng` 时，默认使用 `chi_sim+eng`，减少中文被英文模型识别成乱码的问题。
- OCR 提取现在固定使用 `PDF_OCR_DPI=300` 和整页 OCR，避免默认低分辨率导致的识别噪声。
- PyMuPDF 文本提取现在统一开启 `sort=True`，降低扫描 PDF OCR 后段落顺序错位的问题。
- 如果你的部署主要处理中文扫描件，建议显式配置 `PDF_OCR_LANGUAGE=chi_sim+eng`。

## 2026-05-31 Phase 1 Retrieval Gate

- 服务层现在已经从简单的“检索 / 不检索”二态，升级为 Phase 1 的 `skip / retrieve / probe`。
- 当前一期还没有接独立语义 router，也没有接 LLM judge；目标是先压住“会话里有附件就什么都查”的误检索。
- `probe` 阶段只基于现有检索分数和词面信号做接受/拒绝判断。
- 如果 gate 或 probe 失败，服务层会降级回旧的检索判断链路，不影响消息保存、AI 回复和 `AgentRun` 落库。
