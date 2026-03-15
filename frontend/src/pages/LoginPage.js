import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import './AuthPage.css';

function LoginPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ username: '', password: '' });

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate('/');
  };

  return (
    <div className="auth-page">
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="auth-title">登录</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">用户名/邮箱</label>
            <input
              className="form-input"
              type="text"
              value={formData.username}
              onChange={e => setFormData({ ...formData, username: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">密码</label>
            <input
              className="form-input"
              type="password"
              value={formData.password}
              onChange={e => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>
          <button className="submit-btn" type="submit">
            <span className="submit-btn-inner">登录</span>
          </button>
        </form>
        <div className="auth-link">
          还没有账号？<a href="/register">去注册</a>
        </div>
      </motion.div>
    </div>
  );
}

export default LoginPage;
