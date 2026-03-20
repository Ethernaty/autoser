import { AsYouType } from "libphonenumber-js";

export function sanitizePhoneInput(raw: string): string {
  const trimmed = raw.trim();
  const digits = trimmed.replace(/\D/g, "");
  if (!digits) {
    return trimmed.startsWith("+") ? "+" : "";
  }
  return `+${digits}`;
}

export function formatPhoneInput(raw: string): string {
  const normalized = sanitizePhoneInput(raw);
  if (!normalized || normalized === "+") {
    return normalized;
  }
  const formatter = new AsYouType();
  return formatter.input(normalized);
}

export function normalizePhoneForSubmit(raw: string): string {
  const formatted = formatPhoneInput(raw);
  if (!formatted || formatted === "+") {
    return "";
  }

  const parser = new AsYouType();
  parser.input(formatted);
  return parser.getNumberValue() ?? formatted;
}

export function formatPhoneForDisplay(value: string): string {
  return formatPhoneInput(value) || value;
}
