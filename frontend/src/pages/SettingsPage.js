import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UserAvatar from '../components/UserAvatar';
import { useAuth } from '../contexts/AuthContext';
import { settingsApi } from '../services/settingsApi';
import './SettingsPage.css';

function SettingsPage() {
  const navigate = useNavigate();
  const { user, isLoggedIn, isAuthLoading, setUser } = useAuth();
  const [profile, setProfile] = useState({
    username: '',
    email: '',
  });
  const [savedProfile, setSavedProfile] = useState({
    username: '',
    email: '',
  });
  const [passwords, setPasswords] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  useEffect(() => {
    if (isAuthLoading) return;
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }

    settingsApi
      .getSettings()
      .then((data) => {
        const nextProfile = {
          username: data.username || '',
          email: data.email || '',
        };
        setProfile(nextProfile);
        setSavedProfile(nextProfile);
      })
      .catch((err) => setError(err.message || '设置加载失败'));
  }, [isAuthLoading, isLoggedIn, navigate]);

  const displayName = useMemo(
    () => profile.username || user?.username || '用户',
    [profile.username, user],
  );

  const isProfileDirty = useMemo(
    () => profile.username !== savedProfile.username || profile.email !== savedProfile.email,
    [profile, savedProfile],
  );

  const updateProfileField = (key, value) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
  };

  const updatePasswordField = (key, value) => {
    setPasswords((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveProfile = async () => {
    setStatus('');
    setError('');
    setIsSavingProfile(true);
    try {
      const data = await settingsApi.updateSettings({
        username: profile.username,
        email: profile.email,
      });
      const nextProfile = {
        username: data.username || '',
        email: data.email || '',
      };
      setProfile(nextProfile);
      setSavedProfile(nextProfile);
      setUser((prev) => (
        prev
          ? { ...prev, username: data.username, email: data.email }
          : prev
      ));
      setStatus('账户资料已更新');
    } catch (err) {
      setError(err.message || '保存失败');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    setStatus('');
    setError('');

    const hasAnyPasswordInput = Object.values(passwords).some(Boolean);
    if (!hasAnyPasswordInput) {
      setError('请先填写密码信息');
      return;
    }

    if (Object.values(passwords).some((value) => !value.trim())) {
      setError('请完整填写旧密码、新密码和确认密码');
      return;
    }

    setIsChangingPassword(true);
    try {
      await settingsApi.changePassword({
        old_password: passwords.oldPassword,
        new_password: passwords.newPassword,
        confirm_password: passwords.confirmPassword,
      });
      setPasswords({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
      setUser(null);
      navigate('/login');
    } catch (err) {
      setError(err.message || '密码修改失败');
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (isAuthLoading) {
    return (
      <div className="settings-page">
        <div className="settings-shell">
          <div className="settings-loading-card" />
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <div className="settings-shell">
        <header className="settings-header">
          <div className="settings-identity">
            <UserAvatar name={displayName || user?.email} size="lg" />
            <div className="settings-identity-text">
              <h1 className="settings-title">{displayName}</h1>
              <p className="settings-subtitle">账户与安全</p>
            </div>
            <button className="settings-back-link" onClick={() => navigate('/')}>
              返回对话
            </button>
          </div>
        </header>

        {error && <div className="settings-error">{error}</div>}
        {status && <div className="settings-status">{status}</div>}

        <section className="settings-section">
          <p className="settings-section-title">账号</p>
          <div className="settings-list">
            <label className="settings-item">
              <span className="settings-item-label">用户名</span>
              <input
                className="settings-input"
                autoComplete="username"
                value={profile.username}
                onChange={(e) => updateProfileField('username', e.target.value)}
              />
            </label>

            <label className="settings-item">
              <span className="settings-item-label">邮箱</span>
              <input
                className="settings-input"
                type="email"
                autoComplete="email"
                value={profile.email}
                onChange={(e) => updateProfileField('email', e.target.value)}
              />
            </label>

            <div className="settings-item settings-item-action">
              <span className="settings-item-label">资料保存</span>
              <button
                className="settings-action-button settings-action-button-primary"
                onClick={handleSaveProfile}
                disabled={!isProfileDirty || isSavingProfile || isChangingPassword}
              >
                {isSavingProfile ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </section>

        <section className="settings-section">
          <p className="settings-section-title">安全</p>
          <div className="settings-list">
            <label className="settings-item">
              <span className="settings-item-label">旧密码</span>
              <input
                className="settings-input"
                type="password"
                autoComplete="current-password"
                value={passwords.oldPassword}
                onChange={(e) => updatePasswordField('oldPassword', e.target.value)}
              />
            </label>

            <label className="settings-item">
              <span className="settings-item-label">新密码</span>
              <input
                className="settings-input"
                type="password"
                autoComplete="new-password"
                value={passwords.newPassword}
                onChange={(e) => updatePasswordField('newPassword', e.target.value)}
              />
            </label>

            <label className="settings-item">
              <span className="settings-item-label">确认新密码</span>
              <input
                className="settings-input"
                type="password"
                autoComplete="new-password"
                value={passwords.confirmPassword}
                onChange={(e) => updatePasswordField('confirmPassword', e.target.value)}
              />
            </label>

            <div className="settings-item settings-item-action">
              <span className="settings-item-label">密码更新</span>
              <button
                className="settings-action-button"
                onClick={handleChangePassword}
                disabled={isSavingProfile || isChangingPassword}
              >
                {isChangingPassword ? '提交中...' : '更新'}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default SettingsPage;
