# 设置功能实现

## 当前状态

设置页已经接入 Django 后端，不再是静态表单。

## 前端实现

- `frontend/src/pages/SettingsPage.js` 未登录访问会跳转 `/login`。
- 进入页面后调用 `/api/settings/` 读取用户设置。
- 保存时调用 `/api/settings/` 更新用户名、邮箱、主题、语言和字体大小。
- 填写密码区域时调用 `/api/auth/change-password/`。
- `frontend/src/services/settingsApi.js` 封装设置读取、保存和修改密码接口。

## 后端实现

- `UserSettings` 字段：`theme`、`language`、`font_size`。
- `SettingsView` 支持 `GET /api/settings/` 和 `PATCH /api/settings/`。
- `SettingsView` 同时支持更新 Django User 的 `username` 和 `email`。
- `ChangePasswordView` 验证旧密码和两次新密码，修改成功后删除 token。

## API 接口

- `GET /api/settings/`
- `PATCH /api/settings/`
- `POST /api/auth/change-password/`

## 后续计划

- 主题设置目前只持久化到数据库，尚未全局应用到 CSS 变量。
- 头像上传模型已有 `Attachment` 基础，用户头像字段还未扩展。

## 2026-05-18 更新：页面尺寸统一

- `SettingsPage.css` 已将设置页容器调整为与登录/注册页一致的 420px 卡片宽度和 56px 内边距。
- 设置页标题、阴影、边框和按钮宽度对齐认证页视觉体系。
- `SettingsPage.js` 修复刷新设置页时认证状态尚未恢复就跳转登录页的问题，等待 `isAuthLoading` 结束后再判断登录态。
- 修复设置页中文乱码，并为输入项增加 `autocomplete`。
- 设置页保持原有色彩风格，仅优化层级、间距和响应式内边距。
