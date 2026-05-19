# LangGraph Agent 实现

## 当前状态

后端已经按架构文档拆出独立 AI 编排层：`backend/ai/`。它不是 Django app，不注册到 `INSTALLED_APPS`，只作为普通 Python 包被业务服务调用。

## 目录结构

```text
backend/ai/
├── __init__.py
├── context.py          # 构造 LangGraph config，注入 user_id/conversation_id/thread_id
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
- `read_current_conversation_documents(limit=3)`：读取当前会话最近上传的 Word/PDF 附件文本。
- `read_uploaded_document(attachment_id)`：按附件 ID 精确读取 Word/PDF 附件文本。

## 文件读取能力

第一版文件工具支持：

- `.docx`：使用 `python-docx` 提取段落和表格文本。
- `.pdf`：使用 `pypdf` 提取页面文本。
- 单次读取最多返回前 `12000` 个字符，避免工具结果过大。
- 工具只读取当前登录用户、当前会话下的附件，不能跨用户或跨会话读取。

注意：扫描版 PDF 如果没有可提取文本，工具会返回“没有提取到可读文本”，后续需要 OCR 工具补充。

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
- `requirements.lock` 已包含 `python-docx`、`pypdf`、`lxml`
