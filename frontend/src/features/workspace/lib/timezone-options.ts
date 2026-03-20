import type { ComboboxOption } from "@/design-system/primitives/combobox";

const POPULAR_TIMEZONES = [
  "UTC",
  "America/Los_Angeles",
  "America/Denver",
  "America/Chicago",
  "America/New_York",
  "America/Mexico_City",
  "America/Sao_Paulo",
  "America/Santiago",
  "America/Bogota",
  "Europe/Moscow",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Paris",
  "Europe/Warsaw",
  "Europe/Istanbul",
  "Africa/Cairo",
  "Africa/Johannesburg",
  "Africa/Nairobi",
  "Asia/Dubai",
  "Asia/Karachi",
  "Asia/Kolkata",
  "Asia/Dhaka",
  "Asia/Bangkok",
  "Asia/Singapore",
  "Asia/Shanghai",
  "Asia/Hong_Kong",
  "Asia/Tokyo",
  "Asia/Seoul",
  "Australia/Perth",
  "Australia/Brisbane",
  "Australia/Sydney",
  "Pacific/Auckland"
];

let cachedOptions: ComboboxOption[] | null = null;

function parseGmtOffsetToMinutes(zoneName: string): number {
  if (zoneName === "GMT" || zoneName === "UTC") {
    return 0;
  }

  const match = zoneName.match(/^GMT([+-]\d{1,2})(?::?(\d{2}))?$/i);
  if (!match) {
    return 0;
  }

  const hours = Number(match[1]);
  const minutes = Number(match[2] ?? "0");
  const absoluteMinutes = Math.abs(hours) * 60 + minutes;
  return hours < 0 ? -absoluteMinutes : absoluteMinutes;
}

function formatUtcOffset(minutes: number): string {
  const sign = minutes >= 0 ? "+" : "-";
  const absolute = Math.abs(minutes);
  const hours = Math.floor(absolute / 60)
    .toString()
    .padStart(2, "0");
  const mins = (absolute % 60).toString().padStart(2, "0");
  return `UTC${sign}${hours}:${mins}`;
}

function getTimezoneOffsetMeta(timezone: string): { offsetMinutes: number; offsetLabel: string } {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      timeZoneName: "shortOffset",
      hour: "2-digit"
    }).formatToParts(new Date());

    const zoneName = parts.find((part) => part.type === "timeZoneName")?.value;
    const offsetMinutes = parseGmtOffsetToMinutes(zoneName ?? "GMT");
    return {
      offsetMinutes,
      offsetLabel: formatUtcOffset(offsetMinutes)
    };
  } catch {
    return { offsetMinutes: 0, offsetLabel: "UTC+00:00" };
  }
}

function resolveTimezoneValues(): string[] {
  const supported = POPULAR_TIMEZONES.filter((timezone) => {
    try {
      new Intl.DateTimeFormat("en-US", { timeZone: timezone }).format(new Date());
      return true;
    } catch {
      return false;
    }
  });

  return supported.length > 0 ? supported : ["UTC"];
}

export function getTimezoneOptions(): ComboboxOption[] {
  if (cachedOptions) {
    return cachedOptions;
  }

  const uniqueValues = Array.from(new Set(resolveTimezoneValues()));
  if (!uniqueValues.includes("UTC")) {
    uniqueValues.unshift("UTC");
  }

  const zones = uniqueValues.map((timezone) => {
    const meta = getTimezoneOffsetMeta(timezone);
    return {
      timezone,
      ...meta
    };
  });

  zones.sort((a, b) => {
    if (a.timezone === "UTC") {
      return -1;
    }
    if (b.timezone === "UTC") {
      return 1;
    }
    if (a.offsetMinutes !== b.offsetMinutes) {
      return a.offsetMinutes - b.offsetMinutes;
    }
    return a.timezone.localeCompare(b.timezone);
  });

  cachedOptions = zones.map((zone) => {
    const compactOffset = zone.offsetLabel.replace(":", "");
    const label = zone.timezone === "UTC" ? "UTC+00:00 - UTC" : `${zone.offsetLabel} - ${zone.timezone}`;
    const keywords = [
      zone.timezone.replaceAll("_", " "),
      zone.offsetLabel,
      compactOffset,
      compactOffset.toLowerCase(),
      zone.timezone === "UTC" ? "coordinated universal time" : null
    ].filter(Boolean) as string[];
    return {
      value: zone.timezone,
      label,
      keywords
    };
  });

  return cachedOptions;
}
