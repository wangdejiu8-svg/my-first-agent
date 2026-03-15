import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import './SettingsPage.css';

function SettingsPage() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState({
    username: '用户名',
    email: 'user@example.com',
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    theme: 'dark',
    language: 'zh-CN',
    fontSize: 'medium'
  });

  return (
    <div className="settings-page">
      <motion.div
        className="settings-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <button className="back-btn" onClick={() => navigate('/')}>
          ← 返回
        </button>
        <h1 className="settings-title">设置</h1>

        <div className="settings-section">
          <h2 className="section-title">个人信息</h2>
          <div className="setting-item">
            <label className="setting-label">用户名</label>
            <input
              className="setting-input"
              value={settings.username}
              onChange={e => setSettings({ ...settings, username: e.target.value })}
            />
          </div>
          <div className="setting-item">
            <label className="setting-label">邮箱</label>
            <input
              className="setting-input"
              type="email"
              value={settings.email}
              onChange={e => setSettings({ ...settings, email: e.target.value })}
            />
          </div>
        </div>

        <div className="settings-section">
          <h2 className="section-title">账号安全</h2>
          <div className="setting-item">
            <label className="setting-label">旧密码</label>
            <input className="setting-input" type="password" />
          </div>
          <div className="setting-item">
            <label className="setting-label">新密码</label>
            <input className="setting-input" type="password" />
          </div>
          <div className="setting-item">
            <label className="setting-label">确认新密码</label>
            <input className="setting-input" type="password" />
          </div>
        </div>

        <div className="settings-section">
          <h2 className="section-title">界面设置</h2>
          <div className="setting-item">
            <label className="setting-label">主题</label>
            <select className="setting-input" value={settings.theme}>
              <option value="dark">深色</option>
              <option value="light">浅色</option>
            </select>
          </div>
          <div className="setting-item">
            <label className="setting-label">语言</label>
            <select className="setting-input" value={settings.language}>
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </div>
        </div>

        <button className="save-btn">保存设置</button>
      </motion.div>
    </div>
  );
}

export default SettingsPage;
