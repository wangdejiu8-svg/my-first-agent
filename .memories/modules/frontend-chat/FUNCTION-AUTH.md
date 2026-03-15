# 用户认证功能实现

## 功能概述

实现用户注册、登录、登出功能。

## 输入输出

### 注册输入
- 用户名
- 邮箱
- 密码
- 确认密码

### 登录输入
- 用户名/邮箱
- 密码

### 输出
- 用户token
- 用户信息（用户名、头像、邮箱）

## 核心逻辑

### 1. 注册流程
1. 填写表单
2. 前端验证：邮箱格式、密码一致性
3. 提交到后端
4. 成功后跳转登录页

### 2. 登录流程
1. 输入用户名/邮箱和密码
2. 提交到后端验证
3. 保存token到localStorage
4. 跳转到主页
5. 更新左下角用户信息显示

### 3. 登出流程
1. 点击用户头像菜单中的"退出登录"
2. 清除token
3. 跳转到登录页

## 关键组件

### LoginPage（登录页）
- 表单：用户名/邮箱、密码
- 跳转注册链接

### RegisterPage（注册页）
- 表单：用户名、邮箱、密码、确认密码
- 跳转登录链接

### UserMenu（用户菜单）
- 显示头像和用户名
- 弹出菜单：设置、退出登录

## 关键代码

```javascript
// 登录
const login = async (username, password) => {
  const response = await api.login({ username, password });
  localStorage.setItem('token', response.data.token);
  localStorage.setItem('user', JSON.stringify(response.data.user));
  navigate('/');
};

// 注册
const register = async (username, email, password) => {
  await api.register({ username, email, password });
  navigate('/login');
};

// 登出
const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  navigate('/login');
};
```

## API接口

- `POST /api/auth/register/` - 用户注册
- `POST /api/auth/login/` - 用户登录
- `POST /api/auth/logout/` - 用户登出

## 验证规则

- 邮箱格式：正则验证
- 密码一致性：两次输入必须相同
- 非空验证：所有字段必填

## 踩坑记录

待补充
