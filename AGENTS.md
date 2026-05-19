# 项目契约

本文档定义 `my-first-agent` 的代码边界、质量门禁和安全约束。它不是产品说明，而是给人和 AI 共同遵守的运行契约。

## 作用范围

- `frontend/`：React 前端界面、路由、状态和 API 调用封装。
- `backend/`：Django 后端、认证、会话、附件、Agent 调用和数据库边界。
- `backend/ai/`：LangGraph 编排层，只负责推理流程和工具调用，不直接承担权限校验。
- `.memories/`：功能实现后的知识沉淀和踩坑记录。
- `docs/backend-contract.md` 和 `docs/frontend-contract.md`：前后端代码约束说明。

## 代码边界

- 前端请求统一走 `frontend/src/services/`，页面里不要散写 `fetch`/`axios`。
- 后端复杂逻辑放在 `services.py` 或 `ai/`，`views.py` 保持薄。
- 认证、会话归属、附件归属必须在服务端校验，不能信任前端传入的用户 ID。
- 任何涉及模型、路由、权限、文件上传、Agent 编排的改动都属于高风险改动。

## 不变量

- 未登录用户不能访问需要鉴权的 API。
- `conversation`、`message`、`attachment` 必须始终属于当前登录用户。
- 发送消息时，用户消息、AI 消息和 `AgentRun` 记录必须一起落库。
- `OPENAI_API_KEY` 为空时允许 fallback 回复，但仍要保存消息和运行记录。
- Agent 工具只能使用后端绑定的 `request.user` 和 `conversation`。
- 不允许把真实密钥、token、密码、完整数据库内容写入日志或文档。

## 质量门禁

- 后端改动后至少执行 `manage.py check` 和 `manage.py test`。
- 前端改动后至少执行 `npm run build`。
- 涉及登录、会话、上传、Agent 链路的改动，必须补一次手工浏览器验证。
- 数据模型变更必须配套 migration，并更新相关文档。

## 文档回写

- 改了代码约束，就要同步写回到对应文档。
- 新增接口或行为变化，优先更新 `README.md`、`backend/README.md` 和 `.memories/`。
- 以后任何“以后别这样改”的经验，都要写成明确规则，不要只留在聊天记录里。
