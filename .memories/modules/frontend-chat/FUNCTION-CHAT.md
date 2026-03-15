# 对话功能实现

## 功能概述

实现AI对话交互，包括消息发送、接收、渲染和历史管理。

## 输入输出

### 输入
- 用户文本消息
- 上传的文件/图片
- 对话ID（切换历史对话时）

### 输出
- AI回复消息（支持Markdown）
- 对话历史列表
- 对话标题（自动生成）

## 核心逻辑

### 1. 消息发送流程
1. 用户输入文本（支持Shift+Enter换行，Enter发送）
2. 检查登录状态，未登录弹出提示
3. 发送消息到后端API
4. 显示用户消息和AI加载状态
5. 接收AI回复并渲染

### 2. 历史对话管理
- 首次发送消息自动创建对话
- 对话标题根据第一句话生成
- 支持点击标题重命名
- 点击历史对话切换当前对话

### 3. 沉浸模式
- 点击按钮隐藏左侧边栏
- 对话区全屏显示
- 再次点击恢复

## 关键组件

### ChatPage（主页）
- 左侧边栏：历史对话列表 + 用户信息
- 主对话区：顶部按钮 + 消息列表 + 输入框

### MessageList（消息列表）
- 渲染用户和AI消息
- 支持Markdown和代码高亮
- 消息操作：复制、重新生成

### InputBox（输入框）
- 多行文本输入
- 文件上传按钮
- 发送按钮

## 关键代码

```javascript
// ChatArea.js - 发送消息
const handleSend = () => {
  if (!isLoggedIn) {
    setShowLoginPrompt(true);
    setTimeout(() => setShowLoginPrompt(false), 3000);
    return;
  }
  if (!input.trim()) return;

  setMessages([...messages,
    { role: 'user', content: input },
    { role: 'ai', content: '这是 AI 的回复示例。' }
  ]);
  setInput('');
};

// Sidebar.js - 对话列表选中状态
const [activeConvId, setActiveConvId] = useState(1);
```

## UI/UX 实现细节

### 空状态设计
- 欢迎语："有什么我能帮你的吗？"
- 4个推荐卡片（邮件、量子力学、Python代码、推荐书籍）
- 点击卡片自动填充输入框

### 交互反馈
- 发送按钮：输入为空时自动禁用
- 输入框：获得焦点时显示绿色边框
- 推荐卡片：悬浮时上移 + 绿色阴影

### 视觉层级
- 侧边栏背景：#fafafa（浅灰）
- 主区域背景：#ffffff（纯白）
- 选中对话：浅绿色背景 + 绿色文字和图标

## API接口

- `POST /api/conversations/` - 创建新对话
- `POST /api/messages/` - 发送消息
- `GET /api/conversations/` - 获取对话列表
- `GET /api/conversations/{id}/messages/` - 获取对话消息
- `PATCH /api/conversations/{id}/` - 重命名对话

## 踩坑记录

### 1. 消息列表渲染错误
**问题**：messages.map 缺少闭合括号导致语法错误
**解决**：确保三元表达式的括号完整匹配

### 2. 按钮视觉层级混乱
**问题**：新建对话和登录按钮样式相同，用户无法区分主次
**解决**：登录改为幽灵按钮（透明底+绿边框），新建对话保持实心绿色

### 3. 空状态单调
**问题**：空白页面缺乏引导，用户不知道可以做什么
**解决**：添加4个推荐卡片，点击自动填充输入框

### 4. 输入框焦点反馈不明显
**问题**：用户点击输入框时没有明显的视觉反馈
**解决**：使用 :focus-within 伪类，聚焦时显示绿色边框

## 文件结构

```
frontend/src/
├── components/
│   ├── Sidebar.js/css       # 侧边栏（对话列表+用户信息）
│   ├── ChatArea.js/css      # 主对话区域
│   └── ConversationItem.css # 对话列表项样式
├── pages/
│   ├── ChatPage.js/css      # 主页
│   ├── LoginPage.js         # 登录页
│   ├── RegisterPage.js      # 注册页
│   ├── SettingsPage.js/css  # 设置页
│   └── AuthPage.css         # 认证页面通用样式
└── styles/
    └── globals.css          # 全局样式和CSS变量
```
