export function normalizePlateForSubmit(raw: string): string {
  const normalized = raw.trim().toUpperCase();
  return normalized.replace(/\s+/g, "");
}

export function normalizeVinForSubmit(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  const normalized = raw.trim().toUpperCase();
  if (!normalized) {
    return null;
  }
  return normalized.replace(/\s+/g, "");
}

