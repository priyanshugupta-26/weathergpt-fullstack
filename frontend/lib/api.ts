export type Place = {
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  admin1?: string;
};
export type Row = Record<string, any>;
export type Weather = {
  status: string;
  source: string;
  message?: string;
  timestamp?: string;
  fetched_at?: string;
  timezone?: string;
  current: Row;
  hourly: Row[];
  daily: Row[];
  units: Row;
  official_observation?: Row;
  official_forecast?: Row | string;
};
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    credentials: "same-origin",
  });
  const data: any = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string" ? data.detail : "Please check the supplied values.",
    );
  return data;
}
export const locationQuery = (p: Place) =>
  new URLSearchParams({
    latitude: String(p.latitude),
    longitude: String(p.longitude),
    name: p.name,
  }).toString();
export function readLocal<T>(key: string, fallback: T): T {
  try {
    return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
  } catch {
    return fallback;
  }
}
export function writeLocal(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}
export const number = (v: unknown, digits = 0) =>
  typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "—";
export const condition = (code: number) =>
  code === 0
    ? "Clear sky"
    : code < 4
      ? "Partly cloudy"
      : code < 50
        ? "Foggy"
        : code < 70
          ? "Rain"
          : code < 80
            ? "Snow"
            : code < 90
              ? "Rain showers"
              : code >= 95
                ? "Thunderstorms"
                : "Conditions unavailable";
