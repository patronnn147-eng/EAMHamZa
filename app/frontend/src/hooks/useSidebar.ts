import { useEffect, useState } from 'react';

const STORAGE_KEY = 'sidebar-collapsed';
const EVENT_NAME = 'sidebar-toggle';

function readInitial(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/**
 * Shared sidebar collapse state.
 * Uses localStorage for persistence and a window CustomEvent so every
 * component that calls useSidebar() stays in sync without a context provider.
 */
export function useSidebar() {
  const [collapsed, setCollapsed] = useState<boolean>(readInitial);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<boolean>).detail;
      if (typeof detail === 'boolean') setCollapsed(detail);
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  const setAndBroadcast = (value: boolean) => {
    try {
      localStorage.setItem(STORAGE_KEY, String(value));
    } catch {
      /* ignore quota / privacy errors */
    }
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: value }));
    setCollapsed(value);
  };

  return {
    collapsed,
    toggle: () => setAndBroadcast(!collapsed),
    setCollapsed: setAndBroadcast,
  };
}
