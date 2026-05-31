import React, { useLayoutEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { API_BASE_URL } from '../services/apiClient';
import './ChatArea.css';

const MAX_FALLBACK_CHUNKS = 3;
const MAX_SNIPPETS_PER_SOURCE = 2;
const BOTTOM_STICKY_THRESHOLD = 80;

const normalizeList = (value) => (Array.isArray(value) ? value : []);
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const normalizeRecordList = (value) => normalizeList(value).filter(isObject);
const formatRagScore = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return value.toFixed(3);
};

const summarizeSnippet = (text) => {
  if (typeof text !== 'string' && typeof text !== 'number') return '';
  const normalizedText = String(text).replace(/\s+/g, ' ').trim();
  if (normalizedText.length <= 140) return normalizedText;
  return `${normalizedText.slice(0, 140).trim()}...`;
};

const buildSourceDisplay = (message) => {
  const sources = normalizeRecordList(message.sources);
  const usedChunks = normalizeRecordList(message.used_chunks);
  const groupedUsedChunks = usedChunks.reduce((acc, chunk) => {
    const key = chunk.attachment_id ?? chunk.attachment_name ?? 'unknown';
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(chunk);
    return acc;
  }, {});

  if (sources.length > 0) {
    return sources.map((source) => {
      const sourceKey = source.attachment_id ?? source.attachment_name ?? 'unknown';
      const snippets = normalizeList(source.snippets)
        .map(summarizeSnippet)
        .filter(Boolean)
        .slice(0, MAX_SNIPPETS_PER_SOURCE);
      const fallbackSnippets = snippets.length > 0
        ? snippets
        : (groupedUsedChunks[sourceKey] || [])
          .map(chunk => summarizeSnippet(chunk.text))
          .filter(Boolean)
          .slice(0, MAX_FALLBACK_CHUNKS);

      return {
        key: sourceKey,
        attachmentName: source.attachment_name || 'Reference',
        chunkCount: source.chunk_count,
        snippets: fallbackSnippets,
      };
    });
  }

  return Object.values(
    usedChunks.reduce((acc, chunk) => {
      const key = chunk.attachment_id ?? chunk.attachment_name ?? `chunk-${chunk.chunk_index ?? 'unknown'}`;
      if (!acc[key]) {
        acc[key] = {
          key,
          attachmentName: chunk.attachment_name || 'Reference',
          chunkCount: 0,
          snippets: [],
        };
      }

      if (acc[key].snippets.length < MAX_FALLBACK_CHUNKS) {
        const snippet = summarizeSnippet(chunk.text);
        if (snippet) {
          acc[key].snippets.push(snippet);
        }
      }

      acc[key].chunkCount += 1;
      return acc;
    }, {})
  );
};

function ChatArea({
  sidebarVisible,
  onToggleSidebar,
  conversationId,
  scrollRequestKey,
  forceStickToBottom,
  isLoggedIn,
  messages,
  error,
  isLoading,
  onSendMessage,
}) {
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [showScrollToBottomButton, setShowScrollToBottomButton] = useState(false);
  const fileInputRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const scrollFrameRef = useRef(0);
  const shouldStickToBottomRef = useRef(true);
  const lastMessage = messages[messages.length - 1] || null;
  const lastMessageSignature = [
    lastMessage?.id || 'none',
    lastMessage?.content?.length || 0,
    lastMessage?.attachments?.length || 0,
    lastMessage?.sources?.length || 0,
    lastMessage?.used_chunks?.length || 0,
  ].join(':');
  const previousRenderStateRef = useRef({
    conversationId,
    messageCount: messages.length,
    isLoading,
    lastMessageSignature,
  });

  const isNearBottom = () => {
    const container = messagesContainerRef.current;
    if (!container) return true;

    return (
      container.scrollHeight - container.scrollTop - container.clientHeight
      <= BOTTOM_STICKY_THRESHOLD
    );
  };

  const scrollToBottom = (behavior = 'auto') => {
    const container = messagesContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
      container.scrollTo({ top: container.scrollHeight, behavior });
    }

    const scrollingElement = document.scrollingElement;
    if (scrollingElement) {
      scrollingElement.scrollTop = scrollingElement.scrollHeight;
      scrollingElement.scrollTo({ top: scrollingElement.scrollHeight, behavior });
    }
  };

  const scheduleScrollToBottom = (behavior = 'auto') => {
    if (scrollFrameRef.current) {
      cancelAnimationFrame(scrollFrameRef.current);
    }

    scrollFrameRef.current = requestAnimationFrame(() => {
      scrollToBottom(behavior);
      scrollFrameRef.current = requestAnimationFrame(() => {
        scrollToBottom(behavior);
      });
    });
  };

  useLayoutEffect(() => {
    const previousState = previousRenderStateRef.current;
    const isConversationChanged = previousState.conversationId !== conversationId;
    const hasNewContent = (
      previousState.messageCount !== messages.length
      || previousState.isLoading !== isLoading
      || previousState.lastMessageSignature !== lastMessageSignature
    );

    if (isConversationChanged) {
      shouldStickToBottomRef.current = true;
    }

    const shouldAutoScroll = forceStickToBottom || shouldStickToBottomRef.current;

    if (shouldAutoScroll && (isConversationChanged || hasNewContent)) {
      const behavior = (
        isConversationChanged
        || previousState.messageCount === messages.length
        || previousState.isLoading !== isLoading
      )
        ? 'auto'
        : 'smooth';
      scheduleScrollToBottom(behavior);
    }

    previousRenderStateRef.current = {
      conversationId,
      messageCount: messages.length,
      isLoading,
      lastMessageSignature,
    };
  }, [conversationId, isLoading, lastMessageSignature, messages.length]);

  useLayoutEffect(() => {
    if (forceStickToBottom || shouldStickToBottomRef.current) {
      scheduleScrollToBottom('auto');
    }
  }, [error, forceStickToBottom, selectedFiles.length, showLoginPrompt]);

  useLayoutEffect(() => {
    if (!scrollRequestKey) return;
    shouldStickToBottomRef.current = true;
    setShowScrollToBottomButton(false);
    scheduleScrollToBottom('auto');
  }, [scrollRequestKey]);

  useLayoutEffect(() => {
    if (!forceStickToBottom) return;
    setShowScrollToBottomButton(false);
  }, [forceStickToBottom]);

  useLayoutEffect(() => {
    const handleWindowResize = () => {
      if (forceStickToBottom || shouldStickToBottomRef.current) {
        scheduleScrollToBottom('auto');
      }
    };

    window.addEventListener('resize', handleWindowResize);
    return () => {
      window.removeEventListener('resize', handleWindowResize);
      if (scrollFrameRef.current) {
        cancelAnimationFrame(scrollFrameRef.current);
      }
    };
  }, [forceStickToBottom]);

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

  const handleMessagesScroll = () => {
    if (forceStickToBottom) {
      shouldStickToBottomRef.current = true;
      setShowScrollToBottomButton(false);
      return;
    }
    const nearBottom = isNearBottom();
    shouldStickToBottomRef.current = nearBottom;
    setShowScrollToBottomButton(!nearBottom);
  };

  const handleScrollToBottomClick = () => {
    shouldStickToBottomRef.current = true;
    setShowScrollToBottomButton(false);
    scheduleScrollToBottom('smooth');
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
      <div
        ref={messagesContainerRef}
        className="messages-container"
        onScroll={handleMessagesScroll}
      >
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
            const shouldShowSources = msg.role === 'assistant' && (
              normalizeRecordList(msg.sources).length > 0 || normalizeRecordList(msg.used_chunks).length > 0
            );
            const displayedSources = shouldShowSources ? buildSourceDisplay(msg) : [];
            const ragScore = formatRagScore(msg.rag_score);

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
                  {shouldShowSources && displayedSources.length > 0 && (
                    <div className="message-sources" aria-label="Answer sources">
                      <div className="message-sources-header">
                        <span className="message-sources-label">
                          {msg.is_rag_answer ? 'Sources used' : 'Related references'}
                        </span>
                        {ragScore && (
                          <span className="message-rag-score">RAG score {ragScore}</span>
                        )}
                      </div>
                      <div className="message-sources-list">
                        {displayedSources.map((source) => (
                          <div key={source.key} className="message-source-card">
                            <div className="message-source-meta">
                              <span className="message-source-name">{source.attachmentName}</span>
                              {typeof source.chunkCount === 'number' && source.chunkCount > 0 && (
                                <span className="message-source-count">{source.chunkCount} chunks</span>
                              )}
                            </div>
                            {source.snippets.length > 0 && (
                              <div className="message-source-snippets">
                                {source.snippets.map((snippet, index) => (
                                  <p
                                    key={`${source.key}-snippet-${index}`}
                                    className="message-source-snippet"
                                  >
                                    {snippet}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        {isLoading && lastMessage?.role !== 'assistant' && (
          <div className="message ai">
            <div className="message-content">
              <span>正在输入...</span>
            </div>
          </div>
        )}
      </div>

      {showScrollToBottomButton && (
        <button
          type="button"
          className="scroll-to-bottom-btn"
          onClick={handleScrollToBottomClick}
          aria-label="Scroll to latest message"
        >
          ↓
        </button>
      )}

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
