const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api';
const CSRF_COOKIE_NAME = 'csrftoken';

export async function apiRequest(path, options = {}) {
  const { headers } = buildRequestOptions(options);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      credentials: 'include',
      headers,
    });
  } catch (error) {
    throw new Error('无法连接到服务端，请确认后端服务已启动');
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = normalizeApiError(data, response.status);
    const requestError = new Error(detail);
    requestError.status = response.status;
    requestError.data = data;
    throw requestError;
  }
  return data;
}

export async function apiStreamRequest(path, options = {}) {
  const { headers } = buildRequestOptions(options);
  const { onLine, ...requestOptions } = options;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      credentials: 'include',
      headers,
    });
  } catch (error) {
    throw new Error('无法连接到服务端，请确认后端服务已启动');
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = normalizeApiError(data, response.status);
    const requestError = new Error(detail);
    requestError.status = response.status;
    requestError.data = data;
    throw requestError;
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持流式回复');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed) {
        onLine?.(trimmed);
      }
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    onLine?.(buffer.trim());
  }
}

function normalizeApiError(data, status) {
  const rawMessage = extractErrorMessage(data);
  if (status === 401) return '请先登录后再操作';
  if (status === 403) {
    if (String(rawMessage).includes('CSRF Failed')) {
      return '安全校验已失效，请刷新页面后重试';
    }
    return '你没有权限执行此操作';
  }
  if (status === 404) return '请求的内容不存在或已被删除';
  if (status >= 500) return '服务端暂时不可用，请稍后重试';

  if (!rawMessage) return '请求失败，请稍后重试';
  return translateKnownError(rawMessage);
}

function shouldSendCsrfToken(method) {
  return !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method);
}

function buildRequestOptions(options = {}) {
  const method = String(options.method || 'GET').toUpperCase();
  const headers = {
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  };
  const csrfToken = shouldSendCsrfToken(method) ? readCookie(CSRF_COOKIE_NAME) : '';
  if (csrfToken && !headers['X-CSRFToken']) {
    headers['X-CSRFToken'] = csrfToken;
  }
  return { headers };
}

function readCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) return '';
  const target = `${name}=`;
  const matchedCookie = document.cookie
    .split(';')
    .map(chunk => chunk.trim())
    .find(chunk => chunk.startsWith(target));
  if (!matchedCookie) return '';
  return decodeURIComponent(matchedCookie.slice(target.length));
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
    'Only superusers can modify staff or superuser roles.': '只有超级管理员可以修改管理员角色',
    'Staff users can only manage non-privileged accounts.': '普通管理员只能管理非特权账号',
  };
  return knownMessages[text] || text;
}

export { API_BASE_URL };
