export interface Delta {
  direction: 'up' | 'down' | 'flat';
  amount: number;
  label: string;
}

export function computeDelta(current: number, previous?: number): Delta {
  if (previous === undefined || previous === null || current === previous) {
    return { direction: 'flat', amount: 0, label: '–' };
  }
  const diff = current - previous;
  const amount = Math.abs(Math.round(diff));
  return diff > 0
    ? { direction: 'up', amount, label: `▲ ${amount}` }
    : { direction: 'down', amount, label: `▼ ${amount}` };
}
