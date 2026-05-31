# RAG 检索升级 PRD

更新时间：2026-05-31

## 1. 文档目的

本文档基于 [rag-current-status.md](/D:/The biggest git workplace/my-first-agent/docs/rag-current-status.md:1) 的当前实现快照，定义下一阶段 RAG 检索升级方案。

目标不是把项目一次性重构成完整 Agentic RAG 或真实向量数据库架构，而是先解决当前最直接的问题：

- AI 对“当前这条消息是否真的需要使用附件文档”的判断还不够智能
- 当前系统在会话存在附件时，容易把与文档无关的问题也送进 RAG
- 当前检索链路缺少“不确定态”和可验证评估闭环

本文档遵循最小可验证改造原则：

- 先保留现有会话级 RAG 边界和数据模型
- 先升级检索决策，不先替换底层向量存储
- 先做可灰度、可回滚、可打点评估的增量方案

一句话定义本次改动：

> 在当前会话存在附件时，系统不能再“默认就查”；必须先做可解释、可回滚的检索决策，再决定是否进入 RAG。

## 2. 当前现状

当前项目已经具备可工作的会话内 RAG，关键事实如下：

- embedding 持久化在 `KnowledgeChunk.embedding_json`
- 检索范围限制为 `owner + conversation + completed knowledge documents`
- `backend/apps/chat/services.py` 负责消息级检索前置判断
- `backend/ai/retrieval.py` 负责按当前会话和 `embedding_backend` 做检索
- `backend/ai/vectorstores.py` 负责应用层相似度计算和词面复排

当前系统已经有两层收敛机制：

1. 明显寒暄/感谢/确认类短消息直接跳过检索
2. 短 query 必须命中词面信号才能进入 `used_chunks`

这套机制解决了第一波误检索，但仍然是“规则挡板 + 分数阈值”的 MVP 方案。

## 3. 当前问题

### 3.1 文档无关 query 仍会误触发检索

当前最核心的问题不是“文档相关问题检不出来”，而是“当前会话里只要有附件，一些与附件无关的问题也在走 RAG”。

典型样例：

- `Is there a large block behind a pyramid 翻译一下`
- `解释一下 TCP 三次握手`
- `今天星期几`
- `帮我写一个 Python 冒泡排序`

这类 query 的共同点是：

- 问题本身不依赖当前会话附件
- 即使当前会话里有文档，也不应该默认触发检索
- 是否是翻译、问答、代码、聊天并不是关键，关键是它和文档没有关联

以下类型 query 仍容易被错误触发或错误跳过：

- 模糊文件问法：`这份文档主要讲什么`
- 上下文承接问法：`那上面实验步骤是哪些`
- 弱指代问法：`附件里有没有这个`
- 轻任务问法：`帮我整理一下刚上传的内容`

真正难点是：系统需要区分“这条消息是否与当前附件集合有关”，而不是只看“会话里是否存在附件”。

### 3.2 决策只有二态，没有“不确定态”

当前逻辑只有：

- 检索
- 不检索

这会导致系统在边界 query 上要么过于激进，要么过于保守。

### 3.3 没有独立的检索决策评估闭环

当前系统能记录检索结果，但还不能系统回答下面这些问题：

- 哪些 query 本该检索却没检索
- 哪些 query 不该检索却触发了检索
- 检索命中后，证据是否真的帮助回答

### 3.4 现有相似度阈值不等于“是否该检索”

`RAG_MIN_SCORE` 解决的是“chunk 能不能进入结果”，不是“这条 query 是否值得先做检索”。

两者属于不同层级的问题，不能再继续混用。

## 4. 升级目标

### 4.1 产品目标

让 AI 对“是否需要使用当前会话文档知识”做出更稳定、更低误判的决定，尤其优先避免文档无关 query 误触发 RAG。

### 4.2 业务目标

- 显著降低与当前附件无关 query 的误检索
- 降低“当前会话有附件，所以什么问题都去查一下”的错误倾向
- 保持明确文档问答场景仍能正常触发检索
- 提高系统对“文档相关 / 文档无关 / 无法确定”三类状态的区分能力
- 为后续真实向量数据库升级保留接口边界

### 4.3 技术目标

- 在不改动会话归属和权限边界的前提下升级决策层
- 保持现有 `services.py -> retrieval.py -> vectorstores.py` 主链路
- 为检索决策增加独立 metadata、日志和评估能力

### 4.4 成功指标

一期上线后至少观察以下指标：

- 检索决策准确率：人工标注集上优于当前规则版
- 误检索率：相比当前版本下降
- 文档无关 query 误检索率：相比当前版本显著下降
- 明确文档问答 query 召回率：不明显下降
- 平均响应延迟：不显著恶化
- 用户侧 `Sources used` 误出现频率下降

说明：

- 准确率、误检索率、漏检索率必须建立在一份真实 query 标注集上评估
- 如果没有标注集，任何“更智能”都只能算主观感受

建议把一期验收先收敛成 3 个硬指标：

1. 文档无关 query 误检索率明显下降
2. 明确文档问答 query 召回不明显下降
3. 平均响应延迟不出现不可接受上升

## 5. 非目标

本阶段明确不做以下事项：

- 不直接切换到 `pgvector` / Qdrant / Milvus
- 不直接上完整 Self-RAG 多轮反思闭环
- 不做全局知识库或跨会话检索
- 不重写当前 chunk、embedding、权限和消息落库模型
- 不引入高复杂度训练流程作为首发方案

## 6. 外部方案调研结论

本方案参考以下 GitHub 项目，但只吸收适合当前代码基座的部分：

- [aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router)
  - 启发：先路由，再检索。适合拿来做“文档相关 / 无关 / 不确定”的前置判断。
- [AsH1605/Adaptive-RAG](https://github.com/AsH1605/Adaptive-RAG)
  - 启发：不要把所有 query 都走同一条检索路径，先判断再决定策略。
- [superlinear-ai/raglite](https://github.com/superlinear-ai/raglite)
  - 启发：检索是可选步骤，不是默认步骤。
- [AkariAsai/self-rag](https://github.com/AkariAsai/self-rag)
  - 启发：即使已取回候选证据，也可以再判断是否值得使用。

结合当前项目，结论很明确：

- 不适合直接照搬完整 Self-RAG
- 最有参考价值的是“route before retrieve”
- 当前最适合的最小方案是“文档相关性 gating + probe”

## 7. 目标方案

### 7.1 核心思路

最终目标态是把当前“检索 / 不检索”的二态判断，升级为“先判相关性，再决定是否检索”：

- `skip`：明显不需要检索
- `retrieve`：明显需要检索
- `probe`：不确定，先做低成本证据探测，再决定是否注入 RAG 上下文

这是本次升级最核心的产品变化。

但要强调：

- **这是目标态，不是一期必须一次性全部做满的实现形态**
- 一期先解决“当前会话有附件时，不要什么都查”
- 二期再把“文档相关 / 无关 / 不确定”的路由做得更稳定

### 7.2 决策接口

建议新增统一决策结果：

- `relatedness`: `related | unrelated | uncertain`
- `action`: `skip | retrieve | probe`
- `reason`: 短字符串，便于日志统计
- `probe_score`: 可选
- `judge_used`: `true | false`
- `decision_version`: 例如 `v1-fast-probe`、`v2-router`

系统行为只看这两个字段：

- `relatedness`
- `action`

这样接口足够小，后续实现可以替换，但上层调用方式不变。

补充约束：

- `relatedness` 是**解释字段**
- `action` 是**执行字段**
- 一期允许 `relatedness` 来源较粗，但 `action` 必须稳定、可测试

### 7.3 决策流程

目标态的检索决策分四层执行：

1. 规则快路径
2. 文档相关性路由
3. 探测式检索
4. 证据采用判断

#### 第一层：规则快路径

保留现有 `RETRIEVAL_SKIP_MESSAGES` 和上传提示语过滤。

这一层只负责拦截非常明确的低价值消息，不负责复杂判断。

输出：

- `relatedness = unrelated`
- `action = skip`

#### 第二层：文档相关性路由

新增一个检索路由器，对 query 和当前会话附件集合之间的关系做粗分类，输出：

- `document_related`
- `document_unrelated`
- `uncertain`

推荐实现候选：

- 不训练大模型
- 可以用 embedding + 少量示例语句做相关性路由
- 也可以用轻量 LLM / 小分类器做单轮 JSON 分类

但必须补一个实现约束：

> **同一个阶段只能选一种首发实现，不允许 PRD 保持 “embedding 或 LLM 都可以” 的开放态。**

原因很简单：

- 两种方案的延迟、失败模式、调参方式完全不同
- 如果不先定首发实现，评估结果不可比
- 一期验收会变成“方案切换”和“效果提升”纠缠在一起

路由器输入建议包括：

- 当前 query 文本
- 当前会话是否存在可用知识文档
- 最近一到三条消息是否提到“文档/附件/PDF/文件/材料/上面/这份”
- 当前会话最近是否刚上传附件
- 当前 query 是否包含明显的文档引用信号，例如“这份文档”“附件里”“根据上面的文件”“刚上传的 PDF”
- 当前 query 是否与附件名、附件主题词存在直接重叠

路由输出映射如下：

- `document_unrelated` -> `skip`
- `document_related` -> `retrieve`
- `uncertain` -> `probe`

#### 第三层：探测式检索

当路由结果为 `probe` 时，不直接把完整检索结果注入 prompt，而是先执行一次低成本探测：

- 检索 `top 1-3`
- 读取最高分 `score`
- 读取是否命中词面信号
- 判断是否存在“最近上传文件名命中”或“chunk 前段命中”

探测层输出：

- `probe_reject`
- `probe_accept`
- `probe_judge`

规则建议：

- 明显低分且无词面命中 -> `probe_reject`
- 分数足够高且词面/附件名命中明显 -> `probe_accept`
- 中间态 -> `probe_judge`

这里必须增加一个落地约束：

> **`probe` 的候选结果必须可复用到后续正式 `retrieve`，禁止同一轮消息重复做 query embedding 和重复扫描同一批 chunk。**

最低要求：

- `probe_current_conversation_knowledge()` 返回的候选结构应与正式检索共享同一批 `hit` 数据
- 如果 `probe_accept`，应直接复用 probe 结果构造 `used_chunks` / `sources`
- 如果后续进入 `judge`，也应复用 probe 的 `top hits`

原因：

- 当前 `backend/ai/retrieval.py` 已经会按 `embedding_backend` 生成 query embedding 并扫描 chunk
- 如果 `probe` 和 `retrieve` 各做一遍，一期很容易把延迟明显拉高
- 这会直接违背本 PRD 的延迟目标

#### 第四层：证据采用判断

仅对 `probe_judge` 进入一次轻量证据判断。

推荐首发方式：

- 用当前聊天模型做一个极短 JSON 判断
- 输入仅包含 query 和 `top 1-2` 个候选 chunk 摘要
- 输出 `use_context = yes/no`

这一步不是生成答案，而只是判断：

- 这些证据是否真的相关
- 是否足以说明“这条请求和当前附件有关”

如果 `yes`，则进入正常 RAG 回答。

如果 `no`，则按普通聊天回答。

这一层要明确不是一期必做项，而且必须带超时和失败语义：

- 超时或解析失败时，不允许中断主回答链路
- judge 失败时，必须降级到 `probe_accept` 或旧链路策略，不允许直接抛错给用户

### 7.4 最小可交付版本

一期不要把所有层都做满，最小可交付版本只要求：

1. 保留现有规则快路径
2. 增加显式 `probe` 路径
3. 增加一组**强触发 retrieve 信号**
4. `probe` 只基于分数和词面信号
5. 暂不接入 LLM judge
6. 暂不接入独立语义 router

一期的执行逻辑明确收敛为：

- 命中快路径跳过规则 -> `skip`
- 命中强文档信号 -> `retrieve`
- 当前会话有可用知识文档，但又不满足前两者 -> `probe`
- 当前会话没有可用知识文档 -> `skip`

一期可用的强触发信号建议只包含确定性特征：

- query 明确提到“文档 / 附件 / 文件 / PDF / 上面这份 / 刚上传的内容”
- query 与附件名出现直接重叠
- query 是对最近一条文档相关消息的强承接

这样能先验证主问题是否被解决，再决定是否继续加更复杂的路由层。

## 8. 功能设计

### 8.1 新增决策结果类型

建议新增检索决策结果结构：

- `decision`: `skip | retrieve | probe`
- `reason`: 机器可读原因
- `router_label`: 相关性路由标签
- `probe_score`: 探测阶段最高分
- `probe_used`: 是否进入探测
- `judge_used`: 是否进入证据判断
- `decision_version`: 当前决策版本

字段约束：

- 一期没有独立 router 时，`router_label` 可以为空
- 一期 `decision_version` 固定为 `v1-fast-probe`
- 二期引入 router 后，再升级为 `v2-router`

### 8.2 assistant 元数据扩展

当前 assistant 元数据已有：

- `sources`
- `used_chunks`
- `is_rag_answer`
- `rag_score`

建议补充：

- `retrieval_decision`
- `retrieval_reason`
- `retrieval_router_label`
- `retrieval_relatedness`
- `retrieval_probe_score`
- `retrieval_judge_used`
- `retrieval_decision_version`

这样历史消息回放时可以直接分析“为什么这次触发了或跳过了 RAG”。

这里要定边界，避免日志和消息元数据混用：

- `Message.metadata_json` 只保存**这次回复用户可回放的最终决策结果**
- 不把大段调试中间态、完整候选列表、模型判定原文塞进 message metadata
- 详细调试信息进入 `RetrievalLog` 或单独日志

### 8.3 检索日志扩展

建议扩展 `RetrievalLog` 或新增决策日志字段，记录：

- 原始 query
- 决策结果
- 路由标签
- 文档相关性判定
- 是否 probe
- 是否 judge
- 最终是否采用文档证据
- 命中 chunk ids
- 决策版本
- 各阶段耗时
- 失败阶段与降级原因

如果不先把日志打出来，后面无法客观调阈值。

建议直接在 PRD 里约定：

- assistant metadata 面向“历史消息回放”
- `RetrievalLog` 面向“评估与调参”
- 两者字段名尽量一致，但数据粒度不同

## 9. 代码改造范围

本次升级优先控制在以下范围内：

- `backend/apps/chat/services.py`
- `backend/ai/retrieval.py`
- 新增 `backend/ai/retrieval_gate.py`
- 可能少量补充 `backend/apps/chat/models.py`
- 可能少量补充 `backend/apps/chat/tests.py`

### 9.1 services 层改造

当前 `_should_retrieve_for_message()` 建议拆成两层：

- `_fast_skip_retrieval_message()`
- `_decide_document_relatedness()`
- `_decide_retrieval_strategy()`

`generate_assistant_reply()` 和流式链路共享同一套决策结果。

### 9.2 retrieval 层改造

在现有 `search_current_conversation_knowledge()` 之外，新增一个轻量探测接口，例如：

- `probe_current_conversation_knowledge()`

它只返回少量候选和分数，不构造完整参考块。

同时要求：

- `probe` 和正式 `retrieve` 使用同一套底层查询函数
- 底层查询函数应支持“返回原始 hits + 是否构造 sources/reference block”的分离
- 不允许因为新增 `probe` 而复制一份几乎相同的检索实现

### 9.3 新增 gate 模块

建议把路由、probe、judge 逻辑从 `services.py` 抽离到独立模块，避免把视图/服务层变成条件分发堆。

## 10. 分阶段实施

### Phase 1：`fast-skip + probe` 最小版

目标：

- 保留当前规则挡板
- 增加 `skip / retrieve / probe`
- 引入**强文档信号直达 `retrieve`**
- 其余有知识文档的场景先走 `probe`
- `probe` 只基于分数和词面信号，不调用额外 LLM judge
- 增加 metadata / `RetrievalLog` 扩展
- 增加结果复用，避免重复检索

验收标准：

- 主链路稳定
- 无权限回归
- assistant 元数据可看到决策结果
- 人工样本集上文档无关 query 误检索率下降
- 相比当前版本，平均响应延迟不出现明显上升

说明：

- **Phase 1 不引入独立语义 router**
- **Phase 1 不引入 LLM judge**
- Phase 1 的目标是先用最小复杂度压住误检索

### Phase 2：加入相关性路由

目标：

- 引入轻量相关性路由器
- 让与文档无关的问题更稳定地直接 `skip`
- 让关系不明确的问题进入 `probe`
- 首发时只能在“embedding router”与“LLM router”中二选一

验收标准：

- 比纯规则版文档无关误检索更低
- 明确文档问答召回不明显下降
- 平均延迟控制在可接受范围内

### Phase 3：加入证据判断

目标：

- 给 `probe` 中的中间态增加一次 `judge`
- 避免把“有点像”但实际没帮助的 chunk 注入 prompt

验收标准：

- `Sources used` 误展示频率进一步下降
- 文档问答相关 query 的回答支持性更稳定

说明：

- Phase 1 做完后就应该先评估，不要默认继续上 Phase 2/3
- 如果 Phase 1 已经明显压住误检索，后续阶段可以延后

## 11. 验收与评估方案

### 11.1 标注集要求

至少构建一份小型真实 query 标注集，建议首批 `100-200` 条，标签包括：

- 是否应检索
- 是否与当前会话附件相关
- 如果检索，是否期望出现来源展示

建议覆盖：

- 寒暄
- 普通闲聊
- 与文档无关的普通问题
- 与文档无关但会话里存在附件的问题
- 明确文档问答
- 模糊文档问答
- 上下文承接问法
- 文件定位类问法

### 11.2 核心指标

- `decision_accuracy`
- `false_retrieval_rate`
- `missed_retrieval_rate`
- `avg_probe_latency_ms`
- `rag_usage_rate`
- `gate_fallback_rate`

其中一期最重要的是前 3 个指标：

- `decision_accuracy`
- `false_retrieval_rate`
- `missed_retrieval_rate`

### 11.3 人工评审维度

- 这条消息本来该不该查附件
- 这条消息和当前附件是否真的有关
- 如果查了，检索片段是否真的有帮助
- 来源展示是否让用户感觉合理

### 11.4 验收样例

一期上线前，至少要用下面这类样例回归：

1. 会话里有附件，用户问无关问题 -> 不触发 RAG
2. 会话里有附件，用户明确问“这份文档讲什么” -> 触发 RAG
3. 会话里有附件，用户问弱指代问题“上面那个步骤是什么” -> `probe` 或 `retrieve`
4. 会话里没有附件，普通问题 -> 不触发 RAG
5. 会话里有多个附件，用户按文件名点名提问 -> 触发 RAG

## 12. 风险与约束

### 12.1 风险

- 相关性路由示例集太弱，会把边界 query 误分
- `probe` 阈值未校准，会产生新的误判
- LLM judge 如果提示设计不好，会增加延迟但收益有限
- 元数据和日志不全，会导致上线后无法调参

### 12.2 约束

- 仍必须遵守当前 `owner + conversation` 检索边界
- 仍必须保证用户消息、AI 消息和 `AgentRun` 一起落库
- 不能因为升级 gate 逻辑破坏 fallback 回复链路
- 不能因为新增 `probe` 造成同一轮消息重复 embedding / 重复扫描
- 任何 router / probe / judge 的失败都必须有明确降级路径

### 12.3 失败语义与降级规则

这一部分必须在开发前写死，避免实现分叉。

建议规则如下：

1. **fast-skip 失败**
   - 视为未命中快路径，继续后续决策

2. **Phase 1 probe 失败**
   - 降级到当前旧链路：沿用现有 `_should_retrieve_for_message()` 语义
   - 也就是说，只要不是明确寒暄/感谢/上传提示，就按旧逻辑允许正常检索

3. **Phase 2 router 失败或超时**
   - 不直接报错
   - 降级到 `Phase 1 fast-skip + probe` 逻辑

4. **Phase 3 judge 失败或超时**
   - 不直接报错
   - 降级到 `probe_accept` 结果或 `probe` 的默认接受策略

5. **任意 gate 组件解析异常**
   - 只影响本次是否注入 RAG，不影响消息保存、AI 回复、`AgentRun` 落库

超时预算建议：

- `probe`：必须低于一次完整回答链路的可接受增量预算
- `router` / `judge`：都必须设置显式超时，禁止无限等待
- 所有阶段耗时必须进日志，便于后续评估

## 13. 最终建议

本项目当前最值得做的不是立刻更换向量数据库，而是按下面顺序升级“是否使用 RAG”的决策：

1. 规则快挡板
2. `probe` 探测
3. 文档相关性路由
4. 必要时证据判断

这是对当前架构最小、最稳、最可验证的升级路径。

一句话总结：

> 第一阶段先把“当前会话有附件时，不要什么都查”解决掉；第二阶段再把“问题和附件到底是否有关”判断得更聪明。
