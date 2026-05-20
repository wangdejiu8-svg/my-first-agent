# 用户认证功能实现

## 当前状态

认证已经从前端本地状态/mock 迁移到 Django 后端。

## 前端实现

- `frontend/src/contexts/AuthContext.js` 统一维护 `user`、`isLoggedIn`、`isAuthLoading`。
- `frontend/src/services/authApi.js` 封装注册、登录、登出、当前用户接口。
- `frontend/src/services/apiClient.js` 统一携带 Cookie 登录态，并在非只读请求里自动注入 `X-CSRFToken`。
- `LoginPage.js` 调用真实 `/api/auth/login/`。
- `RegisterPage.js` 调用真实 `/api/auth/register/`。

## 后端实现

- `backend/apps/accounts/` 提供注册、登录、登出、当前用户、设置和修改密码接口。
- 鉴权方式：DRF TokenAuthentication + HttpOnly Cookie，Cookie 身份的非只读请求需要通过 CSRF 校验。
- 注册时创建 Django User，并初始化 `UserSettings`。
- 登录支持用户名或邮箱。
- 登录会签发 `authToken` 与 `csrftoken`，登出和改密会删除当前用户 token 与相关 Cookie。

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

- 只要浏览器通过 Cookie 承载 token，就必须在前端补 `X-CSRFToken`，否则 `POST`、`PATCH`、`DELETE` 会被服务端按预期拦截。
- 修改密码后后端会删除 token，前端需要引导用户重新登录。

## 2026-05-20 更新：认证与后台安全边界

- 普通 `staff` 只能管理非特权账号，不能修改或删除 `staff/superuser`。
- 只有 `superuser` 可以修改 `is_staff`、`is_superuser`。
- 登录响应会同步发放 `csrftoken`，前端统一由 `apiClient` 自动注入 CSRF 请求头。

## 2026-05-18 更新：认证页 UI 优化

- 登录页和注册页继续沿用原有浅色背景、黑色输入框阴影和蓝色渐变按钮，不更改色彩风格。
- 修复登录/注册页面中文乱码。
- 表单增加 `auth-form` 统一间距。
- 输入框增加 hover 阴影反馈和合理的 `autocomplete`。
- 卡片增加小屏响应式内边距。
- 登录页增加密码“显示/隐藏”切换，登录失败后不会清空密码，用户可显示密码检查输入。
- 前端 `apiClient` 会将认证失败、权限不足、资源不存在、网络连接失败等面向用户的错误统一转换为中文。
- 后端认证相关 serializer 校验错误已改为中文，包括用户名占用、邮箱占用、密码不一致、旧密码错误等。
