import { apiRequest } from './apiClient';

export const authApi = {
  register: (payload) =>
    apiRequest('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  login: (payload) =>
    apiRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  adminLogin: (payload) =>
    apiRequest('/auth/admin/login/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  adminMe: () => apiRequest('/auth/admin/me/'),

  logout: () =>
    apiRequest('/auth/logout/', {
      method: 'POST',
    }),

  me: () => apiRequest('/auth/me/'),
};
