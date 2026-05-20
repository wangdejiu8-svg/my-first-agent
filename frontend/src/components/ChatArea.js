import React, { useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../services/apiClient';
import './ChatArea.css';

function ChatArea({
  sidebarVisible,
  onToggleSidebar,
  isLoggedIn,
  messages,
  error,
  isLoading,
  onSendMessage,
}) {
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const fileInputRef = useRef(null);

  const handleSend = async () => {
    if (!isLoggedIn) {
      setShowLoginPrompt(true);
      setTimeout(() => setShowLoginPrompt(false), 3000);
      return;
    }

    const content = input.trim();
    if ((!content && selectedFiles.length === 0) || isLoading) return;

    const filesToSend = selectedFiles;
    const messageContent = content || `上传了 ${filesToSend.length} 个文件`;

    setInput('');
    setSelectedFiles([]);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    try {
      await onSendMessage(messageContent, filesToSend);
    } catch (err) {
      setInput(content);
      setSelectedFiles(filesToSend);
    }
  };

  const handleFileChange = (event) => {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    setSelectedFiles(prev => {
      const existingKeys = new Set(prev.map(file => `${file.name}-${file.size}-${file.lastModified}`));
      const nextFiles = files.filter(file => !existingKeys.has(`${file.name}-${file.size}-${file.lastModified}`));
      return [...prev, ...nextFiles];
    });

    event.target.value = '';
  };

  const removeSelectedFile = (indexToRemove) => {
    setSelectedFiles(prev => prev.filter((_file, index) => index !== indexToRemove));
  };

  const formatFileSize = (size) => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / 1024 / 1024).toFixed(1)} MB`;
  };

  const getAttachmentUrl = (fileUrl) => {
    if (!fileUrl) return '#';
    if (/^https?:\/\//i.test(fileUrl)) return fileUrl;
    const baseUrl = API_BASE_URL.replace(/\/api\/?$/, '');
    const normalizedPath = fileUrl.startsWith('/') ? fileUrl : `/${fileUrl}`;
    return `${baseUrl}${normalizedPath}`;
  };

  return (
    <div className="chat-area">
      <button className="toggle-sidebar-btn" onClick={onToggleSidebar}>
        {sidebarVisible ? '◀' : '▶'}
      </button>
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h1>
              <span>我是一个轻量化 agent，</span>
              <span>有什么我能帮你的吗？</span>
            </h1>
          </div>
        ) : (
          messages.map((msg) => {
            const messageClass = msg.role === 'assistant' ? 'ai' : msg.role;
            return (
              <div key={msg.id} className={`message ${messageClass}`}>
                <div className="message-content">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {msg.attachments?.length > 0 && (
                    <div className="message-attachments">
                      {msg.attachments.map(attachment => (
                        <a
                          key={attachment.id}
                          className="message-attachment"
                          href={getAttachmentUrl(attachment.file)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <span className="attachment-icon">📎</span>
                          <span>{attachment.original_name}</span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
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
          <div className="login-prompt">请先登录后使用</div>
        )}
        {error && <div className="login-prompt">{error}</div>}
        <div className="input-wrapper">
          {selectedFiles.length > 0 && (
            <div className="selected-files">
              {selectedFiles.map((file, index) => (
                <div className="selected-file" key={`${file.name}-${file.size}-${file.lastModified}`}>
                  <span className="selected-file-name">{file.name}</span>
                  <span className="selected-file-size">{formatFileSize(file.size)}</span>
                  <button
                    type="button"
                    className="remove-file-btn"
                    onClick={() => removeSelectedFile(index)}
                    aria-label={`移除 ${file.name}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
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
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx,.pdf"
                  multiple
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                />
                <svg stroke="currentColor" fill="none" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
                </svg>
              </label>
            </div>
            <button className="send-btn" onClick={handleSend} disabled={(!input.trim() && selectedFiles.length === 0) || isLoading}>
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
