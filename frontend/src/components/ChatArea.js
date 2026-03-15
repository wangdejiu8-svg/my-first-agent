import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { mockApi } from '../services/mockApi';
import './ChatArea.css';

function ChatArea({ sidebarVisible, onToggleSidebar, isLoggedIn }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!isLoggedIn) {
      setShowLoginPrompt(true);
      setTimeout(() => setShowLoginPrompt(false), 3000);
      return;
    }
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    // 模拟 AI 回复
    const response = await mockApi.sendMessage(1, input);
    setMessages(prev => [...prev, response.data]);
    setIsLoading(false);
  };

  return (
    <div className="chat-area">
      <button className="toggle-sidebar-btn" onClick={onToggleSidebar}>
        {sidebarVisible ? '◀' : '▶'}
      </button>
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>有什么我能帮你的吗？</h1>
            <div className="prompt-cards">
              <div className="prompt-card" onClick={() => setInput('帮我写一封邮件')}>
                <span>✉️</span>
                <p>帮我写一封邮件</p>
              </div>
              <div className="prompt-card" onClick={() => setInput('解释量子力学')}>
                <span>🔬</span>
                <p>解释量子力学</p>
              </div>
              <div className="prompt-card" onClick={() => setInput('帮我写段Python代码')}>
                <span>💻</span>
                <p>帮我写段Python代码</p>
              </div>
              <div className="prompt-card" onClick={() => setInput('推荐一本好书')}>
                <span>📚</span>
                <p>推荐一本好书</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-content">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message ai">
            <div className="message-content">
              <span>正在输入...</span>
            </div>
          </div>
        )}
      </div>

      <div className="input-area">
        {showLoginPrompt && (
          <div style={{
            textAlign: 'center',
            marginBottom: '12px',
            padding: '12px',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid #ef4444',
            borderRadius: '8px',
            color: '#ef4444'
          }}>
            请先登录后使用
          </div>
        )}
        <div className="input-wrapper">
          <textarea
            className="input-box"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入消息..."
          />
          <div className="input-controls">
            <div className="input-controls-left">
              <label className="attach-btn">
                <input type="file" style={{ display: 'none' }} />
                <svg stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
              </label>
            </div>
            <button className="send-btn" onClick={handleSend} disabled={!input.trim()}>
              <svg stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                <path d="m22 2-7 20-4-9-9-4Z"></path>
                <path d="M22 2 11 13"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatArea;
