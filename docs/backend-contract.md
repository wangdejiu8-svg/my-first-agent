# backend/ 契约

本文档只约束 `backend/` 下的实现。

## 目录职责

- `apps/accounts/`：注册、登录、退出、个人设置、改密。
- `apps/chat/`：会话、消息、附件、`AgentRun`。
- `ai/`：LangGraph 编排、模型调用、embedding、检索和工具封装。
- `config/`：Django 配置、路由、CORS、鉴权、环境变量。

## 实现规则

- 视图层只做参数接收、权限校验、调用服务和返回响应。
- 会话和附件归属必须在服务端根据 `request.user` 校验。
- `ai/tools/` 里的工具不能直接信任前端传参。
- 发送消息时，优先保证“用户消息 -> AI 回复 -> AgentRun”完整落库。
- RAG 检索默认先按 `owner + conversation` 做边界过滤，再决定是否扩展到更大范围。
- 附件索引失败不能影响 `Attachment` 主记录保存，必须通过索引状态显式标记失败。
- assistant 消息如返回来源信息，必须随消息一起持久化，避免历史消息刷新后丢失 `sources/used_chunks`。
- `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 以及 `OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_MODEL` 必须只从后端环境读取。

## 安全规则

- 不要把 token、密码、API key、私有 prompt 原样写进日志。
- 不要用前端传入的 `user_id` 代替后端当前用户。
- 不要绕过 `Conversation.objects.active().owned_by(user)` 这类归属过滤。
- 会话删除如果定义为硬删除，必须同时清理关联的消息、附件、检索数据和物理上传文件，不能只删主表记录。
- 文件上传后要记录所有者，后续绑定消息时要再次校验归属。
- `KnowledgeDocument`、`KnowledgeChunk`、`RetrievalLog` 等检索数据必须继承同样的用户/会话归属边界。
- 使用 Cookie 承载 token 时，任何 `POST`、`PATCH`、`DELETE` 等非只读请求都必须通过 CSRF 校验。
- 普通 `staff` 不能提升、降级、删除或修改 `staff/superuser` 账号，角色字段只能由 `superuser` 修改。
- `.docx`、`.pdf` 上传不能只信任扩展名和前端 `content_type`，至少要做服务端文件头或结构校验，并对解析失败返回稳定错误。

## 验证规则

- 改 `models.py`、`serializers.py`、`views.py`、`services.py` 或 `ai/` 后，至少跑 `manage.py check` 和 `manage.py test`。
- 改数据库结构后必须补 migration，并更新 `backend/README.md`。
- 改环境变量或接口路径后，必须同步更新 `backend/.env.example` 和文档。
- 改检索链路后，至少要覆盖上传索引、会话边界检索和来源元数据返回。
