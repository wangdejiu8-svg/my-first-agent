import React, { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import './AuthPage.css';

function getPasswordScore(password) {
  const checks = [
    /[a-z]/.test(password),
    /[A-Z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  return checks.filter(Boolean).length;
}

function getPasswordStrengthLabel(score) {
  if (score >= 4) return { key: 'strong', label: '强' };
  if (score >= 3) return { key: 'medium', label: '中' };
  return { key: 'weak', label: '弱' };
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const passwordScore = useMemo(() => getPasswordScore(formData.password), [formData.password]);
  const passwordStrength = getPasswordStrengthLabel(passwordScore);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!isValidEmail(formData.email)) {
      setError('请输入有效的邮箱地址');
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('两次密码不一致');
      return;
    }
    setIsSubmitting(true);
    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        confirm_password: formData.confirmPassword,
      });
      navigate('/login');
    } catch (err) {
      setError(err.message || '注册失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <h1 className="auth-title">注册</h1>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">用户名</label>
            <input
              className="form-input"
              type="text"
              autoComplete="username"
              value={formData.username}
              onChange={e => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">邮箱</label>
            <input
              className="form-input"
              type="email"
              autoComplete="email"
              value={formData.email}
              onChange={e => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">密码</label>
            <div className="password-field">
              <input
                className="form-input password-input"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(prev => !prev)}
                aria-label={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.8-2.27 2.27-4.19 4.13-5.52" />
                    <path d="M9.9 4.24A10.64 10.64 0 0 1 12 4c5 0 9.27 3.11 11 8a11.72 11.72 0 0 1-2.18 3.59" />
                    <path d="M14.12 14.12A3 3 0 0 1 9.88 9.88" />
                    <path d="M1 1l22 22" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
            {formData.password && (
              <div className={`password-hint strength-${passwordStrength.key}`}>
                密码强度：{passwordStrength.label}
              </div>
            )}
          </div>
          <div className="form-group">
            <label className="form-label">确认密码</label>
            <div className="password-field">
              <input
                className="form-input password-input"
                type={showConfirmPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={formData.confirmPassword}
                onChange={e => setFormData({ ...formData, confirmPassword: e.target.value })}
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(prev => !prev)}
                aria-label={showConfirmPassword ? '隐藏确认密码' : '显示确认密码'}
              >
                {showConfirmPassword ? (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12c.8-2.27 2.27-4.19 4.13-5.52" />
                    <path d="M9.9 4.24A10.64 10.64 0 0 1 12 4c5 0 9.27 3.11 11 8a11.72 11.72 0 0 1-2.18 3.59" />
                    <path d="M14.12 14.12A3 3 0 0 1 9.88 9.88" />
                    <path d="M1 1l22 22" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          {error && <div className="form-error">{error}</div>}
          <button className="submit-btn" type="submit" disabled={isSubmitting}>
            <span className="submit-btn-inner">{isSubmitting ? '注册中...' : '注册'}</span>
          </button>
        </form>
        <div className="auth-link">
          已有账号？<Link to="/login">去登录</Link>
        </div>
      </motion.div>
    </div>
  );
}

export default RegisterPage;
