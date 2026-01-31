export const toDateInputValue = (value?: string | null): string => {
  if (!value) return '';

  // Already in YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;

  // ISO string like 2026-01-29T00:00:00Z -> 2026-01-29
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return value.slice(0, 10);

  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';

  return d.toISOString().slice(0, 10);
};
