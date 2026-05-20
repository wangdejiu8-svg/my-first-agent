# 前端 AI 对话应用模块

## 模块文档

- [PRD.md](./PRD.md) - 产品需求文档
- [FUNCTION-CHAT.md](./FUNCTION-CHAT.md) - 对话功能实现
- [FUNCTION-AUTH.md](./FUNCTION-AUTH.md) - 用户认证功能
- [FUNCTION-SETTINGS.md](./FUNCTION-SETTINGS.md) - 设置功能
- [FUNCTION-AI-AGENT.md](./FUNCTION-AI-AGENT.md) - LangGraph Agent 实现

## 当前状态

当前版本已经打通 React 前端、Django 后端、SQLite 数据库和 LangGraph Agent。

核心链路：

`React -> apiClient -> Django REST API -> Token Auth -> SQLite -> LangGraph -> DeepSeek-compatible LLM -> tools -> Django ORM`

## 文档约束

这个模块的文档要同步记录：

- 页面级交互和状态变化
- 后端 API 变化
- 安全边界变化
- 代码层新增的不变量
- 已验证的测试命令和踩坑记录

## 本地验证命令

```bash
cd backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test

cd ..\frontend
npm run build
```
