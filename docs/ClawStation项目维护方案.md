# ClawStation 项目维护说明

本文档总结当前仓库体现出来的维护方式，面向接手开发、日常排障、合并 PR 和测试服发布。

## 1. 项目维护定位

ClawStation 是一个前后端分离的 AI 员工管理与协作平台，维护重点不是单一前端或后端，而是四类服务的协同：

- `frontend/`: React 18 + Vite 前端应用，包含业务页面、路由、UI 基础组件、布局骨架和前端测试。
- `backend/`: FastAPI 后端，负责用户、工作台、工作区、资产库、AI runtime 网关、权限校验、数据库模型和 API。
- `ai_backend/`: LangGraph Agent Server，负责对话运行态、工具调用和模型运行。
- `ai-backend/`: 另一个 AI 辅助服务，目前主要服务 Excel/资产导入等专项 agent 能力。

项目维护的核心原则是：后端作为业务和权限入口，AI Runtime 作为运行面，前端只通过统一 API 封装访问后端；数据库变更通过 Alembic 迁移管理；PR 合并前依赖自动化测试和测试服验证。

## 2. 目录和职责边界

根目录主要文件：

- `README.md`: 项目总览、启动方式、环境变量和测试命令。
- `AGENTS.md` / `CLAUDE.md`: AI 协作开发规范，包含目录归属、PR 要求和文档同步要求。
- `CONTRIBUTING.md`: 分支、提交和 PR 基本规范。
- `docker-compose.yml`: 本地完整服务编排。
- `docker-compose.monitoring.yml`: Prometheus + Grafana 监控栈。
- `local-dev.ps1`: Windows 本地开发启动脚本。
- `deploy.sh`: 测试服部署脚本，由 GitHub Actions CD 调用。
- `.github/workflows/ci.yml`: PR 持续集成。
- `.github/workflows/cd.yml`: `test-run` 分支测试服部署。

主要代码目录：

- `frontend/src/api/`: 前端 API 封装，新增接口调用应优先放这里，避免页面里重复写请求逻辑。
- `frontend/src/components/ui/`: 基础 UI 组件，修改会影响较广，需要额外验证。
- `frontend/src/components/layout/`: 应用骨架层，承载导航、顶部区域和主内容布局。
- `frontend/src/pages/`: 业务页面层，是日常前端功能迭代的主要位置。
- `frontend/src/styles/`: 全局样式入口和页面级样式，设计 token 统一在 `--cs-*` 体系下维护。
- `backend/app/api/`: FastAPI 路由，新增 API 后需要注册到 `backend/app/main.py` 或对应聚合 router。
- `backend/app/models/`: SQLAlchemy 模型，模型变更必须配套迁移和 schema/service 更新。
- `backend/app/schemas/`: Pydantic 入参出参结构，需与模型和前端调用保持一致。
- `backend/app/services/`: 业务服务层，复杂逻辑应优先落在这里，而不是塞进路由函数。
- `backend/alembic/versions/`: Alembic 数据库迁移。
- `docs/`: API、数据库、CI/CD、监控、功能设计和专项 PRD。

## 3. 分支、提交和 PR 维护方式

当前仓库约定：

- `main`: 主分支，用于稳定代码。
- `test-run`: 测试开发/测试服部署分支，push 后会触发 CD。
- `feature/...`: 新功能分支。
- `fix/...`: 问题修复分支。

提交信息使用类似下面的格式：

```text
<type>(scope): description
```

常见 type：

- `feat`: 新功能
- `fix`: 修复问题
- `docs`: 文档
- `style`: 格式或样式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建、配置或杂项
- `merge`: 合并分支或解决冲突

PR 应包含：

- 问题分析过程。
- 改动位置和影响范围。
- 测试用例和通过情况。
- 前端改动的截图或视频，尤其是测试服验证截图。
- 如果修改 `README.md`、`AGENTS.md`、`CLAUDE.md` 等协作文档，需要说明原因。

## 4. 本地开发维护

### Docker 全量启动

适合验证完整服务链路：

```bash
docker compose up -d
```

常用地址：

- 前端: `http://localhost:3100`
- 后端: `http://localhost:8100`
- 后端 API 文档: `http://localhost:8100/docs`
- AI Runtime: `http://localhost:8200`
- PostgreSQL: `localhost:5433`
- Redis: `localhost:6379`

### Windows 本地开发脚本

项目提供 `local-dev.ps1`，用于 Windows 下启动常用开发组合：

```powershell
.\local-dev.ps1
```

它会：

- 停止 Docker 里的 `frontend` / `nginx`，避免 3100 端口冲突。
- 启动 Docker 中的 PostgreSQL 和 Redis。
- 确保 `clawstation_airuntime` 数据库存在。
- 启动后端 `uvicorn app.main:app --reload`。
- 启动前端 `npm run dev`。
- 启动 `ai_backend` 的 `langgraph dev`。
- 将日志写入 `artifacts/local-*-stdout.log` 和 `artifacts/local-*-stderr.log`。

### 手动启动前端

```bash
cd frontend
npm install
npm run dev
```

前端 Vite 默认端口是 `3100`，并通过 `/api` 和 `/uploads` 代理到后端。

### 手动启动后端

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8100
```

后端启动时会根据 `AUTO_INIT_DB_ON_STARTUP` 自动初始化数据库；PostgreSQL 环境下优先走 Alembic，SQLite 测试/本地场景会按需补建缺失表。

### 手动启动 AI Runtime

```bash
cd ai_backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
langgraph dev --host 0.0.0.0 --port 8200 --config langgraph.json
```

如果 `ai_backend/.env` 同时配置了 `DATABASE_URI` 和 `REDIS_URI`，本地脚本会尝试使用 postgres runtime edition；否则回退到 in-memory runtime。

## 5. 配置和环境变量维护

根目录 `.env.example` 给出后端、前端和 AI LLM 的基础配置。维护时重点关注：

- `DATABASE_URL`: 后端业务库连接，Docker 默认指向 `db:5432/clawstation`，本机常用 `localhost:5433/clawstation`。
- `SECRET_KEY`: 生产或测试服必须替换默认值。
- `FRONTEND_URL` / `FRONTEND_URLS`: CORS 允许来源。
- `BACKEND_PUBLIC_BASE_URL`: AI runtime 回调后端时使用的后端公开地址。
- `AI_AGENT_SERVER_URL`: 后端访问 LangGraph runtime 的地址。
- `AI_TOOL_BRIDGE_TOKEN`: 后端和 AI runtime 工具桥接 token，双方必须一致。
- `AI_LLM_PROVIDER` / `AI_LLM_BASE_URL` / `AI_LLM_API_KEY` / `AI_LLM_MODEL`: 后端直连 LLM 的统一配置。
- `VITE_API_URL`: 前端 API 基址，Docker nginx 场景一般使用 `/api`。

注意事项：

- 不要把真实 API key 提交到仓库。
- 测试服 CD 至少需要 `MINIMAX_API_KEY` 或 `OPENAI_API_KEY` 之一。
- 容器内访问服务时不要使用 `127.0.0.1` 指向宿主机，应该使用 compose 服务名或可达的公网/内网地址。

## 6. 数据库维护

数据库维护以 Alembic 为主：

- 模型定义在 `backend/app/models/`。
- schema 定义在 `backend/app/schemas/`。
- 迁移文件在 `backend/alembic/versions/`。
- Alembic 入口在 `backend/alembic/env.py`，会读取 `app.config.settings.DATABASE_URL`。

修改数据库结构时的维护流程：

1. 修改 SQLAlchemy model。
2. 同步更新 Pydantic schema、service 和相关 API。
3. 新增 Alembic migration。
4. 本地执行迁移或启动后端验证。
5. 补充或更新 pytest。
6. 必要时更新 `docs/DATABASE.md` 和 OpenAPI。

常用命令：

```bash
cd backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

历史上项目同时存在过 `backend/migrations/*.sql` 和 Alembic 文件；新结构应优先维护 Alembic。

## 7. 测试和质量门禁

### 前端测试

```bash
cd frontend
npm test -- --run
npm run build
npm run lint
npm run check:style-arch
```

前端测试栈：

- Vitest
- React Testing Library
- jsdom
- Playwright E2E

E2E 命令：

```bash
cd frontend
npm run test:e2e
```

Playwright 配置会启动：

- 后端: `127.0.0.1:8110`
- AI Runtime: `127.0.0.1:8210`
- 前端: `127.0.0.1:3110`

因此本地跑 E2E 前需要确保：

- `backend/.venv` 已安装 `backend/requirements.txt`。
- `ai_backend/.venv` 已安装 `ai_backend/requirements.txt`。
- Playwright 浏览器已安装。

### 后端测试

```bash
cd backend
pytest -v
pytest -v tests/test_main.py
```

CI 中会设置：

```bash
PYTEST_USE_REAL_RUNTIME=0
```

用于避免普通后端回归测试依赖真实 AI runtime。

### CI 当前执行内容

`.github/workflows/ci.yml` 在 PR 到 `main` 或 `test-run` 时执行：

- `frontend-test`: Node 18，`npm ci`，`npm test -- --run`。
- `backend-test`: Python 3.11，安装后端依赖，先跑 AI backend 回归子集，再跑完整 pytest。
- `fullstack-e2e`: 安装前端、后端、AI runtime 依赖和 Playwright Chromium，执行 `npm run test:e2e`。

## 8. 发布和测试服维护

CD 由 `.github/workflows/cd.yml` 维护：

- 触发条件：push 到 `test-run`，或 GitHub Actions 手动 `workflow_dispatch`。
- 部署方式：GitHub Actions 通过 SSH 登录测试服，进入 `~/project/clawstation`，执行 `DEPLOY_BRANCH=<branch> ./deploy.sh`。
- 并发控制：`cd-test-server`，新的部署会取消正在运行的旧部署。

测试服所需 secrets：

- `SSH_PRIVATE_KEY`
- `TEST_SERVER_HOST` 或 `SSH_HOST`
- `TEST_SERVER_PORT` 或 `SSH_PORT`
- `TEST_SERVER_USER` 或 `SSH_USER`
- `MINIMAX_API_KEY` 或 `OPENAI_API_KEY`

`deploy.sh` 负责：

- 同步 `test-run` 最新代码。
- 安装前端、后端和 AI runtime 依赖。
- 生成或更新 `backend/.env` 和 `ai_backend/.env`。
- 创建或校验业务库 `clawstation` 和 AI runtime 库 `clawstation_airuntime`。
- 启动 FastAPI、Vite、LangGraph AI runtime 和监控栈。
- 优先使用 `langgraph up --postgres-uri`，Docker 不可用时回退到 `langgraph dev`。
- 执行 health check 和真实 backend -> LangGraph -> model smoke test，避免误回落到本地 mock。

## 9. 监控维护

后端通过 `prometheus-fastapi-instrumentator` 暴露 `/metrics`，并排除 `/metrics`、`/docs`、`/redoc`、`/openapi.json` 等内部端点。

本地启动监控：

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

常用地址：

- Backend Metrics: `http://localhost:8100/metrics`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

监控文档在 `docs/METRICS.md` 和 `docs/METRICS_BEST_PRACTICES.md`。Grafana dashboard 位于 `monitoring/grafana/dashboards/clawstation-overview.json`。

## 10. API 和文档同步

后端 API 变更后应导出 OpenAPI：

```bash
cd backend
python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
```

需要同步更新文档的情况：

- 全局配置变化：更新 `README.md` 或本维护说明。
- 新增/调整 API：更新 `backend/openapi.json` 和 `docs/API.md`。
- 数据模型变化：更新 Alembic migration 和 `docs/DATABASE.md`。
- CI/CD 或部署逻辑变化：更新 `docs/CI_CD.md`。
- 监控指标或 dashboard 变化：更新 `docs/METRICS.md`。
- 前端基础组件、布局骨架或样式 token 变化：更新 `frontend/README.md` 或 `frontend/AGENTS.md`。

## 11. 高风险改动清单

以下改动需要扩大测试范围，并在 PR 中明确说明影响：

- 修改 `backend/app/models/`、`backend/app/database.py` 或 Alembic 迁移。
- 修改认证、用户中心、权限、资产库权限相关代码。
- 修改 `backend/app/main.py` 的中间件、异常处理、路由注册或 CORS。
- 修改 `AI_AGENT_SERVER_URL`、`AI_TOOL_BRIDGE_TOKEN`、`BACKEND_PUBLIC_BASE_URL` 等 AI runtime 联通配置。
- 修改 `frontend/src/components/ui/` 或 `frontend/src/components/layout/`。
- 修改 `frontend/src/router/`、登录守卫或 `frontend/src/utils/auth.js`。
- 修改 `deploy.sh`、GitHub Actions workflow 或 Docker Compose。
- 修改监控端口、Prometheus scrape 配置或 Grafana provisioning。

建议验证组合：

- 后端模型/API 改动：`cd backend && pytest -v`。
- 前端页面改动：`cd frontend && npm test -- --run && npm run build`。
- 路由、登录、工作区、AI 对话链路改动：补跑 `cd frontend && npm run test:e2e`。
- 部署脚本改动：在测试服或等价环境执行一次完整部署。

## 12. 日常维护检查清单

开发前：

- 从目标基线分支拉取最新代码。
- 确认当前任务属于前端、后端、AI runtime、部署或文档哪个边界。
- 查看相关 `AGENTS.md` 和现有测试，避免重复实现已有封装。

开发中：

- 前端请求统一走 `frontend/src/api/`。
- 后端复杂业务放在 service 层，路由层保持薄。
- 数据库结构变化必须有 migration。
- 不提交真实密钥、个人本地数据库、临时日志和测试截图以外的无关产物。

提交前：

- 跑与改动范围匹配的测试。
- 前端视觉改动保留截图或测试服验证证据。
- API 变更导出 OpenAPI。
- 文档与配置同步更新。
- 检查 `git status`，确认没有混入无关文件。

合并后：

- 需要测试服验证的改动合入 `test-run`。
- 查看 GitHub Actions CI/CD 结果。
- 部署失败时优先看 Actions 日志，其次看测试服上的 `frontend.log`、`backend.log`、`ai_backend.log`、`prometheus.log`、`grafana.log`。
