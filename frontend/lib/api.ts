import { Capacitor, CapacitorHttp } from "@capacitor/core";

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
  _cache_state?: "LIVE" | "CACHED" | "STALE" | "OFFLINE";
  _cached_at?: string;
};

// ========================================================
// API Base URL Detection (Sections 39, 41, 42)
// ========================================================
const PRODUCTION_API_URL = "https://weathergpt-fullstack.onrender.com";

export function isNativeApp(): boolean {
  if (typeof window === "undefined") return false;
  return (
    Capacitor.isNativePlatform() ||
    Boolean((window as any).androidBridge) ||
    Boolean((window as any).Capacitor?.isNativePlatform?.()) ||
    window.location.protocol === "capacitor:" ||
    window.location.protocol === "file:" ||
    (window.location.hostname === "localhost" && window.location.port === "")
  );
}

export function getApiBaseUrl(): string {
  if (typeof window === "undefined") return "";

  // If Capacitor Native Android App or file/capacitor scheme:
  if (isNativeApp()) {
    return (import.meta as any).env?.VITE_API_BASE_URL || PRODUCTION_API_URL;
  }

  // If running in development pointing to local or custom API
  const customBase = (import.meta as any).env?.VITE_API_BASE_URL;
  if (customBase) return customBase;

  // Standard web browser or PWA uses relative paths to same origin
  return "";
}

export function getWsBaseUrl(): string {
  if (typeof window === "undefined") return "";
  const apiBase = getApiBaseUrl();
  if (apiBase) {
    return apiBase.replace(/^http/, "ws");
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

// Native Android HTTP client via CapacitorHttp (Bypasses CORS entirely)
async function nativeRequest<T = any>(
  fullUrl: string,
  options: RequestInit,
  authHeaders: Record<string, string>,
  token: string | null,
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();

  let bodyData: any = undefined;
  if (options.body) {
    if (typeof options.body === "string") {
      try {
        bodyData = JSON.parse(options.body);
      } catch {
        bodyData = options.body;
      }
    } else {
      bodyData = options.body;
    }
  }

  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...(bodyData !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(token ? { "Cookie": `wg_session=${token}` } : {}),
    ...authHeaders,
    ...(options.headers as Record<string, string>),
  };

  let attempts = 0;
  const maxAttempts = 3;

  while (attempts < maxAttempts) {
    attempts++;
    try {
      const response = await CapacitorHttp.request({
        url: fullUrl,
        method,
        headers,
        data: bodyData,
        connectTimeout: 45000,
        readTimeout: 45000,
      });

      let data = response.data;
      if (typeof data === "string") {
        try {
          data = JSON.parse(data);
        } catch {
          // Keep as string
        }
      }

      // Handle Render free tier cold-start (502/503/504)
      if ((response.status === 502 || response.status === 503 || response.status === 504) && attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        continue;
      }

      // Success (2xx)
      if (response.status >= 200 && response.status < 300) {
        // Check for session cookie from Set-Cookie header
        const setCookie = response.headers?.["set-cookie"] || response.headers?.["Set-Cookie"] || "";
        const cookieMatch = typeof setCookie === "string" ? setCookie.match(/wg_session=([^;]+)/) : null;
        const sessionToken = (cookieMatch && cookieMatch[1]) || (data && typeof data === "object" ? data.token : null);
        if (sessionToken) {
          localStorage.setItem("wg.token", sessionToken);
          if (data && typeof data === "object" && !data.token) {
            data.token = sessionToken;
          }
        }
        return data as T;
      }

      // 401 Unauthorized
      if (response.status === 401 && typeof window !== "undefined") {
        localStorage.removeItem("wg.token");
        window.dispatchEvent(new CustomEvent("wg:unauthorized"));
      }

      // Error with message
      const errorMsg =
        typeof data?.detail === "string"
          ? data.detail
          : Array.isArray(data?.detail)
            ? data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ")
            : typeof data?.message === "string"
              ? data.message
              : `Request failed with status ${response.status}`;

      throw new Error(errorMsg);
    } catch (err: any) {
      if (err.message && !err.message.includes("failed") && !err.message.includes("timed out") && !err.message.includes("timeout")) {
        throw err;
      }
      if (attempts < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        continue;
      }
      throw new Error(err.message || "Network request failed. Please check your internet connection.");
    }
  }

  throw new Error("Unable to reach WeatherGPT server. Please check your connection and try again.");
}

// ========================================================
// Universal Authenticated API Client (Sections 40, 42)
// ========================================================
export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const fullUrl = path.startsWith("http://") || path.startsWith("https://") ? path : `${baseUrl}${path}`;

  // Retrieve auth token for Bearer authentication
  const token = typeof window !== "undefined" ? localStorage.getItem("wg.token") : null;
  const authHeaders: Record<string, string> = {};
  if (token) {
    authHeaders["Authorization"] = `Bearer ${token}`;
  }

  // When running in native Android app, use native CapacitorHttp
  if (isNativeApp()) {
    return await nativeRequest<T>(fullUrl, options, authHeaders, token);
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options.headers,
    },
    credentials: "include",
  });

  const data: any = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("wg.token");
      window.dispatchEvent(new CustomEvent("wg:unauthorized"));
    }
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ")
          : "The request could not be completed. Please try again.",
    );
  }
  return data;
}

// ========================================================
// Stale-While-Revalidate Weather Caching (Sections 28, 29, 30)
// ========================================================
function cacheKeyFor(p: Place): string {
  return `wg.cache.weather.${p.latitude.toFixed(2)}_${p.longitude.toFixed(2)}`;
}

export function getCachedWeather(p: Place): Weather | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(cacheKeyFor(p));
    if (!raw) return null;
    const { data, timestamp } = JSON.parse(raw);
    const ageSeconds = (Date.now() - timestamp) / 1000;
    const isStale = ageSeconds > 1800; // > 30 minutes is stale
    return {
      ...data,
      _cache_state: isStale ? "STALE" : "CACHED",
      _cached_at: new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
  } catch {
    return null;
  }
}

export function setCachedWeather(p: Place, weather: Weather) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(
      cacheKeyFor(p),
      JSON.stringify({ data: weather, timestamp: Date.now() }),
    );
  } catch {}
}

// ========================================================
// Network Connectivity Status (Section 31)
// ========================================================
export type ConnectionStatus = "ONLINE" | "SLOW CONNECTION" | "OFFLINE";

export function getConnectionStatus(): ConnectionStatus {
  if (typeof navigator === "undefined") return "ONLINE";
  if (!navigator.onLine) return "OFFLINE";
  const nav = navigator as any;
  const conn = nav.connection || nav.mozConnection || nav.webkitConnection;
  if (conn && (conn.effectiveType === "2g" || conn.effectiveType === "slow-2g" || conn.saveData)) {
    return "SLOW CONNECTION";
  }
  return "ONLINE";
}

// ========================================================
// Low Data Mode (Section 33)
// ========================================================
export function isLowDataMode(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("wg.low_data_mode") === "true";
}

export function setLowDataMode(enabled: boolean) {
  if (typeof window === "undefined") return;
  localStorage.setItem("wg.low_data_mode", enabled ? "true" : "false");
  window.dispatchEvent(new CustomEvent("wg:low_data_mode_changed", { detail: enabled }));
}

// ========================================================
// Utilities
// ========================================================
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
