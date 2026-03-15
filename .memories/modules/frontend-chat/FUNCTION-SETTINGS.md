# 设置功能实现

## 功能概述

实现个人信息管理、账号安全、界面设置功能。

## 输入输出

### 输入
- 个人信息：用户名、头像、邮箱
- 密码修改：旧密码、新密码、确认新密码
- 界面设置：主题模式、语言、字体大小

### 输出
- 更新后的用户信息
- 设置保存成功提示

## 核心逻辑

### 1. 个人信息管理
- 修改用户名
- 上传头像图片
- 修改邮箱

### 2. 账号安全
- 输入旧密码验证
- 输入新密码和确认密码
- 提交修改

### 3. 界面设置
- 主题切换：浅色/深色
- 语言选择：中文/英文
- 字体大小：小/中/大

## 关键组件

### SettingsPage（设置页）
- Tab切换：个人信息、账号安全、界面设置
- 表单和保存按钮

### ThemeProvider（主题提供者）
- 管理全局主题状态
- 应用主题样式

## 关键代码

```javascript
// 更新个人信息
const updateProfile = async (data) => {
  const response = await api.updateProfile(data);
  localStorage.setItem('user', JSON.stringify(response.data));
};

// 修改密码
const changePassword = async (oldPassword, newPassword) => {
  await api.changePassword({ oldPassword, newPassword });
};

// 切换主题
const toggleTheme = (theme) => {
  localStorage.setItem('theme', theme);
  document.body.className = theme;
};
```

## API接口

- `PATCH /api/users/profile/` - 更新个人信息
- `POST /api/users/change-password/` - 修改密码
- `POST /api/users/upload-avatar/` - 上传头像

## 踩坑记录

待补充
