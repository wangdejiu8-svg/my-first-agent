# 项目 MVP 开发计划

## 1. 文档目的

这份文档只服务当前一个明确目标：

**逐步去除当前分散的 LangGraph `tools`，改为内部白名单 CLI 能力层。**

这里的“改为 CLI”不是把系统变成任意命令执行器，也不是把 Django 的权限边界让给外部进程，而是：

- 把当前 `tools` 中的业务能力整理成统一的内部 CLI 接口。
- 用结构化命令替代多组零散 tool 定义。
- 保留 Django 作为唯一认证、会话归属、附件归属和持久化边界。

## 2. 当前状态

当前项目已经具备一个可用的会话型 AI MVP：

- React 前端、Django REST 后端、LangGraph 编排链路。
- 用户认证、会话、消息、附件、`AgentRun` 持久化。
- `.docx` / `.pdf` 上传、文本提取、OCR fallback。
- `KnowledgeDocument`、`KnowledgeChunk`、`RetrievalLog` 数据模型。
- 会话内 RAG、来源展示、流式回复。

当前 `tools` 已经能完成：

- 读取当前用户会话列表。
- 读取当前会话消息。
- 读取用户设置。
- 检索当前会话知识。
- 读取附件片段或全文。

但当前问题也已经足够明确：

- `tools` 是 LangGraph 闭包式定义，复用性一般。
- 工具能力分散，不适合被其他 agent 宿主或脚本统一复用。
- 缺少统一命令入口、统一 JSON 输出和统一帮助文档。
- 后续继续加工具时，维护成本会逐步上升。

## 3. 当前决策

当前阶段的路线不是继续扩写 `backend/ai/tools/chat.py`，而是：

1. 抽离工具业务逻辑到独立服务层。
2. 建立统一内部 CLI。
3. 让 Agent 通过 CLI 适配层访问能力。
4. 最终移除原有分散的 LangGraph `tools` 定义。

一句话总结：

**后续演进目标是“CLI-first 的内部能力层”，而不是继续堆更多 LangGraph tools。**

## 4. 为什么要从 `tools` 改到 CLI

这次改造的收益必须说清楚，否则只是在换壳。

切到内部 CLI 后，能得到：

- 统一入口：所有能力都变成同一套命令空间。
- 统一输出：所有命令默认支持结构化 JSON。
- 更强复用：Django、LangGraph、测试脚本、外部 agent 都可以复用同一能力层。
- 更好调试：命令可单独执行，不需要每次都走整条对话链路。
- 更清晰约束：命令名、参数、输出格式都可以固定，减少隐式行为。

这条路线不是为了“更酷”，而是为了降低后续维护成本。

## 5. GitHub 参考方案

本次文档方向参考 `CLI-Anything` 的公开方案，但不是照搬它的全部形态。

参考仓库：

- `CLI-Anything`：https://github.com/HKUDS/CLI-Anything
- `HARNESS.md`：https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/HARNESS.md
- `cli-anything-plugin/README.md`：https://github.com/HKUDS/CLI-Anything/blob/main/cli-anything-plugin/README.md

### 5.1 参考点一：统一 CLI 壳

`CLI-Anything` 的核心思路不是“先写一堆 tool”，而是：

- 把系统能力整理成一个统一 CLI。
- 用命令组、子命令和参数描述能力边界。
- 让 agent 通过 CLI 帮助信息和 JSON 输出理解系统。

这对当前项目最有借鉴意义。

### 5.2 参考点二：结构化输出

参考方案强调：

- 命令要适合 agent 使用。
- 命令输出要稳定。
- JSON 是默认的一等输出形式。

这正好解决当前 `tools` 分散、返回结构靠函数定义约定的问题。

### 5.3 参考点三：CLI + 文档 + 测试一起交付

参考方案不是只生成命令，还会把以下内容视为同一交付物：

- CLI 命令本体
- 帮助信息
- Agent 使用说明
- 测试

这点也必须纳入本项目改造，否则 CLI 只会变成另一层隐式复杂度。

### 5.4 本项目不照搬的部分

本项目不会直接照搬以下能力：

- 任意系统范围 CLI 封装。
- 让模型自由拼装 shell 命令。
- 把 Django 权限边界外包给 CLI 框架。

原因很简单：

- 当前项目是受认证保护的 Web 应用，不是通用桌面代理。
- 当前项目的核心边界是 `request.user + conversation`，不是本机环境。
- 任何脱离 Django 认证上下文的通用命令执行都是高风险改造。

## 6. 本项目的 CLI 化原则

按 Karpathy 风格，这里只保留最小必要原则，不做空泛设计。

### 6.1 只做白名单内部 CLI

CLI 只能暴露明确子命令，不允许透传任意命令。

允许的方向是：

- `conversation list`
- `conversation messages`
- `settings get`
- `knowledge search`
- `attachment read`

不允许的方向是：

- 让模型传自由 shell 字符串。
- 让模型自行指定任意路径或任意用户。
- 让 CLI 直接承担高风险写操作。

### 6.2 Django 仍然是唯一权限边界

CLI 不是新的安全边界。

必须保持：

- 当前登录用户由 Django 注入。
- 当前会话 ID 由 Django 注入或经过 Django 校验。
- CLI 内部继续走服务层和 ORM 归属检查。
- CLI 只是一层统一调用面，不替代鉴权逻辑。

### 6.3 先只读，后评估写操作

MVP 改造期只把现有只读工具能力 CLI 化。

以下高风险链路继续留在 Django 服务层，不进入第一阶段 CLI：

- 用户发消息落库
- assistant 消息回填
- `AgentRun` 创建与更新
- 上传绑定附件
- 删除会话

### 6.4 输出必须稳定

CLI 适配层必须支持：

- `--json`
- 稳定字段名
- 稳定错误结构

不能让 agent 依赖松散文本输出。

## 7. 目标架构

改造后的推荐链路：

```text
React
-> Django REST API
-> apps.chat.services
-> ai.runtime
-> internal CLI bridge
-> internal app CLI
-> service layer
-> Django ORM
```

对应关系如下：

- 前端继续只调用 Django API。
- Django 继续负责认证、会话归属、附件归属和落库。
- Agent 不再面向多组分散 `tools`。
- Agent 改为面向统一 CLI 能力面。
- CLI 内部再调用服务层，而不是直接裸查数据库。

## 8. 目录改造建议

建议新增或调整如下结构：

```text
backend/
├── ai/
│   ├── runtime.py
│   ├── cli_bridge.py
│   └── tool_services.py
├── app_cli/
│   ├── __init__.py
│   ├── main.py
│   ├── commands/
│   │   ├── conversation.py
│   │   ├── settings.py
│   │   ├── knowledge.py
│   │   └── attachment.py
│   └── tests/
```

说明：

- `tool_services.py` 负责承载原 `tools` 的核心业务逻辑。
- `app_cli/` 提供统一 CLI。
- `cli_bridge.py` 负责把 Agent 请求映射到 CLI 调用。

## 9. 命令设计建议

建议使用 `Click` 风格的命令树。

第一阶段命令建议如下：

### 9.1 conversation

- `agent-app conversation list --user-id <id> --limit 5 --json`
- `agent-app conversation messages --user-id <id> --conversation-id <id> --limit 10 --json`

### 9.2 settings

- `agent-app settings get --user-id <id> --json`

### 9.3 knowledge

- `agent-app knowledge search --user-id <id> --conversation-id <id> --query "<text>" --top-k 5 --json`

### 9.4 attachment

- `agent-app attachment read --user-id <id> --conversation-id <id> --attachment-id <id> --json`
- `agent-app attachment context --user-id <id> --conversation-id <id> --attachment-id <id> --query "<text>" --top-k 5 --json`

注意：

- `user-id` 和 `conversation-id` 不是给模型自由发挥的开放参数。
- 在线上调用中，它们应该由 Django 包装层填充。
- CLI 本身仍要做归属校验，不能信任调用方。

## 10. LangGraph 迁移方案

当前项目不应该一步删光 `tools`，而应该按最小风险迁移。

### Phase 1：抽离现有工具逻辑

目标：

- 把 `backend/ai/tools/chat.py` 中的业务逻辑移到 `tool_services.py`。

要求：

- 当前接口行为不变。
- 当前测试不回退。
- 当前安全边界不变化。

### Phase 2：实现内部 CLI

目标：

- 把服务层能力暴露成统一 CLI。

要求：

- 命令帮助清晰。
- 所有命令支持 `--json`。
- 错误输出结构统一。

### Phase 3：新增 CLI bridge

目标：

- 在 `ai.runtime` 附近增加一层桥接，让 Agent 调 CLI，而不是调多组分散 tools。

做法：

- 初期可以保留一个很薄的桥接 tool，例如 `run_internal_cli_command`。
- 这个桥接层只接受白名单命令，不接受自由文本命令。
- 桥接层负责注入用户和会话上下文。

### Phase 4：替换现有分散 tools

目标：

- 把原有 `list_user_conversations`、`get_user_settings` 等分散 tools 逐步下线。

要求：

- CLI 路线完全覆盖原有只读能力。
- 行为一致性已经通过测试验证。
- 文档和调用约束已经同步更新。

### Phase 5：删除旧工具实现

目标：

- 删除旧的 LangGraph 细粒度 tool 定义，只保留 CLI bridge 或等价统一入口。

要求：

- 没有残留双轨调用逻辑。
- 没有前后不一致的文档。

## 11. 测试要求

这次改造必须补足测试，否则只是架构口号。

至少覆盖：

- CLI 命令成功返回 JSON。
- CLI 对错误会话、错误附件、错误归属返回稳定错误。
- CLI 不会跨用户读取数据。
- CLI bridge 注入上下文后行为与旧 tools 一致。
- 旧 tools 下线前，新旧实现结果一致。

执行门禁：

- `manage.py check`
- `manage.py test`
- 前端 `npm run build`

如果改到登录、会话、上传、Agent 链路，还必须补手工浏览器验证。

## 12. 风险清单

### 12.1 最大风险

最大的风险不是“CLI 写不出来”，而是“CLI 改造把安全边界做丢了”。

### 12.2 具体风险

- 把统一 CLI 误做成任意命令执行层。
- 让模型自由控制 `user_id`、`conversation_id` 或文件路径。
- 为了 CLI 化，把现有事务链路拆碎。
- 新旧工具并存时间过长，导致行为漂移。

### 12.3 约束

必须保持：

- 未登录用户不能访问受保护 API。
- `conversation`、`message`、`attachment` 必须属于当前用户。
- 发送消息时，用户消息、AI 消息和 `AgentRun` 必须完整落库。
- `OPENAI_API_KEY` 为空时允许 fallback，但仍要保存消息和运行记录。
- Agent 使用 CLI 时也只能使用后端绑定的上下文。

## 13. 验收标准

本次文档所定义的方向完成后，至少要满足：

1. 原有只读 `tools` 的能力已经迁移到内部 CLI。
2. Agent 能通过统一 CLI 能力面完成原有读取和检索任务。
3. CLI 输出结构稳定，支持 JSON，便于 agent 和测试复用。
4. Django 仍然是唯一权限边界，没有出现任意命令执行面。
5. 原有分散 `tools` 已经下线或明确处于待删除状态。
6. 文档中已经明确记录 GitHub 参考方案和本项目实际裁剪后的做法。

## 14. 最终结论

当前项目接下来的正确方向是：

**不再继续扩张 LangGraph `tools`，而是以去除 `tools`、改为内部白名单 CLI 为目标推进。**

参考 `CLI-Anything` 的正确方式不是照搬一个通用命令代理框架，而是借它这几件事：

- 统一 CLI 命令空间
- 统一 `--json` 输出
- 统一帮助信息
- 统一测试与文档交付

本项目的落地版本必须额外坚持一条硬约束：

**CLI 只能是 Django 安全边界内部的一层能力适配面，不能反过来成为新的系统边界。**
