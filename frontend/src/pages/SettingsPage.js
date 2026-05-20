import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import { settingsApi } from '../services/settingsApi';
import './SettingsPage.css';

function SettingsPage() {
  const navigate = useNavigate();
  const { isLoggedIn, isAuthLoading, setUser } = useAuth();
  const [settings, setSettings] = useState({
    username: '',
    email: '',
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    theme: 'light',
    language: 'zh-CN',
    font_size: 'medium'
  });
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (isAuthLoading) return;
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }
    settingsApi
      .getSettings()
      .then(data => setSettings(prev => ({ ...prev, ...data })))
      .catch(err => setError(err.message));
  }, [isAuthLoading, isLoggedIn, navigate]);

  const updateField = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveSettings = async () => {
    setStatus('');
    setError('');
    try {
      const data = await settingsApi.updateSettings({
        username: settings.username,
        email: settings.email,
        theme: settings.theme,
        language: settings.language,
        font_size: settings.font_size,
      });
      setSettings(prev => ({ ...prev, ...data }));
      setUser(prev => prev ? { ...prev, username: data.username, email: data.email } : prev);
      setStatus('设置已保存');
    } catch (err) {
      setError(err.message || '保存失败');
    }
  };

  const handleChangePassword = async () => {
    setStatus('');
    setError('');
    if (!settings.oldPassword && !settings.newPassword && !settings.confirmPassword) {
      return;
    }
    try {
      await settingsApi.changePassword({
        old_password: settings.oldPassword,
        new_password: settings.newPassword,
        confirm_password: settings.confirmPassword,
      });
      setSettings(prev => ({
        ...prev,
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      }));
      setStatus('密码已修改，请重新登录');
    } catch (err) {
      setError(err.message || '密码修改失败');
    }
  };

  const handleSave = async () => {
    await handleSaveSettings();
    await handleChangePassword();
  };

  if (isAuthLoading) {
    return <div className="settings-page" />;
  }

  return (
    <div className="settings-page">
      <motion.div
        className="settings-container"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <button className="back-btn" onClick={() => navigate('/')}>
          <div className="back-btn-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" height="25px" width="25px">
              <path d="M224 480h640a32 32 0 1 1 0 64H224a32 32 0 0 1 0-64z" fill="#000000"></path>
              <path d="m237.248 512 265.408 265.344a32 32 0 0 1-45.312 45.312l-288-288a32 32 0 0 1 0-45.312l288-288a32 32 0 1 1 45.312 45.312L237.248 512z" fill="#000000"></path>
            </svg>
          </div>
          <span className="back-btn-text">返回</span>
        </button>
        <h1 className="settings-title">设置</h1>

        <div className="settings-section">
          <h2 className="section-title">个人信息</h2>
          <div className="setting-item">
            <label className="setting-label">用户名</label>
            <input
              className="setting-input"
              autoComplete="username"
              value={settings.username}
              onChange={e => updateField('username', e.target.value)}
            />
          </div>
          <div className="setting-item">
            <label className="setting-label">邮箱</label>
            <input
              className="setting-input"
              type="email"
              autoComplete="email"
              value={settings.email}
              onChange={e => updateField('email', e.target.value)}
            />
          </div>
        </div>

        <div className="settings-section">
          <h2 className="section-title">账号安全</h2>
          <div className="setting-item">
            <label className="setting-label">旧密码</label>
            <input
              className="setting-input"
              type="password"
              autoComplete="current-password"
              value={settings.oldPassword}
              onChange={e => updateField('oldPassword', e.target.value)}
            />
          </div>
          <div className="setting-item">
            <label className="setting-label">新密码</label>
            <input
              className="setting-input"
              type="password"
              autoComplete="new-password"
              value={settings.newPassword}
              onChange={e => updateField('newPassword', e.target.value)}
            />
          </div>
          <div className="setting-item">
            <label className="setting-label">确认新密码</label>
            <input
              className="setting-input"
              type="password"
              autoComplete="new-password"
              value={settings.confirmPassword}
              onChange={e => updateField('confirmPassword', e.target.value)}
            />
          </div>
        </div>

        <div className="settings-section">
          <h2 className="section-title">界面设置</h2>
          <div className="setting-item">
            <label className="setting-label">主题</label>
            <select
              className="setting-input"
              value={settings.theme}
              onChange={e => updateField('theme', e.target.value)}
            >
              <option value="light">浅色</option>
              <option value="dark">深色</option>
            </select>
          </div>
          <div className="setting-item">
            <label className="setting-label">语言</label>
            <select
              className="setting-input"
              value={settings.language}
              onChange={e => updateField('language', e.target.value)}
            >
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </div>
          <div className="setting-item">
            <label className="setting-label">字体大小</label>
            <select
              className="setting-input"
              value={settings.font_size}
              onChange={e => updateField('font_size', e.target.value)}
            >
              <option value="small">小</option>
              <option value="medium">中</option>
              <option value="large">大</option>
            </select>
          </div>
        </div>

        {error && <div className="settings-error">{error}</div>}
        {status && <div className="settings-status">{status}</div>}
        <button className="save-btn" onClick={handleSave}>保存设置</button>
      </motion.div>
    </div>
  );
}

export default SettingsPage;
