import { createClient } from '@metagptx/web-sdk';
import { getAPIBaseURL } from './config';

// Create client instance with correct base URL
export const client = createClient({
  baseURL: getAPIBaseURL(),
});

// Add JWT token to all requests - more robust approach
const injectToken = (config: any) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    // Some SDK versions use 'options', others use 'headers' directly
    config.options = config.options || {};
    config.options.headers = config.options.headers || {};
    config.options.headers['Authorization'] = `Bearer ${token}`;
    
    // Also inject directly into config if it's the top-level object used by fetch
    config.headers = config.headers || {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
};

// Override the main request method
const apiCall = client.apiCall as any;
const originalInvoke = apiCall.invoke;
apiCall.invoke = async function (config: any) {
  return originalInvoke.call(this, injectToken(config));
};

// Override all HTTP methods for safety
['get', 'post', 'put', 'delete', 'patch'].forEach(method => {
  if (apiCall[method]) {
    const originalMethod = apiCall[method];
    apiCall[method] = async function (url: string, config: any = {}) {
      config.url = url;
      config.method = method.toUpperCase();
      return originalMethod.call(this, injectToken(config));
    };
  }
});

// Override auth.me to provide consistent behavior
(client.auth as any).me = async function () {
  const token = localStorage.getItem('access_token');
  if (!token) return { data: null };

  try {
    const response = await apiCall.invoke({
      url: '/api/v1/auth/me',
      method: 'GET'
    });
    // Handle cases where the response itself is the user object or nested in .data
    const userData = response?.data || response;
    return { data: userData };
  } catch (error) {
    // If 401, token is definitely bad
    if (error?.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
    return { data: null };
  }
};

// Override logout
(client.auth as any).logout = async function () {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  globalThis.location.href = '/login';
};

export const api = client;
