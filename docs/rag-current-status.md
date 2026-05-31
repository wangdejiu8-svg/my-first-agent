# 当前 RAG 状态说明（2026-05-31 快照）

本文档只回答两件事：

1. **代码现在是怎么工作的**
2. **当前本地数据库里已经验证到什么状态**

这两个维度必须分开看。代码事实相对稳定，数据库里的“某个文件是否索引成功”是**时间点快照**，会随着重新上传、重新索引或环境变化而改变。

## 一句话结论

当前项目已经具备可工作的 **MVP 级会话内 RAG**，但它**不是独立向量数据库方案**。

更准确的描述是：

> 当前项目把 embedding 持久化到 SQLite 的 `KnowledgeChunk.embedding_json`，并在 Django/Python 应用层完成向量检索、词面复排和来源回写。

## 一、当前代码事实

以下结论直接来自当前代码：

- 主数据库：`backend/db.sqlite3`
- 向量存储位置：`KnowledgeChunk.embedding_json`
- 检索范围：`owner + conversation + completed knowledge documents`
- 相似度计算：Python 侧余弦相似度
- 结果复排：向量分 + 词面命中加权
- assistant 元数据持久化：`sources`、`used_chunks`、`is_rag_answer`、`rag_score`
- 检索决策元数据持久化：`retrieval_decision`、`retrieval_reason`、`retrieval_relatedness`、`retrieval_probe_score`、`retrieval_decision_version`

相关实现文件：

- `backend/apps/chat/services.py`
- `backend/apps/chat/indexing.py`
- `backend/ai/chunking.py`
- `backend/ai/embeddings.py`
- `backend/ai/retrieval.py`
- `backend/ai/vectorstores.py`
- `backend/ai/document_readers.py`

## 二、当前检索链路

一次消息的大致处理流程如下：

1. 用户发送消息。
2. `backend/apps/chat/services.py` 先走 Phase 1 gate：`skip / retrieve / probe`。
3. 明显寒暄/感谢/上传提示类消息直接 `skip`。
4. 明显文档引用或附件名重叠的消息直接 `retrieve`。
5. 其余“当前会话存在可用知识文档”的消息进入 `probe`。
6. `backend/ai/retrieval.py` 会先确保当前会话里 `pending` 或缺失的知识文档被补索引。
7. 检索只会查询当前会话中 `index_status=completed` 的 `KnowledgeDocument`。
8. 文档文本按 chunk 切分后，embedding 写入 `KnowledgeChunk.embedding_json`。
9. 查询时按 `embedding_backend` 分组生成 query embedding，避免不同向量来源混检。
10. `backend/ai/vectorstores.py` 先做向量召回，再叠加词面命中分数。
11. `probe` 与正式 `retrieve` 复用同一批 hits，避免同一轮消息重复 embedding / 重复扫描。
12. 命中的 chunk 会回写到 assistant 消息的 `used_chunks` 和 `sources`；决策结果会同时写入 assistant metadata 和 `RetrievalLog.metadata_json`。

## 三、当前配置参数

当前代码默认值和本地环境实值一致：

- `RAG_CHUNK_SIZE = 900`
- `RAG_CHUNK_OVERLAP = 120`
- `RAG_TOP_K = 5`
- `RAG_MIN_SCORE = 0.5`
- `RAG_INDEX_MAX_CHARS = 120000`
- `PDF_OCR_DPI = 300`

当前本地环境还启用了：

- `OPENAI_MODEL = deepseek-v4-flash`
- `OPENAI_BASE_URL = https://api.deepseek.com`
- `OPENAI_EMBEDDING_BASE_URL = http://127.0.0.1:11434/v1`
- `OPENAI_EMBEDDING_MODEL = nomic-embed-text`
- `PDF_OCR_LANGUAGE = chi_sim`

说明：

- 聊天模型走 **DeepSeek 的 OpenAI-compatible 接口**。
- embedding 代码内部仍把远端 backend 记作 `openai`，但当前实际 endpoint 指向 **本机 Ollama**。
- 所以数据库里看到 `embedding_backend = openai`，并不等于“在用 OpenAI 官方 embedding”。

## 四、短 query 和误检索收敛

当前实现已经有三层收敛机制：

### 1. 检索前置挡板

`backend/apps/chat/services.py` 会直接跳过明显寒暄/感谢/确认类短消息。

当前运行时已确认会跳过的样例包括：

- `你好`
- `您好`
- `谢谢`
- `收到`
- `在吗`
- `继续`
- `hi`
- `hello`
- `thanks`

这不是复杂分类器，只是规则挡板。

### 2. Phase 1 gate 会先区分 `skip / retrieve / probe`

当前已落地的是 **Phase 1: `fast-skip + probe`**，还没有接独立语义 router，也没有接 LLM judge。

当前行为：

- 明显文档信号：直接 `retrieve`
- 当前会话没有 `completed` 知识文档：直接 `skip`
- 其余有可用文档的消息：先 `probe`

当前强触发 `retrieve` 的信号主要是：

- query 明确提到“这份文档”“附件里”“刚上传”“根据附件”“根据文档”等短语
- query 与附件名存在直接重叠
- query 是明显的文档承接问法，并且最近消息已有文档相关上下文

### 3. 短 query 必须有词面命中

`backend/ai/retrieval.py` 与 `backend/ai/vectorstores.py` 当前会把下面两类 query 视为“短 keyword”：

- `1-4` 个汉字
- `1-4` 个英数/下划线/连字符 token

对这类 query：

- 召回候选池会适当放大
- 结果会按词面信号复排
- **没有词面命中的 chunk 不允许进入 `used_chunks`**

当前词面信号包括：

- 附件名命中
- chunk 文本包含 query
- query 命中 chunk 前 `180` 字
- `chunk_index == 0`

## 五、PDF 和 OCR 的真实状态

当前代码路径是：

1. 先用 `pypdf`
2. 失败后回退 `pymupdf`
3. 仍提取不到文本时，如果环境可用 `tesseract` 或设置了 `TESSDATA_PREFIX`，再尝试 OCR

当前这台机器已经确认：

- 已安装 `tesseract`
- 可用语言包含 `chi_sim` 和 `eng`
- `PDF_OCR_LANGUAGE = chi_sim`

所以更准确的说法不是“项目可能有 OCR”，而是：

> 当前本地开发环境已经具备 OCR 兜底能力，但 OCR 是否可用仍取决于部署环境是否安装了 `tesseract` 和语言包。

## 六、当前数据库快照

以下内容来自 **2026-05-31** 的 `backend/db.sqlite3`。

当前 `KnowledgeDocument` 快照：

| id | 附件名 | 状态 | backend | chunk 数 | 向量维度 | 备注 |
| --- | --- | --- | --- | ---: | ---: | --- |
| 5 | `RZ51_单片机实验任务实现一步一步教程.docx` | `completed` | `openai` | 27 | 768 | 当前已成功 |
| 6 | `WireShark常用过滤器语法.pdf` | `failed` | 空 | 0 | 0 | 错误：`文档中没有提取到可索引文本。` |
| 7 | `31180014XX-XXX-计算机网络实验报告（部分参考案例）.docx` | `completed` | `openai` | 1 | 768 | 当前已成功 |
| 8 | `WireShark常用过滤器语法.pdf` | `failed` | 空 | 0 | 0 | 错误：`文档中没有提取到可索引文本。` |
| 9 | `WireShark常用过滤器语法.pdf` | `completed` | `openai` | 4 | 768 | 后续上传已成功 |
| 10 | `数据库系统原理及应用实验方案.pdf` | `completed` | `openai` | 9 | 768 | 当前已成功 |

当前总 `KnowledgeChunk` 数量：`41`

这里有一个重要结论：

> 文档原先把 `WireShark常用过滤器语法.pdf` 写成“当前失败且没有生成向量”，这在 **2026-05-31** 已经不再准确。更准确的说法是：**同名 PDF 历史上有失败记录，但当前数据库里已经存在后续上传并索引成功的记录。**

## 七、哪些说法是准确的，哪些已经过期

### 仍然准确

- 当前项目有可工作的会话内 RAG。
- 当前项目不是 `pgvector` / Milvus / Qdrant 这类独立向量数据库方案。
- 检索使用 SQLite 持久化 + Python 应用层相似度计算。
- 当前 embedding 使用 `nomic-embed-text`，并通过 OpenAI-compatible 接口调用。
- 当前有短 query 收紧和最小相似度阈值。
- 当前服务层已经不是简单二态判断，而是 Phase 1 的 `skip / retrieve / probe` 决策。
- 当前 skip/probe/retrieve 决策会写入 `RetrievalLog.metadata_json`，assistant 消息也会带检索决策元数据。

### 已经过期或需要改写

- “`WireShark常用过滤器语法.pdf` 当前索引失败、没有生成向量。”
- “扫描 PDF 的 OCR 兜底还没有。”

这两句在当前本地环境和数据库快照下都不准确。

## 八、推荐术语

以后对内对外描述时，建议使用下面这些说法：

- “当前项目使用 SQLite 持久化 embedding。”
- “当前项目在应用层做向量检索和轻量复排。”
- “当前项目的 embedding 服务当前接的是本机 Ollama 的 `nomic-embed-text`。”
- “当前项目已经有会话内 RAG，但还不是独立向量数据库架构。”

不建议直接说：

- “我们已经用了向量数据库。”
- “这个 PDF 现在一定索引失败。”

第二句的问题不是技术定义，而是它会把**某次历史结果**误写成**当前状态**。

## 九、维护规则

以后更新这份文档时，按下面规则写，避免再次过期：

1. 把“代码事实”和“数据库快照”分开写。
2. 所有“当前成功/当前失败”都带上明确日期。
3. 对具体文件名，不要只写结论；要写是否存在多次上传。
4. 对 OCR 这类环境能力，区分“代码支持”和“当前机器已配置”。
