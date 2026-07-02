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

/**
 * Relabel + recolor slices already grouped server-side. Multiple raw names
 * mapping to the same display label (e.g. "EN_ATTENTE" and "PENDING" both
 * -> "Pending") are merged into one slice.
 */
export function relabelSlices(
  slices: GroupedDatum[],
  labelMap: Record<string, string> = {},
  colorMap: Record<string, string> = {}
): (GroupedDatum & { color?: string })[] {
  const counts = new Map<string, number>();

  for (const { name, value } of slices) {
    const label = labelMap[name] || name;
    counts.set(label, (counts.get(label) || 0) + value);
  }

  return Array.from(counts.entries())
    .map(([name, value]) => ({ name, value, color: colorMap[name] }))
    .sort((a, b) => b.value - a.value);
}
