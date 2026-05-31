# FUNCTION-RAG-GATE

## 功能边界

- 只处理“这条消息要不要进当前会话 RAG”。
- 不改 `owner + conversation` 检索边界。
- 不引入独立语义 router。
- 不引入 LLM judge。

## 当前实现

代码路径：

- `backend/ai/retrieval_gate.py`
- `backend/ai/retrieval.py`
- `backend/apps/chat/services.py`

Phase 1 已落地规则：

- `skip`：寒暄、感谢、上传提示、无可用知识文档
- `retrieve`：明确文档引用、附件名重叠、明显文档承接问法
- `probe`：其余“当前会话有可用知识文档”的消息

## 关键约束

- `probe` 和正式 `retrieve` 必须复用同一批 hits，不能同一轮重复 embedding / 重复扫描。
- gate / probe 失败时必须降级回旧链路，不能影响消息保存、AI 回复、`AgentRun` 落库。
- assistant 消息要保存最终决策元数据。
- `RetrievalLog.metadata_json` 要保存本次决策，便于后续评估。

## 验证方式

- `backend\\.venv\\Scripts\\python.exe manage.py check`
- `backend\\.venv\\Scripts\\python.exe manage.py test apps.chat.tests`

## 踩坑记录

- Phase 1 如果把 `文档` / `附件` / `pdf` 这种泛词直接当强触发，很容易把泛问题误判成文档问题，所以当前只保留更明确的短语触发。
- 当前底层还是 SQLite + Python 扫描，`probe` 并不会带来真正的 ANN 级性能优化；它的主要价值是减少无关上下文注入，而不是降低扫描成本。
