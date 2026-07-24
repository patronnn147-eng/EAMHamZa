import { describe, expect, it } from 'vitest';
import { getPriorityColor, getStatusColor } from './badges';

describe('getPriorityColor', () => {
  it.each([
    ['URGENTE', 'bg-red-100 text-red-800'],
    ['ÉLEVÉE', 'bg-orange-100 text-orange-800'],
    ['MOYENNE', 'bg-yellow-100 text-yellow-800'],
    ['BASSE', 'bg-green-100 text-green-800'],
  ])('maps %s to %s', (priority, expected) => {
    expect(getPriorityColor(priority)).toBe(expected);
  });

  it('falls back to gray for an unknown priority', () => {
    expect(getPriorityColor('WHATEVER')).toBe('bg-gray-100 text-gray-800');
  });
});

describe('getStatusColor', () => {
  it.each([
    ['PENDING_APPROVAL', 'bg-orange-100 text-orange-800'],
    ['APPROVED', 'bg-green-100 text-green-800'],
    ['DECLINED', 'bg-red-100 text-red-800'],
    ['REJECTED', 'bg-red-100 text-red-800'],
    ['EN_COURS', 'bg-blue-100 text-blue-800'],
    ['TERMINÉ', 'bg-green-100 text-green-800'],
    ['EN_ATTENTE', 'bg-yellow-100 text-yellow-800'],
    ['CRITIQUE', 'bg-red-100 text-red-800'],
    ['MAINTENANCE', 'bg-orange-100 text-orange-800'],
  ])('maps %s to %s', (status, expected) => {
    expect(getStatusColor(status)).toBe(expected);
  });

  it('falls back to gray for an unknown status', () => {
    expect(getStatusColor('WHATEVER')).toBe('bg-gray-100 text-gray-800');
  });
});
