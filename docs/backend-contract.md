# backend/ 契约

本文档只约束 `backend/` 下的实现。

## 目录职责

- `apps/accounts/`：注册、登录、退出、个人设置、改密。
- `apps/chat/`：会话、消息、附件、`AgentRun`。
- `ai/`：LangGraph 编排、模型调用、工具封装。
- `config/`：Django 配置、路由、CORS、鉴权、环境变量。

## 实现规则

- 视图层只做参数接收、权限校验、调用服务和返回响应。
- 会话和附件归属必须在服务端根据 `request.user` 校验。
- `ai/tools/` 里的工具不能直接信任前端传参。
- 发送消息时，优先保证“用户消息 -> AI 回复 -> AgentRun”完整落库。
- `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL` 必须只从后端环境读取。

## 安全规则

- 不要把 token、密码、API key、私有 prompt 原样写进日志。
- 不要用前端传入的 `user_id` 代替后端当前用户。
- 不要绕过 `Conversation.objects.active().owned_by(user)` 这类归属过滤。
- 文件上传后要记录所有者，后续绑定消息时要再次校验归属。

## 验证规则

- 改 `models.py`、`serializers.py`、`views.py`、`services.py` 或 `ai/` 后，至少跑 `manage.py check` 和 `manage.py test`。
- 改数据库结构后必须补 migration，并更新 `backend/README.md`。
- 改环境变量或接口路径后，必须同步更新 `backend/.env.example` 和文档。
