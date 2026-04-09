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

export const toDateTimeLocalInputValue = (value?: string | null): string => {
  if (!value) return '';

  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';

  // Format to YYYY-MM-DDTHH:mm
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}`;
};
