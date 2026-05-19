import { apiRequest } from './apiClient';

export const adminApi = {
  listUsers: () => apiRequest('/auth/admin/users/'),
  updateUser: (userId, payload) =>
    apiRequest(`/auth/admin/users/${userId}/`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteUser: (userId) =>
    apiRequest(`/auth/admin/users/${userId}/`, {
      method: 'DELETE',
    }),
};
