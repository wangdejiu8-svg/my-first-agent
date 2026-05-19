# 用户认证功能实现

## 当前状态

认证已经从前端本地状态/mock 迁移到 Django 后端。

## 前端实现

- `frontend/src/contexts/AuthContext.js` 统一维护 `user`、`isLoggedIn`、`isAuthLoading`。
- `frontend/src/services/authApi.js` 封装注册、登录、登出、当前用户接口。
- `frontend/src/services/apiClient.js` 统一注入 `Authorization: Token <token>`。
- `LoginPage.js` 调用真实 `/api/auth/login/`。
- `RegisterPage.js` 调用真实 `/api/auth/register/`。

## 后端实现

- `backend/apps/accounts/` 提供注册、登录、登出、当前用户、设置和修改密码接口。
- 鉴权方式：DRF TokenAuthentication。
- 注册时创建 Django User，并初始化 `UserSettings`。
- 登录支持用户名或邮箱。
- 登出会删除当前用户 token。

## API 接口

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `POST /api/auth/change-password/`

## 验收测试

```bash
cd backend
.\.venv\Scripts\python.exe manage.py test
```

## 踩坑记录

- 当前本地开发使用 Token 鉴权，避免 React dev server 跨域调用 Django 时被 CSRF/Cookie 配置阻塞。
- 修改密码后后端会删除 token，前端需要引导用户重新登录。

## 2026-05-18 更新：认证页 UI 优化

- 登录页和注册页继续沿用原有浅色背景、黑色输入框阴影和蓝色渐变按钮，不更改色彩风格。
- 修复登录/注册页面中文乱码。
- 表单增加 `auth-form` 统一间距。
- 输入框增加 hover 阴影反馈和合理的 `autocomplete`。
- 卡片增加小屏响应式内边距。
- 登录页增加密码“显示/隐藏”切换，登录失败后不会清空密码，用户可显示密码检查输入。
- 前端 `apiClient` 会将认证失败、权限不足、资源不存在、网络连接失败等面向用户的错误统一转换为中文。
- 后端认证相关 serializer 校验错误已改为中文，包括用户名占用、邮箱占用、密码不一致、旧密码错误等。
