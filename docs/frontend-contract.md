# frontend/ 契约

本文档只约束 `frontend/` 下的实现。

## 目录职责

- `src/services/`：所有 API 调用封装。
- `src/contexts/`：登录态和全局状态。
- `src/pages/`：页面逻辑。
- `src/components/`：可复用 UI 组件。

## 实现规则

- 页面不要直接写网络请求，统一通过 `src/services/`。
- `apiClient.js` 负责基础请求、Token 注入和错误归一化。
- 登录态只能从 `AuthContext` 读取和修改。
- 新增接口时，先补 `services`，再接页面。
- 不要把后端返回的错误原文直接裸露给用户，优先做可读化处理。

## 安全规则

- 只允许在浏览器端保存必要的 `authToken`。
- 不要在前端代码中硬编码服务端密钥。
- 不要把 token、密码、完整请求体写入控制台日志。

## 验证规则

- 改页面、样式、路由、登录链路后，至少跑 `npm run build`。
- 改 `src/services/` 后，要手工验证对应 API 是否还兼容。
- 改 `apiClient.js` 或错误映射后，要检查所有页面的错误提示是否仍可读。
