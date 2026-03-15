// Mock API 服务
const mockConversations = [
  { id: 1, title: '如何学习 React？', createdAt: '2026-03-15' },
  { id: 2, title: 'Python 数据分析', createdAt: '2026-03-14' },
  { id: 3, title: 'JavaScript 异步编程', createdAt: '2026-03-13' }
];

const mockMessages = {
  1: [
    { id: 1, role: 'user', content: '如何学习 React？' },
    { id: 2, role: 'ai', content: '学习 React 可以从以下几个方面入手：\n\n1. **基础知识**：先掌握 JavaScript ES6+ 语法\n2. **官方文档**：阅读 React 官方文档\n3. **实践项目**：动手做一些小项目\n4. **学习生态**：了解 React Router、Redux 等' }
  ],
  2: [
    { id: 3, role: 'user', content: 'Python 数据分析' },
    { id: 4, role: 'ai', content: 'Python 数据分析主要使用以下库：\n\n- **Pandas**：数据处理\n- **NumPy**：数值计算\n- **Matplotlib**：数据可视化\n- **Seaborn**：统计图表' }
  ]
};

export const mockApi = {
  // 获取对话列表
  getConversations: () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ data: mockConversations });
      }, 300);
    });
  },

  // 获取对话消息
  getMessages: (conversationId) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ data: mockMessages[conversationId] || [] });
      }, 300);
    });
  },

  // 发送消息
  sendMessage: (conversationId, content) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const aiResponse = {
          id: Date.now(),
          role: 'ai',
          content: '这是 AI 的模拟回复。实际应用中，这里会调用真实的 AI API。'
        };
        resolve({ data: aiResponse });
      }, 1000);
    });
  },

  // 创建新对话
  createConversation: (title) => {
    return new Promise((resolve) => {
      setTimeout(() => {
        const newConv = {
          id: Date.now(),
          title: title || '新对话',
          createdAt: new Date().toISOString()
        };
        mockConversations.unshift(newConv);
        resolve({ data: newConv });
      }, 300);
    });
  }
};
