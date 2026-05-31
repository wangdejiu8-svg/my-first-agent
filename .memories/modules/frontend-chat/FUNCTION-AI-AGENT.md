# LangGraph Agent 实现

## 当前状态

后端已经按架构文档拆出独立 AI 编排层：`backend/ai/`。它不是 Django app，不注册到 `INSTALLED_APPS`，只作为普通 Python 包被业务服务调用。

## 目录结构

```text
backend/ai/
├── __init__.py
├── context.py          # 构造 LangGraph config，注入 user_id/conversation_id/thread_id
├── chunking.py         # 文档切片
├── embeddings.py       # embedding 抽象，远程失败时可退回本地哈希向量
├── retrieval.py        # 会话级 top-k 检索与来源组装
├── graph.py            # StateGraph、assistant 节点和 ToolNode
├── llms.py             # ChatOpenAI 客户端，支持 DeepSeek OpenAI-compatible API
├── prompts.py          # 中文系统提示词，避免自称 GPT
├── document_readers.py # Word/PDF 文本提取
├── runtime.py          # invoke_chat_agent 统一入口
└── tools/
    ├── __init__.py
    └── chat.py         # 当前用户会话、当前会话消息、用户设置工具
```

## 调用链路

```text
POST /api/chat/send/
-> ChatSendView
-> generate_assistant_reply()
-> ai.runtime.invoke_chat_agent()
-> LangGraph StateGraph
-> assistant node
-> ToolNode
-> ai.tools.chat
-> Django ORM
```

## 工具边界

当前工具全部由服务端闭包绑定 `request.user` 和 `conversation`，模型不能自己传入 `user_id` 越权查询。

已实现工具：

- `list_user_conversations(limit=5)`
- `get_current_conversation_messages(limit=10)`
- `get_user_settings()`
- `search_current_conversation_knowledge_tool(query, top_k=5)`：按 `owner + conversation` 检索最相关 chunk。
- `get_attachment_chunk_context(attachment_id, query, top_k=5)`：检索指定附件的相关 chunk。
- `read_current_conversation_documents(limit=3)`：读取当前会话最近上传的 Word/PDF 附件文本。
- `read_uploaded_document(attachment_id)`：按附件 ID 精确读取 Word/PDF 附件文本。

## 文件读取能力

第一版文件工具支持：

- `.docx`：使用 `python-docx` 提取段落和表格文本。
- `.pdf`：优先使用 `pypdf`，提取不到文本时回退 `pymupdf`。
- 单次读取最多返回前 `12000` 个字符，避免工具结果过大。
- 工具只读取当前登录用户、当前会话下的附件，不能跨用户或跨会话读取。

注意：扫描版 PDF 会在环境具备 `tesseract` 或 `TESSDATA_PREFIX` 时继续尝试 OCR；如果环境没有 OCR 能力，工具仍可能返回“没有提取到可读文本”。

## 2026-05-20 RAG MVP 更新

- 上传附件后会同步创建 `KnowledgeDocument` 并尝试索引。
- 索引流程是：全文解析 -> 固定长度切片 -> embedding -> `KnowledgeChunk` 持久化。
- 发送消息时，服务层会先做当前会话内检索，再把检索结果注入 LangGraph 上下文。
- assistant 消息会持久化 `sources`、`used_chunks`、`is_rag_answer`、`rag_score`，前端刷新历史后仍能看到来源和本次检索分数。
- 如果远程 embedding 不可用，会退回本地哈希向量；如果聊天模型不可用，仍保留原有 fallback 回复。

## 2026-05-25 RAG 检索收敛

- `backend/apps/chat/services.py` 增加了检索前置判断，明显寒暄、感谢、确认类短消息会直接跳过检索。
- `backend/config/settings.py` 新增 `RAG_MIN_SCORE`，默认 `0.5`。
- `backend/ai/vectorstores.py` 会过滤低于 `RAG_MIN_SCORE` 的 chunk，避免弱相关片段进入 `used_chunks`。
- `backend/ai/retrieval.py` 在当前会话没有可用 `completed` 索引时直接短路返回空结果，不再白做 query embedding。

## 2026-05-26 短 query 检索修正

- 纯向量分数对超短 query 不再被当成可解释信号，`1-4` 个汉字或极短单 token 会启用更严格的检索规则。
- `backend/ai/vectorstores.py` 现在会给 exact substring、附件名命中、chunk 前部命中、首块命中加权，做轻量混合复排。
- 短 query 没有词面命中时，不再把结果写入 `used_chunks`，也不再显示 `Sources used`。
- `used_chunks` 额外保留 `vector_score` 和 `lexical_match`，方便后续排查“向量高分但业务不相关”的误召回。

## 配置

```env
OPENAI_API_KEY=你的密钥
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash
```

虽然变量名仍叫 `OPENAI_*`，但当前实现使用的是 OpenAI-compatible 协议，DeepSeek 可以通过 `OPENAI_BASE_URL` 接入。

## 验收记录

2026-05-18 已验证：

- `python manage.py check` 通过
- `python manage.py test` 通过
- `npm run build` 通过
- 真实发送消息后，最新 `AgentRun.status` 为 `langgraph_completed`

2026-05-18 文件工具更新已验证：

- `python manage.py check` 通过
- `python manage.py test` 通过，当前 8 个测试
- `npm run build` 通过
- `requirements.lock` 已包含 `python-docx`、`pypdf`、`pymupdf`、`lxml`

## 2026-05-27 OCR 调优记录

- `backend/ai/document_readers.py` 的 PDF OCR fallback 现在会优先根据本机 `tesseract --list-langs` 自动选择语言；检测到 `chi_sim` 和 `eng` 时默认使用 `chi_sim+eng`。
- OCR 调用改为 `300 DPI + full-page OCR + sort=True`，主要针对扫描 PDF 的中文乱码和文本顺序错位问题。
- 如果部署环境明确以中文扫描件为主，建议在 `.env` 里显式设置 `PDF_OCR_LANGUAGE=chi_sim+eng`，并保留 `PDF_OCR_DPI=300`。
