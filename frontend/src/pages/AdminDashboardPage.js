import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { authApi } from '../services/authApi';
import { adminApi } from '../services/adminApi';
import './AdminDashboardPage.css';

const FILTERS = [
  { key: 'all', label: '全部用户' },
  { key: 'admins', label: '管理员' },
  { key: 'active', label: '启用中' },
];

function AdminDashboardPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [savingRowId, setSavingRowId] = useState(null);
  const [editingRowId, setEditingRowId] = useState(null);
  const [editingField, setEditingField] = useState(null);
  const [draftUser, setDraftUser] = useState(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [adminUser, userData] = await Promise.all([
          authApi.adminMe(),
          adminApi.listUsers(),
        ]);
        setCurrentUser(adminUser);
        setUsers(userData.users || []);
      } catch (_err) {
        navigate('/admin/login');
      } finally {
        setIsLoading(false);
      }
    };

    bootstrap();
  }, [navigate]);

  const totalUsers = users.length;
  const adminCount = useMemo(
    () => users.filter(user => user.is_staff || user.is_superuser).length,
    [users],
  );
  const activeCount = useMemo(
    () => users.filter(user => user.is_active).length,
    [users],
  );

  const filteredUsers = useMemo(() => {
    const text = query.trim().toLowerCase();
    return users.filter(user => {
      if (activeFilter === 'admins' && !(user.is_staff || user.is_superuser)) return false;
      if (activeFilter === 'active' && !user.is_active) return false;
      if (!text) return true;

      return [
        user.username,
        user.email,
        user.first_name,
        user.last_name,
        String(user.id),
      ]
        .filter(Boolean)
        .some(value => String(value).toLowerCase().includes(text));
    });
  }, [activeFilter, query, users]);

  const refreshUsers = async ({ silent = false } = {}) => {
    if (!silent) {
      setIsRefreshing(true);
    }
    const data = await adminApi.listUsers();
    setUsers(data.users || []);
    setIsRefreshing(false);
  };

  const startEditing = (user, field) => {
    setError('');
    setStatus('');
    if (editingRowId !== user.id) {
      setDraftUser({ ...user, password: '' });
    }
    setEditingRowId(user.id);
    setEditingField(field);
  };

  const updateDraftField = (field, value) => {
    setDraftUser(prev => ({ ...(prev || {}), [field]: value }));
  };

  const cancelEditing = () => {
    setEditingRowId(null);
    setEditingField(null);
    setDraftUser(null);
  };

  const saveRow = async () => {
    if (!draftUser?.id) return;
    setSavingRowId(draftUser.id);
    setError('');
    setStatus('');
    try {
      await adminApi.updateUser(draftUser.id, {
        username: draftUser.username,
        email: draftUser.email,
        first_name: draftUser.first_name,
        last_name: draftUser.last_name,
        is_active: draftUser.is_active,
        is_staff: draftUser.is_staff,
        is_superuser: draftUser.is_superuser,
        password: draftUser.password || '',
      });
      await refreshUsers({ silent: true });
      setStatus(`已更新用户 ${draftUser.username}`);
      cancelEditing();
    } catch (err) {
      setError(err.message || '保存失败');
    } finally {
      setSavingRowId(null);
    }
  };

  const handleDelete = async (user) => {
    if (!window.confirm(`确定删除用户 ${user.username} 吗？`)) return;
    setError('');
    setStatus('');
    try {
      await adminApi.deleteUser(user.id);
      await refreshUsers({ silent: true });
      if (editingRowId === user.id) {
        cancelEditing();
      }
      setStatus(`已删除用户 ${user.username}`);
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  const handleCellKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      saveRow();
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelEditing();
    }
  };

  const renderTextCell = (user, field, placeholder = '未填写') => {
    const isEditing = editingRowId === user.id && editingField === field;
    const value = editingRowId === user.id ? draftUser?.[field] ?? '' : user[field] ?? '';

    if (isEditing) {
      return (
        <input
          className="admin-inline-input"
          value={value}
          onChange={(event) => updateDraftField(field, event.target.value)}
          onKeyDown={handleCellKeyDown}
          autoFocus
        />
      );
    }

    return (
      <button
        type="button"
        className={`admin-cell-button ${value ? '' : 'is-empty'}`}
        onClick={() => startEditing(user, field)}
      >
        {value || placeholder}
      </button>
    );
  };

  const renderBooleanCell = (user, field) => {
    const isEditing = editingRowId === user.id && editingField === field;
    const value = editingRowId === user.id ? draftUser?.[field] : user[field];

    if (isEditing) {
      return (
        <select
          className="admin-inline-select"
          value={String(Boolean(value))}
          onChange={(event) => updateDraftField(field, event.target.value === 'true')}
          onKeyDown={handleCellKeyDown}
          autoFocus
        >
          <option value="true">是</option>
          <option value="false">否</option>
        </select>
      );
    }

    return (
      <button
        type="button"
        className={`admin-chip ${value ? 'is-true' : 'is-false'}`}
        onClick={() => startEditing(user, field)}
      >
        {value ? '是' : '否'}
      </button>
    );
  };

  const renderPasswordCell = (user) => {
    const isEditing = editingRowId === user.id && editingField === 'password';
    const value = editingRowId === user.id ? draftUser?.password ?? '' : '';

    if (isEditing) {
      return (
        <input
          className="admin-inline-input"
          type="password"
          value={value}
          onChange={(event) => updateDraftField('password', event.target.value)}
          onKeyDown={handleCellKeyDown}
          autoFocus
          placeholder="输入新密码"
        />
      );
    }

    return (
      <button
        type="button"
        className="admin-cell-button is-empty"
        onClick={() => startEditing(user, 'password')}
      >
        点击设置
      </button>
    );
  };

  if (isLoading) {
    return <div className="admin-page" />;
  }

  return (
    <div className="admin-page">
      <motion.div
        className="admin-shell"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <header className="admin-hero">
          <div className="admin-hero-copy">
            <div className="admin-eyebrow">Admin Control</div>
            <h1 className="admin-title">用户管理</h1>
            <p className="admin-subtitle">以表格为主工作区，点击任意值即可进入行内编辑，保存后立即同步到后端。</p>
          </div>
          <div className="admin-hero-side">
            <div className="admin-identity">
              <span className="admin-identity-label">当前管理员</span>
              <span className="admin-identity-value">{currentUser?.username || '-'}</span>
            </div>
            <div className="admin-hero-actions">
              <button
                type="button"
                className="admin-toolbar-btn"
                onClick={() => refreshUsers()}
                disabled={isRefreshing}
              >
                {isRefreshing ? '刷新中' : '刷新列表'}
              </button>
              <button
                type="button"
                className="admin-toolbar-btn is-dark"
                onClick={async () => {
                  await authApi.logout();
                  navigate('/admin/login');
                }}
              >
                退出
              </button>
            </div>
          </div>
        </header>

        <section className="admin-stats">
          <div className="admin-stat">
            <span className="admin-stat-label">用户总数</span>
            <span className="admin-stat-value">{totalUsers}</span>
          </div>
          <div className="admin-stat">
            <span className="admin-stat-label">启用账号</span>
            <span className="admin-stat-value">{activeCount}</span>
          </div>
          <div className="admin-stat">
            <span className="admin-stat-label">管理员</span>
            <span className="admin-stat-value">{adminCount}</span>
          </div>
        </section>

        <section className="admin-workspace">
          <div className="admin-toolbar">
            <div className="admin-search-wrap">
              <span className="admin-search-label">搜索</span>
              <input
                className="admin-search-input"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="用户名、邮箱、姓名、ID"
              />
            </div>
            <div className="admin-filter-group">
              {FILTERS.map(filter => (
                <button
                  key={filter.key}
                  type="button"
                  className={`admin-filter-pill ${activeFilter === filter.key ? 'is-active' : ''}`}
                  onClick={() => setActiveFilter(filter.key)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="admin-feedback is-error">{error}</div>}
          {status && <div className="admin-feedback is-success">{status}</div>}

          <div className="admin-table-meta">
            <span>当前显示 {filteredUsers.length} / {totalUsers}</span>
            <span>点击单元格可编辑，`Enter` 保存，`Esc` 取消</span>
          </div>

          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户名</th>
                  <th>邮箱</th>
                  <th>名</th>
                  <th>密码</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(user => {
                  const rowIsEditing = editingRowId === user.id;
                  const rowIsSaving = savingRowId === user.id;
                  return (
                    <tr key={user.id} className={rowIsEditing ? 'is-editing' : ''}>
                      <td className="admin-id-cell">{user.id}</td>
                      <td>{renderTextCell(user, 'username')}</td>
                      <td>{renderTextCell(user, 'email')}</td>
                      <td>{renderTextCell(user, 'first_name')}</td>
                      <td>{renderPasswordCell(user)}</td>
                      <td>
                        <div className="admin-row-actions">
                          {rowIsEditing ? (
                            <>
                              <button
                                type="button"
                                className="admin-action-btn is-primary"
                                onClick={saveRow}
                                disabled={rowIsSaving}
                              >
                                {rowIsSaving ? '保存中' : '保存'}
                              </button>
                              <button
                                type="button"
                                className="admin-action-btn"
                                onClick={cancelEditing}
                                disabled={rowIsSaving}
                              >
                                取消
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                className="admin-action-btn"
                                onClick={() => startEditing(user, 'username')}
                              >
                                编辑
                              </button>
                              <button
                                type="button"
                                className="admin-action-btn is-danger"
                                onClick={() => handleDelete(user)}
                                disabled={currentUser?.id === user.id}
                                title={currentUser?.id === user.id ? '不能删除当前管理员自己' : '删除用户'}
                              >
                                删除
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </motion.div>
    </div>
  );
}

export default AdminDashboardPage;
