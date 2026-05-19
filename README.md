# AI 对话应用

一个基于 React + Django + LangGraph 的 AI 对话应用，提供用户认证、会话持久化、历史对话管理和真实模型调用能力。

## 项目概述

本项目是一个面向普通用户的AI对话应用，采用前后端分离架构。

- **前端技术栈**：React + HTML5 + CSS3 + JavaScript
- **后端技术栈**：Django + Django REST Framework + SQLite
- **AI 编排层**：LangGraph + LangChain OpenAI-compatible client
- **模型服务**：支持 DeepSeek 这类 OpenAI-compatible API

## 功能特性

### 核心功能
- ✅ AI对话交互（支持Markdown渲染、代码高亮）
- ✅ 历史对话管理（自动生成标题、支持重命名）
- ✅ 用户认证系统（注册、登录）
- ✅ 个人设置（信息管理、主题切换、语言选择）
- ✅ 文件上传功能
- ✅ 沉浸对话模式

### 页面结构
- **主页** (`/`) - 对话界面，包含左侧边栏和主对话区
- **登录页** (`/login`) - 用户登录
- **注册页** (`/register`) - 用户注册
- **设置页** (`/settings`) - 个人设置和偏好配置

## 文档

- [前端PRD文档](./前端PRD文档.md) - 详细的产品需求文档
- [后端架构文档](./Django-AI-Agent-后端架构文档.md) - 后端技术架构说明
- [后端服务说明](./backend/README.md) - 本地启动、API、数据库和 LangGraph 说明
- [后端代码约束](./docs/backend-contract.md) - 后端实现边界、安全规则和验证要求
- [前端代码约束](./docs/frontend-contract.md) - 前端实现边界、安全规则和验证要求
- [记忆文档系统](./.memories/) - 项目知识库和实现细节
- [项目契约](./AGENTS.md) - 全局代码边界、质量门禁和安全约束

## 项目契约

这个项目的代码约束不是只写在代码里，而是“代码 + 文档”一起维护。

- 前端请求统一走 `frontend/src/services/`。
- 后端复杂逻辑放在 `services.py` 和 `ai/`，视图层保持薄。
- 任何改动到认证、会话、附件、Agent、路由、配置的内容，都要同步更新文档。
- 每次完成开发后，记忆文档 `.memories/` 需要补充对应实现和踩坑记录。
- 密钥、token、密码、数据库内容不能写进日志或文档。

## 质量门禁

当前项目没有接入 `pytest`，后端以 Django 自带测试为准。

- 后端改动后至少执行 `manage.py check` 和 `manage.py test`。
- 前端改动后至少执行 `npm run build`。
- 涉及登录、会话、附件、AI 链路的改动，必须再做一次浏览器手工验证。
- 涉及模型、接口、环境变量的改动，必须同步更新对应文档。

## 当前目录结构

```text
my-first-agent/
├── frontend/                  # React 前端应用
│   └── src/
│       ├── components/        # 对话区、侧边栏等组件
│       ├── contexts/          # 登录态上下文
│       ├── pages/             # 登录、注册、设置、对话页面
│       └── services/          # 前端 API 封装
├── backend/                   # Django 后端服务
│   ├── ai/                    # LangGraph 编排层，不注册为 Django app
│   │   ├── tools/             # Agent 可调用工具
│   │   ├── graph.py           # StateGraph 定义
│   │   ├── runtime.py         # 统一运行入口
│   │   ├── llms.py            # 模型客户端工厂
│   │   └── prompts.py         # 系统提示词
│   ├── apps/
│   │   ├── accounts/          # 认证、用户设置
│   │   └── chat/              # 会话、消息、AgentRun
│   ├── config/                # Django 项目配置
│   └── manage.py
├── .memories/                 # 项目记忆文档
└── Django-AI-Agent-后端架构文档.md
```

## 核心调用链路

```text
React -> apiClient -> Django REST API -> Token Auth -> SQLite
      -> backend/ai/runtime.py -> LangGraph StateGraph
      -> DeepSeek-compatible LLM -> tools -> Django ORM
```

Django 仍然是业务数据和权限边界的唯一入口；LangGraph 只负责编排模型、工具和对话上下文。

## 记忆文档模块

本项目使用记忆文档系统来管理核心知识和实现细节，位于 `.memories/` 目录。

### 目录结构
```
.memories/
├── README.md              # 记忆系统说明
├── modules/               # 功能模块
│   ├── INDEX.md           # 模块索引
│   └── frontend-chat/     # 前端对话模块
│       ├── README.md      # 模块导航
│       ├── PRD.md         # 产品需求
│       └── FUNCTION-*.md  # 功能实现文档
├── templates/             # 文档模板
└── scripts/               # 速查脚本
```

### 使用规范

**重要：每次完成开发工作后，必须更新记忆文档！**

1. **新增功能** - 创建对应的 `FUNCTION-*.md` 文档
2. **修改功能** - 更新相关功能文档的实现细节
3. **踩坑经验** - 在"踩坑记录"章节记录问题和解决方案
4. **API变更** - 更新接口文档部分

记忆文档帮助团队快速了解项目，避免重复踩坑。

## 快速开始

### 前端启动

```bash
cd frontend
npm install
npm start
```

应用将在 http://localhost:3000 启动。

### 后端启动

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 8000
```

详见 [后端服务说明](./backend/README.md)。

## UI/UX 设计特点

- **简约现代风格** - 参考 ChatGPT 的设计语言
- **清晰的视觉层级** - 侧边栏与主区域色差分明
- **流畅的交互反馈** - 悬浮效果、选中状态、焦点高亮
- **引导式设计** - 空状态推荐卡片，降低使用门槛
- **响应式按钮** - 根据状态自动禁用/启用
- **立体输入框** - 黑色边框 + 阴影效果，聚焦时阴影增强
- **渐变按钮** - 蓝色渐变登录/注册按钮，动态交互效果
- **真实接口联调** - 前端通过 API 调用 Django 后端，不再依赖 mock 数据

## 项目状态

✅ 前端 UI 已完成并接入真实 API
✅ 用户认证、设置、会话和消息已持久化到 SQLite
✅ 后端已接入 LangGraph 编排层
✅ 支持 DeepSeek/OpenAI-compatible 模型配置
✅ 前后端基础联调已完成

## 版本信息

- 版本: v1.2
- 最后更新: 2026-05-18
