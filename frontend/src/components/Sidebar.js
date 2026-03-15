import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { mockApi } from '../services/mockApi';
import './Sidebar.css';

function Sidebar({ isLoggedIn, onLogout }) {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(1);
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    // 加载对话列表
    mockApi.getConversations().then(res => {
      setConversations(res.data);
    });
  }, []);

  const handleNewConversation = () => {
    mockApi.createConversation('新对话').then(res => {
      setConversations([res.data, ...conversations]);
      setActiveConvId(res.data.id);
    });
  };

  return (
    <motion.div
      className="sidebar"
      initial={{ x: -280 }}
      animate={{ x: 0 }}
      exit={{ x: -280 }}
      transition={{ type: 'spring', damping: 25 }}
    >
      <div style={{ padding: '16px' }}>
        <button onClick={handleNewConversation} style={{
          width: '100%',
          padding: '10px 12px',
          background: 'var(--accent-primary)',
          border: 'none',
          borderRadius: '6px',
          color: 'white',
          fontSize: '14px',
          fontWeight: '500',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
          transition: 'all 0.7s',
          zIndex: 30
        }}
        onMouseEnter={e => {
          const after = document.createElement('div');
          after.style.cssText = `
            position: absolute;
            width: 4px;
            height: 4px;
            background: var(--accent-hover);
            left: 50%;
            bottom: 0;
            transform: translateY(100%);
            border-radius: 50%;
            transition: all 0.7s;
            z-index: -20;
          `;
          e.currentTarget.appendChild(after);
          setTimeout(() => after.style.transform = 'scale(100)', 10);
        }}
        onMouseLeave={e => {
          const after = e.currentTarget.querySelector('div');
          if (after) after.remove();
        }}>
          + 新建对话
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
        {conversations.map(conv => (
          <div key={conv.id}
            onClick={() => setActiveConvId(conv.id)}
            style={{
            padding: '12px',
            margin: '4px 0',
            cursor: 'pointer',
            background: activeConvId === conv.id ? 'rgba(16, 163, 127, 0.1)' : 'transparent',
            borderRadius: '8px',
            transition: 'all 0.15s',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}
          onMouseEnter={e => {
            if (activeConvId !== conv.id) {
              e.currentTarget.style.background = 'rgba(16, 163, 127, 0.05)';
            }
          }}
          onMouseLeave={e => {
            if (activeConvId !== conv.id) {
              e.currentTarget.style.background = 'transparent';
            }
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={activeConvId === conv.id ? 'var(--accent-primary)' : 'currentColor'} strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <div style={{ fontSize: '14px', color: activeConvId === conv.id ? 'var(--accent-primary)' : 'var(--text-primary)', fontWeight: activeConvId === conv.id ? '500' : '400', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {conv.title}
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: '16px', borderTop: '1px solid var(--border-color)' }}>
        {!isLoggedIn ? (
          <button onClick={() => navigate('/login')} style={{
            width: '100%',
            padding: '10px',
            background: 'transparent',
            border: '1px solid var(--accent-primary)',
            borderRadius: '6px',
            color: 'var(--accent-primary)',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500',
            transition: 'all 0.2s'
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(16, 163, 127, 0.05)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
            登录
          </button>
        ) : (
          <div onClick={() => setShowMenu(!showMenu)} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            cursor: 'pointer',
            padding: '8px',
            borderRadius: '6px',
            background: showMenu ? 'var(--bg-tertiary)' : 'transparent',
            transition: 'background 0.15s'
          }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              background: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '500',
              fontSize: '14px',
              color: 'white'
            }}>U</div>
            <span style={{ fontSize: '14px' }}>用户名</span>
          </div>
        )}

        {showMenu && (
          <div style={{
            position: 'absolute',
            bottom: '70px',
            left: '12px',
            right: '12px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            overflow: 'hidden',
            boxShadow: '0 4px 12px var(--shadow-soft)'
          }}>
            <div onClick={() => navigate('/settings')} style={{
              padding: '12px 16px',
              cursor: 'pointer',
              fontSize: '14px',
              borderBottom: '1px solid var(--border-color)'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-tertiary)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>设置</div>
            <div onClick={onLogout} style={{
              padding: '12px 16px',
              cursor: 'pointer',
              color: '#ef4444',
              fontSize: '14px'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-tertiary)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>退出登录</div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default Sidebar;
