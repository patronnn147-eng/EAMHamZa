// Runtime configuration
let runtimeConfig: {
  API_BASE_URL: string;
} | null = null;

// Configuration loading state
let configLoading = true;

// Default fallback configuration
const defaultConfig = {
  API_BASE_URL: 'http://127.0.0.1:8000', // Only used if runtime config fails to load
};

// Function to load runtime configuration
export async function loadRuntimeConfig(): Promise<void> {
  try {
    console.log('🔧 DEBUG: Starting to load runtime config...');
    // Try to load configuration from a config endpoint
    const response = await fetch('/api/config');
    if (response.ok) {
      const contentType = response.headers.get('content-type');
      // Only parse as JSON if the response is actually JSON
      if (contentType?.includes('application/json')) {
        runtimeConfig = await response.json();
        console.log('Runtime config loaded successfully');
      } else {
        console.log(
          'Config endpoint returned non-JSON response, skipping runtime config'
        );
      }
    } else {
      console.log(
        '🔧 DEBUG: Config fetch failed with status:',
        response.status
      );
    }
  } catch (error) {
    console.log('Failed to load runtime config, using defaults:', error);
  } finally {
    configLoading = false;
    console.log(
      '🔧 DEBUG: Config loading finished, configLoading set to false'
    );
  }
}

// Get current configuration
export function getConfig() {
  // Runtime config (fetched from /api/config, e.g. for Lambda) wins once loaded.
  if (runtimeConfig) {
    console.log('Using runtime config');
    return runtimeConfig;
  }

  // Vite env vars are baked in at build time -- known synchronously, so
  // there's no reason to wait on the async /api/config fetch for this.
  // Checked via !== undefined, not truthiness -- an explicitly empty
  // string means "same-origin relative paths" (e.g. behind nginx's own
  // /api/ proxy) and must be honored, not treated as "unset".
  if (import.meta.env.VITE_API_BASE_URL !== undefined) {
    const viteConfig = {
      API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
    };
    console.log('Using Vite environment config');
    return viteConfig;
  }

  // No Vite env var set -- still waiting on /api/config, or it came back
  // empty. Use the Lambda-oriented default either way.
  if (configLoading) {
    console.log('Config still loading, using default config');
  } else {
    console.log('Using default config');
  }
  return defaultConfig;
}

// Dynamic API_BASE_URL getter - this will always return the current config
export function getAPIBaseURL(): string {
  return getConfig().API_BASE_URL;
}

// For backward compatibility, but this should be avoided
// Removed static export to prevent using stale config values
// export const API_BASE_URL = getAPIBaseURL();

export const config = {
  get API_BASE_URL() {
    return getAPIBaseURL();
  },
};
