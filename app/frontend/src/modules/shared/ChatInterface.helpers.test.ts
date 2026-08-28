import { describe, expect, it } from 'vitest';
import { filterVisibleSessions } from './ChatInterface';

const session = (id: string, message_count: number) => ({
  id,
  title: id,
  message_count,
});

describe('filterVisibleSessions', () => {
  it('keeps sessions that have at least one message', () => {
    const sessions = [session('a', 3), session('b', 1)];
    expect(filterVisibleSessions(sessions, null)).toEqual(sessions);
  });

  it('drops empty sessions that are not the current selection', () => {
    const sessions = [session('a', 3), session('b', 0)];
    expect(filterVisibleSessions(sessions, null)).toEqual([session('a', 3)]);
  });

  it('keeps an empty session when it is the current selection', () => {
    const sessions = [session('a', 3), session('b', 0)];
    expect(filterVisibleSessions(sessions, 'b')).toEqual(sessions);
  });

  it('keeps an empty session when another empty one is selected (only the selected one survives)', () => {
    const sessions = [session('a', 0), session('b', 0)];
    expect(filterVisibleSessions(sessions, 'b')).toEqual([session('b', 0)]);
  });
});
