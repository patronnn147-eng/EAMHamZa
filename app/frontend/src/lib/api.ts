import { createClient } from '@metagptx/web-sdk';

// Create client instance
export const client = createClient();

// Add JWT token to all requests
const originalInvoke = client.apiCall.invoke;
client.apiCall.invoke = async function (config: Record<string, unknown>) {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.options = config.options || {};
    (config.options as Record<string, unknown>).headers = (config.options as Record<string, unknown>).headers || {};
    ((config.options as Record<string, unknown>).headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }
  return originalInvoke.call(this, config);
};

// Override auth.me to use JWT token from localStorage
const originalMe = client.auth.me;
client.auth.me = async function () {
  const token = localStorage.getItem('access_token');
  if (!token) {
    return { data: null };
  }

  try {
    const response = await client.apiCall.invoke({
      url: '/api/v1/auth/me',
      method: 'GET',
      options: {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      },
    });
    return { data: response.data };
  } catch (error) {
    // Token invalid or expired, clear storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    return { data: null };
  }
};

// Override logout to clear localStorage
client.auth.logout = async function () {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
};

export const api = client;