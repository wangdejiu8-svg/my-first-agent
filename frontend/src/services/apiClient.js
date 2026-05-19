const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';

export async function apiRequest(path, options = {}) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers,
    });
  } catch (error) {
    throw new Error('无法连接服务器，请确认后端服务已启动');
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = normalizeApiError(data, response.status);
    const error = new Error(detail);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function normalizeApiError(data, status) {
  if (status === 401) return '请先登录后再操作';
  if (status === 403) return '你没有权限执行此操作';
  if (status === 404) return '请求的内容不存在或已被删除';
  if (status >= 500) return '服务器暂时不可用，请稍后重试';

  const rawMessage = extractErrorMessage(data);
  if (!rawMessage) return '请求失败，请稍后重试';
  return translateKnownError(rawMessage);
}

function extractErrorMessage(data) {
  if (!data) return '';
  if (typeof data === 'string') return data;
  if (Array.isArray(data)) return data[0] || '';
  if (data.detail) return data.detail;
  if (data.non_field_errors?.[0]) return data.non_field_errors[0];

  const firstKey = Object.keys(data)[0];
  const firstValue = data[firstKey];
  if (Array.isArray(firstValue)) return firstValue[0];
  if (typeof firstValue === 'string') return firstValue;
  return '';
}

function translateKnownError(message) {
  const text = String(message);
  const knownMessages = {
    'This field is required.': '请填写必填项',
    'This field may not be blank.': '内容不能为空',
    'Enter a valid email address.': '请输入有效的邮箱地址',
    'A valid integer is required.': '参数格式不正确',
    'Invalid token.': '登录状态已失效，请重新登录',
    'Authentication credentials were not provided.': '请先登录后再操作',
    'Invalid username/email or password.': '用户名、邮箱或密码错误',
    'Username is already taken.': '用户名已被占用',
    'Email is already taken.': '邮箱已被占用',
    'Passwords do not match.': '两次密码不一致',
    'Old password is incorrect.': '旧密码不正确',
    'Conversation was not found.': '对话不存在或已被删除',
    'Missing file.': '请选择要上传的文件',
    'Only .docx and .pdf files are supported.': '仅支持上传 .docx 和 .pdf 文件',
  };
  return knownMessages[text] || text;
}

export { API_BASE_URL };
