import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import './Sidebar.css';

function Sidebar({
  user,
  isLoggedIn,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onLogout,
}) {
  const navigate = useNavigate();
  const [showMenu, setShowMenu] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [pendingDeleteConversation, setPendingDeleteConversation] = useState(null);
  const [isDeletingConversation, setIsDeletingConversation] = useState(false);
  const displayedConversations = conversations.slice(0, 20);

  useEffect(() => {
    if (!contextMenu) return undefined;

    const closeContextMenu = () => setContextMenu(null);
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        closeContextMenu();
      }
    };

    window.addEventListener('click', closeContextMenu);
    window.addEventListener('scroll', closeContextMenu, true);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('click', closeContextMenu);
      window.removeEventListener('scroll', closeContextMenu, true);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [contextMenu]);

  const handleNewConversation = async () => {
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    await onNewConversation();
  };

  const handleLogout = async () => {
    await onLogout();
    setShowMenu(false);
  };

  const handleConversationContextMenu = (event, conversation) => {
    event.preventDefault();
    setContextMenu({
      conversation,
      x: event.clientX,
      y: event.clientY,
    });
  };

  const handleDeleteConversation = () => {
    if (!contextMenu?.conversation) return;
    setPendingDeleteConversation(contextMenu.conversation);
    setContextMenu(null);
  };

  const handleConfirmDeleteConversation = async () => {
    if (!pendingDeleteConversation) return;
    setIsDeletingConversation(true);
    try {
      await onDeleteConversation(pendingDeleteConversation.id);
      setPendingDeleteConversation(null);
    } finally {
      setIsDeletingConversation(false);
    }
  };

  return (
    <motion.div
      className="sidebar"
      initial={{ x: -280 }}
      animate={{ x: 0 }}
      exit={{ x: -280 }}
      transition={{ type: 'spring', damping: 25 }}
    >
      <div className="sidebar-header">
        <button onClick={handleNewConversation} className="new-conversation-btn">
          + 新建对话
        </button>
      </div>

      <div className="sidebar-divider" />
      <div className="sidebar-note">仅显示最近 20 条历史对话</div>

      <div className="conversation-list">
        {isLoggedIn && displayedConversations.length === 0 && (
          <div className="conversation-empty">暂无历史对话</div>
        )}
        {displayedConversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelectConversation(conv.id)}
            onContextMenu={(event) => handleConversationContextMenu(event, conv)}
            className={`conversation-row ${activeConversationId === conv.id ? 'active' : ''}`}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span>{conv.title}</span>
          </button>
        ))}
        {contextMenu && (
          <div
            className="conversation-context-menu"
            style={{ left: contextMenu.x, top: contextMenu.y }}
            onClick={(event) => event.stopPropagation()}
          >
            <button onClick={handleDeleteConversation} className="danger">
              删除对话
            </button>
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        {!isLoggedIn ? (
          <button onClick={() => navigate('/login')} className="login-entry-btn">
            登录
          </button>
        ) : (
          <div className="user-menu-wrap">
            <button onClick={() => setShowMenu(!showMenu)} className="user-menu-trigger">
              <div className="user-avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
              <span>{user?.username || '用户'}</span>
            </button>
            {showMenu && (
              <div className="user-menu">
                <button onClick={() => navigate('/settings')}>设置</button>
                <button onClick={handleLogout} className="danger">退出登录</button>
              </div>
            )}
          </div>
        )}
      </div>

      {pendingDeleteConversation && (
        <div className="delete-dialog-backdrop" onClick={() => setPendingDeleteConversation(null)}>
          <div className="delete-dialog" onClick={(event) => event.stopPropagation()}>
            <div className="delete-dialog-title">删除对话</div>
            <div className="delete-dialog-message">
              确定要删除“{pendingDeleteConversation.title}”吗？此操作不会在侧边栏中继续显示该对话。
            </div>
            <div className="delete-dialog-actions">
              <button
                className="delete-dialog-cancel"
                onClick={() => setPendingDeleteConversation(null)}
                disabled={isDeletingConversation}
              >
                取消
              </button>
              <button
                className="delete-dialog-confirm"
                onClick={handleConfirmDeleteConversation}
                disabled={isDeletingConversation}
              >
                {isDeletingConversation ? '删除中...' : '删除'}
              </button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default Sidebar;
