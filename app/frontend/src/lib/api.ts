import { createClient } from '@metagptx/web-sdk';
import { getAPIBaseURL } from './config';

// Create client instance with correct base URL
export const client = createClient({
  baseURL: getAPIBaseURL(),
});

// Add JWT token to all requests - comprehensive approach
const addAuthHeader = (config: Record<string, unknown>) => {
  const token = localStorage.getItem('access_token');
  console.log('🔧 DEBUG: Adding auth header, token exists:', !!token);
  if (token) {
    config.options = config.options || {};
    (config.options as Record<string, unknown>).headers = (config.options as Record<string, unknown>).headers || {};
    ((config.options as Record<string, unknown>).headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    console.log('🔧 DEBUG: Auth header added:', ((config.options as Record<string, unknown>).headers as Record<string, string>)['Authorization']);
  }
  return config;
};

// Override the main request method
const originalInvoke = client.apiCall.invoke;
client.apiCall.invoke = async function (config: Record<string, unknown>) {
  console.log('🔧 DEBUG: apiCall.invoke called with:', config);
  config = addAuthHeader(config);
  console.log('🔧 DEBUG: After adding auth header:', config);
  return originalInvoke.call(this, config);
};

// Also override any other request methods the SDK might use
if (client.apiCall.request) {
  const originalRequest = client.apiCall.request;
  client.apiCall.request = async function (config: Record<string, unknown>) {
    console.log('🔧 DEBUG: apiCall.request called with:', config);
    config = addAuthHeader(config);
    return originalRequest.call(this, config);
  };
}

// Override any HTTP methods if they exist
['get', 'post', 'put', 'delete', 'patch'].forEach(method => {
  if ((client.apiCall as any)[method]) {
    const originalMethod = (client.apiCall as any)[method];
    (client.apiCall as any)[method] = async function (url: string, config: Record<string, unknown> = {}) {
      console.log(`🔧 DEBUG: apiCall.${method} called with url:`, url, 'config:', config);
      config.url = url;
      config.method = method.toUpperCase();
      config = addAuthHeader(config);
      return originalMethod.call(this, config);
    };
  }
});

// Override entities methods specifically if they exist
if (client.entities) {
  Object.keys(client.entities).forEach(entityName => {
    const entity = (client.entities as any)[entityName];
    if (entity && typeof entity === 'object') {
      ['query', 'get', 'create', 'update', 'delete'].forEach(methodName => {
        if (typeof entity[methodName] === 'function') {
          const originalMethod = entity[methodName];
          entity[methodName] = async function (...args: any[]) {
            console.log(`🔧 DEBUG: entities.${entityName}.${methodName} called with:`, args);
            // If this is a config object, add auth headers
            if (args.length > 0 && typeof args[0] === 'object') {
              args[0] = addAuthHeader(args[0]);
            }
            return originalMethod.apply(this, args);
          };
        }
      });
    }
  });
}

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
  globalThis.location.href = '/login';
};

export const api = client;