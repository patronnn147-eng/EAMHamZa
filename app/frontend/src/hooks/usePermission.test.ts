import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseAuth = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

import {
  getPermissionMessage,
  useHasAllPermissions,
  useHasAnyPermission,
  useHasPermission,
  useUserRole,
} from './usePermission';

function setUser(role: string | null) {
  mockUseAuth.mockReturnValue({ user: role ? { role } : null });
}

beforeEach(() => {
  mockUseAuth.mockReset();
});

describe('useHasPermission', () => {
  it('denies when there is no logged-in user', () => {
    setUser(null);
    const { result } = renderHook(() => useHasPermission('planning:create'));
    expect(result.current).toBe(false);
  });

  it('grants a permission to an allowed role', () => {
    setUser('ADMIN');
    const { result } = renderHook(() => useHasPermission('planning:create'));
    expect(result.current).toBe(true);
  });

  it('denies a permission to a disallowed role', () => {
    setUser('TECHNICIEN');
    const { result } = renderHook(() => useHasPermission('planning:create'));
    expect(result.current).toBe(false);
  });

  it('allows a role listed among several allowed roles', () => {
    setUser('CHETOP');
    const { result } = renderHook(() => useHasPermission('workorder:create'));
    expect(result.current).toBe(true);
  });
});

describe('useUserRole', () => {
  it('returns null with no user', () => {
    setUser(null);
    const { result } = renderHook(() => useUserRole());
    expect(result.current).toBeNull();
  });

  it('returns the user role', () => {
    setUser('CHEFTECH');
    const { result } = renderHook(() => useUserRole());
    expect(result.current).toBe('CHEFTECH');
  });
});

describe('useHasAnyPermission', () => {
  it('denies with no user', () => {
    setUser(null);
    const { result } = renderHook(() => useHasAnyPermission(['planning:create', 'workorder:create']));
    expect(result.current).toBe(false);
  });

  it('grants when at least one permission matches the role', () => {
    setUser('TECHNICIEN');
    const { result } = renderHook(() => useHasAnyPermission(['planning:create', 'workorder:create']));
    expect(result.current).toBe(true);
  });

  it('denies when none of the permissions match the role', () => {
    setUser('TECHNICIEN');
    const { result } = renderHook(() => useHasAnyPermission(['planning:create', 'planning:approve']));
    expect(result.current).toBe(false);
  });
});

describe('useHasAllPermissions', () => {
  it('denies with no user', () => {
    setUser(null);
    const { result } = renderHook(() => useHasAllPermissions(['planning:read']));
    expect(result.current).toBe(false);
  });

  it('grants when the role satisfies every permission', () => {
    setUser('ADMIN');
    const { result } = renderHook(() =>
      useHasAllPermissions(['planning:create', 'planning:approve', 'workorder:close'])
    );
    expect(result.current).toBe(true);
  });

  it('denies when the role is missing at least one permission', () => {
    setUser('CHEFTECH');
    const { result } = renderHook(() =>
      useHasAllPermissions(['planning:submit', 'planning:approve'])
    );
    expect(result.current).toBe(false);
  });
});

describe('getPermissionMessage', () => {
  it('returns the specific message for a known permission', () => {
    expect(getPermissionMessage('planning:create')).toBe(
      "Seul l'administrateur peut créer un planning"
    );
  });

  it('falls back to the default message for an unmapped permission key', () => {
    expect(getPermissionMessage('intervention:validate' as any)).toBe(
      "Vous n'avez pas la permission de valider une intervention"
    );
  });
});
