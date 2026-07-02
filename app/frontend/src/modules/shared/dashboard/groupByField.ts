export interface GroupedDatum {
  name: string;
  value: number;
}

export function groupByField<T>(
  items: T[],
  getKey: (item: T) => string | null | undefined,
  labelMap: Record<string, string> = {},
  otherLabel = 'Other'
): GroupedDatum[] {
  const counts = new Map<string, number>();

  for (const item of items) {
    const rawKey = getKey(item);
    const key = rawKey ? (labelMap[rawKey] || rawKey) : otherLabel;
    counts.set(key, (counts.get(key) || 0) + 1);
  }

  return Array.from(counts.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}
