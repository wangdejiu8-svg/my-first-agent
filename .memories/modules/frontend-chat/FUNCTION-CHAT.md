# 对话功能实现

## 当前状态

对话功能已经从 `mockApi` 迁移到 Django 后端和 SQLite 数据库。前端可以真实创建会话、读取历史消息、发送消息并持久化。

## 前端实现

- `frontend/src/pages/ChatPage.js` 维护 `conversations`、`activeConversationId`、`messages`。
- `frontend/src/components/Sidebar.js` 由父组件传入会话列表和当前会话，不再自己维护孤立的 `activeConvId`。
- `frontend/src/components/ChatArea.js` 只负责输入、展示和触发发送。
- `frontend/src/services/chatApi.js` 封装会话和消息相关 API。
- `Sidebar.js` 支持在会话项上右键打开上下文菜单。
- 右键菜单提供“删除对话”操作，并调用 `DELETE /api/conversations/{id}/`。
- 删除确认不再使用 `window.confirm`，改为应用内 `delete-dialog` 确认弹层。
- 删除当前选中的对话后，`ChatPage.js` 会自动切换到剩余第一条会话；如果没有剩余会话，则清空消息区。
- `ChatArea.css` 修正消息区布局：消息行固定最大可读宽度，用户气泡靠右且不再被短中文挤成竖向窄块，AI 回复保持完整阅读宽度。
- Markdown 段落、列表和代码块增加基础间距与代码样式。
- `ChatArea.css` 将消息列和输入框从居中改为左锚定布局；后续按视觉反馈将输入框进一步向右偏移到 `clamp(88px, 11vw, 180px)`。
- 输入框支持选择多个文件，选中文件会显示为文件 chip，可在发送前移除。
- 发送消息时会先调用 `POST /api/files/upload/` 上传文件，再把 `attachment_ids` 传给 `POST /api/chat/send/`。
- 输入区调整了 textarea 的高度和内边距，修正单行文本不在输入框视觉中间的问题。
- 用户消息会展示已绑定附件，点击附件可打开后端 media 文件地址。

## 后端实现

- `Conversation`：用户会话，按 `owner` 隔离，当前 `DELETE /api/conversations/{id}/` 执行硬删除并级联清理关联数据。
- `Message`：保存用户消息和 AI 回复。
- `Attachment`：保存上传文件记录，并可绑定到具体 `Message`。
- `AgentRun`：记录 AI 调用请求、响应、模型、状态和耗时。
- `KnowledgeDocument`：记录附件索引状态、归属和错误信息。
- `KnowledgeChunk`：记录切片文本、元数据和向量。
- `RetrievalLog`：记录每次检索命中的 chunk。
- `backend/apps/chat/services.py` 调用 `backend/ai/runtime.py`，由 LangGraph 编排模型和工具。
- 没有正确配置模型环境变量时返回中文 fallback，保证联调闭环可运行。
- assistant 消息现在会携带 `sources`、`used_chunks`、`is_rag_answer`、`rag_score` 元数据。

## API 接口

- `GET /api/conversations/`
- `POST /api/conversations/`
- `PATCH /api/conversations/{id}/`
- `DELETE /api/conversations/{id}/`
- `GET /api/conversations/{id}/messages/`
- `POST /api/chat/send/`
- `POST /api/files/upload/`

## 2026-05-20 RAG MVP 更新

- 上传 `.docx/.pdf` 后会立即尝试索引，索引失败不影响附件主记录保存。
- 起始上传若还未绑定会话，附件相关的知识记录先挂在 `owner` 下；发送消息绑定到会话时，会同步回写 `KnowledgeDocument/KnowledgeChunk` 的 `conversation`。
- 发送消息前会先做当前会话内 top-k 检索，再把来源片段注入模型上下文。
- 前端 assistant 消息下方新增来源区块，优先展示 `sources`，没有摘要时回退展示 `used_chunks` 片段，并显示本条回复的实际 `rag_score`。

## 数据隔离规则

所有会话查询都必须使用：

```python
Conversation.objects.active().owned_by(request.user)
```

不能信任前端传来的用户 ID。

## 验收测试

后端测试覆盖：

- 会话列表只返回当前用户数据
- 不能读取其他用户会话消息
- 发送消息会创建会话和两条消息
- 发送带附件消息会把上传文件绑定到用户消息
- 未登录不能发送消息

本次右键删除已验证：

- `npm run build` 通过
- `python manage.py test` 通过
- 真实调用 `DELETE /api/conversations/{id}/` 后，再访问该会话消息返回 404

本次对话框修正已验证：

- `npm run build` 通过
- `python manage.py test` 通过
- 浏览器截图确认用户气泡不再窄列换行

本次删除弹层修正已验证：

- 右键会话后点击“删除对话”显示应用内确认弹层
- 不再触发 Windows/浏览器原生确认框

本次文件输入修正已验证：

- `python manage.py makemigrations --check --dry-run` 通过
- `python manage.py check` 通过
- `python manage.py migrate` 已应用 `chat.0002_attachment_message`
- `python manage.py test` 通过，当前 7 个测试
- `npm run build` 通过

本次 RAG MVP 已验证：

- `python manage.py check` 通过
- `python manage.py test` 通过
- `npm run build` 通过
- 历史消息返回体包含 `sources/used_chunks/is_rag_answer/rag_score`

## 2026-05-20 更新：上传安全加固

- 上传入口不再只信任扩展名和前端 `content_type`，新增了 PDF 文件头校验与 DOCX ZIP 结构校验。
- 服务端会拒绝空文件、异常 DOCX 结构、非法归档路径和解压后体积异常的文档。
- 保存附件时会收敛 `original_name` 为基名，避免把路径片段带进业务数据。
- 文档读取失败现在统一返回稳定业务错误，不再直接向上层暴露底层解析器异常。

## 后续计划

- 将普通非流式回复升级为 SSE 流式输出。
- Word/PDF 文件内容读取已接入 Agent 工具；扫描版 PDF 在环境具备 `tesseract` 时会走 OCR fallback，但图片和其他文件格式仍未接入 OCR/解析。
- 当前向量存储仍是 SQLite + JSON 持久化向量的 MVP 方案，后续如规模增长再迁移 pgvector。

## 2026-05-20 会话删除更新

- 删除会话现已改为硬删除，对应 `Message`、`Attachment`、`AgentRun`、`KnowledgeDocument`、`KnowledgeChunk`、`RetrievalLog` 会一起清理。
- 会话关联的上传文件会从 `backend/media/` 同步删除，不再只是在会话列表里隐藏。
## 2026-05-21 流式回复

- 前端 `chatApi.sendMessageStream()` 现在消费 `POST /api/chat/send-stream/` 的 NDJSON 流，事件顺序是 `start -> delta* -> done`。
- `ChatPage.js` 在 `start` 事件时替换 optimistic user message，并建立 assistant 占位消息；后续 `delta` 事件持续追加到同一条 assistant 消息。
- `ChatArea.js` 的自动滚动不再只看 `messages.length`，而是跟踪最后一条消息的内容长度变化；用户仍贴底时会继续追踪 assistant 生成中的文本。
- 为避免切换到新会话时被后台 `getMessages()` 请求覆盖流式中的增量文本，消息列表刷新会在 `isChatLoading` 结束后再恢复。
