import { afterEach, describe, expect, it, vi } from 'vitest';

async function freshConfig() {
  vi.resetModules();
  return await import('./config');
}

describe('config', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllEnvs();
  });

  it('returns the default config before loadRuntimeConfig has resolved', async () => {
    const { getConfig, getAPIBaseURL } = await freshConfig();
    expect(getConfig()).toEqual({ API_BASE_URL: 'http://127.0.0.1:8000' });
    expect(getAPIBaseURL()).toBe('http://127.0.0.1:8000');
  });

  it('adopts the runtime config when /api/config returns JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ API_BASE_URL: 'https://runtime.example.com' }),
    }) as typeof fetch;

    const { loadRuntimeConfig, getConfig } = await freshConfig();
    await loadRuntimeConfig();
    expect(getConfig()).toEqual({ API_BASE_URL: 'https://runtime.example.com' });
  });

  it('ignores a non-JSON response and keeps the default after loading finishes', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'text/html' },
      json: async () => ({}),
    }) as typeof fetch;

    const { loadRuntimeConfig, getConfig } = await freshConfig();
    await loadRuntimeConfig();
    expect(getConfig()).toEqual({ API_BASE_URL: 'http://127.0.0.1:8000' });
  });

  it('falls back to default when the config endpoint responds with an error status', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as typeof fetch;

    const { loadRuntimeConfig, getConfig } = await freshConfig();
    await loadRuntimeConfig();
    expect(getConfig()).toEqual({ API_BASE_URL: 'http://127.0.0.1:8000' });
  });

  it('falls back to default when fetch throws', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down')) as typeof fetch;

    const { loadRuntimeConfig, getConfig } = await freshConfig();
    await loadRuntimeConfig();
    expect(getConfig()).toEqual({ API_BASE_URL: 'http://127.0.0.1:8000' });
  });

  it('config.API_BASE_URL getter reflects the current resolved config', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ API_BASE_URL: 'https://runtime.example.com' }),
    }) as typeof fetch;

    const { loadRuntimeConfig, config } = await freshConfig();
    await loadRuntimeConfig();
    expect(config.API_BASE_URL).toBe('https://runtime.example.com');
  });
});
