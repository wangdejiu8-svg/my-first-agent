import { apiRequest } from './apiClient';

export const settingsApi = {
  getSettings: () => apiRequest('/settings/'),

  updateSettings: (payload) =>
    apiRequest('/settings/', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  changePassword: (payload) =>
    apiRequest('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
