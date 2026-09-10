import { lazy, Suspense, useEffect, useState, useCallback, useRef } from "react";
import {
  CloudSun,
  LayoutDashboard,
  Globe2,
  ChartNoAxesCombined,
  Sparkles,
  ShieldAlert,
  Leaf,
  Plane,
  Waves,
  Settings,
  User,
  Activity,
  Bell,
  LocateFixed,
  LogOut,
  Building2,
  Cpu,
  Database,
  Key,
  Globe,
  Layers,
  Radio,
  Mic,
  ShieldCheck,
  MoreHorizontal,
  Wifi,
  WifiOff,
  X,
  Zap,
} from "lucide-react";
import { Capacitor } from "@capacitor/core";
import {
  Sidebar,
  SidebarProvider,
  SidebarContent,
  SidebarFooter,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import Search from "@/components/Search";
import { Choice } from "@/components/WeatherUI";
import { Context } from "@/lib/context";
import {
  api,
  getWsBaseUrl,
  locationQuery,
  readLocal,
  writeLocal,
  type Place,
  type Weather,
  type Row,
  getCachedWeather,
  setCachedWeather,
  getConnectionStatus,
  isLowDataMode,
  setLowDataMode,
  type ConnectionStatus,
} from "@/lib/api";
import { pushManager } from "@/lib/push";
import { LANGUAGES, t, isRTL, getLanguageInfo } from "@/lib/i18n";
const Home = lazy(() => import("./views/Home"));
const Forecast = lazy(() => import("./views/Forecast"));
const GlobePage = lazy(() => import("./views/GlobePage"));
const Chat = lazy(() => import("./views/Chat"));
const Alerts = lazy(() => import("./views/Alerts"));
const Climate = lazy(() => import("./views/Climate"));
const Specialist = lazy(() => import("./views/Specialist"));
const Account = lazy(() => import("./views/Account"));
const Admin = lazy(() => import("./views/Admin"));
const Dashboard = lazy(() => import("./views/Dashboard"));
const CityMonitor = lazy(() => import("./views/CityMonitor"));
const ModelLab = lazy(() => import("./views/ModelLab"));
const DataLab = lazy(() => import("./views/DataLab"));
const Setup = lazy(() => import("./views/Setup"));
const Register = lazy(() => import("./views/Register"));
const Login = lazy(() => import("./views/Login"));
const Onboarding = lazy(() => import("./views/Onboarding"));
const Notifications = lazy(() => import("./views/Notifications"));
const NWP = lazy(() => import("./views/NWP"));
const Dissemination = lazy(() => import("./views/Dissemination"));
const RuralVoice = lazy(() => import("./views/RuralVoice"));
const Sources = lazy(() => import("./views/Sources"));
const SIHReadiness = lazy(() => import("./views/SIHReadiness"));

const defaultPlace = { name: "Patna", latitude: 25.5941, longitude: 85.1376, country: "India" };
const nav = [
  ["/dashboard", "My dashboard", LayoutDashboard, "nav.dashboard"],
  ["/globe", "Live globe", Globe2, "nav.globe"],
  ["/forecast", "Forecast", CloudSun, "nav.forecast"],
  ["/chat", "WeatherGPT", Sparkles, "nav.chat"],
  ["/rural", "Rural & Voice", Mic, "nav.rural"],
  ["/alerts", "Disaster center", ShieldAlert, "nav.alerts"],
  ["/notifications", "Notifications", Bell, "nav.notifications"],
  ["/nwp", "NWP / GFS 0.25°", Layers, "nav.nwp"],
  ["/climate", "Climate analytics", ChartNoAxesCombined, "nav.climate"],
  ["/agriculture", "Agriculture", Leaf, "nav.agriculture"],
  ["/aviation", "Aviation", Plane, "nav.aviation"],
  ["/marine", "Marine", Waves, "nav.marine"],
  ["/city-monitor", "Smart city", Building2, "nav.cityMonitor"],
  ["/dissemination", "Dissemination demo", Radio, "nav.dissemination"],
  ["/data-lab", "Data & Learning Lab", Database, "nav.dataLab"],
  ["/model-lab", "Model lab", Cpu, "nav.modelLab"],
  ["/sources", "Data sources", Database, "nav.sources"],
  ["/sih-readiness", "SIH 26068 Matrix", ShieldCheck, "nav.sihReadiness"],
] as const;

function Nav({ route, navigate, language }: { route: string; navigate: (s: string) => void; language: string }) {
  const { setOpenMobile } = useSidebar();
  return (
    <>
      <SidebarContent>
        <a
          href="/dashboard"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            navigate("/dashboard");
          }}
        >
          <span className="brand-mark">
            <CloudSun size={24} />
          </span>
          WeatherGPT<small>BETA</small>
        </a>
        <nav className="nav-group">
          {nav.map(([href, label, Icon, navKey], i) => (
            <div key={href}>
              {[0, 7, 14].includes(i) && (
                <span
                  className="eyebrow"
                  style={{ display: "block", padding: "15px 12px 8px", fontSize: 10 }}
                >
                  {i === 0 ? "WORKSPACE" : i === 7 ? "METEOROLOGY & SECTORS" : "INTELLIGENCE & AUDIT"}
                </span>
              )}
              <a
                href={href}
                className={`nav-link ${route === href ? "active" : ""}`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(href);
                  setOpenMobile(false);
                }}
              >
                <Icon size={18} />
                {t(navKey, language) || label}
              </a>
            </div>
          ))}
        </nav>
      </SidebarContent>
      <SidebarFooter>
        <nav className="nav-group">
          <a
            href="/setup"
            className={`nav-link ${route === "/setup" ? "active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              navigate("/setup");
              setOpenMobile(false);
            }}
          >
            <Key size={18} />
            {t("nav.apiSetup", language) || "API setup"}
          </a>
          <a
            href="/settings"
            className={`nav-link ${route === "/settings" ? "active" : ""}`}
            onClick={(e) => {
              e.preventDefault();
              navigate("/settings");
              setOpenMobile(false);
            }}
          >
            <Settings size={18} />
            {t("nav.settings", language) || "Settings"}
          </a>
          <a
            href="/admin"
            className="nav-link"
            onClick={(e) => {
              e.preventDefault();
              navigate("/admin");
              setOpenMobile(false);
            }}
          >
            <Activity size={18} />
            {t("nav.systemStatus", language) || "System status"}
          </a>
        </nav>
        <div className="provider-indicator" style={{ padding: "4px 24px 24px" }}>
          <span className="dot" />
          {t("brand.tagline", language) || "Weather intelligence, connected"}
        </div>
      </SidebarFooter>
    </>
  );
}

export default function App() {
  const [route, setRoute] = useState(location.pathname),
    [place, setPlaceState] = useState<Place>(() => readLocal("wg.place", defaultPlace)),
    [weather, setWeather] = useState<Weather | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [tick, setTick] = useState(0),
    [alerts, setAlerts] = useState<Row[]>([]),
    [user, setUser] = useState<Row | null>(null),
    [authChecked, setAuthChecked] = useState(false),
    [language, setLanguage] = useState(() => readLocal("wg.language", "en")),
    [theme, setTheme] = useState(() => readLocal("wg.theme", "dark")),
    [notifications, setNotifications] = useState<Record<string, boolean>>(() =>
      readLocal("wg.notifications", {}),
    ),
    [toastText, setToastText] = useState(""),
    [forecastSource, setForecastSourceState] = useState(() => readLocal("wg.forecastSource", "AUTO")),
    [showMoreSheet, setShowMoreSheet] = useState(false),
    [connStatus, setConnStatus] = useState<ConnectionStatus>(() => getConnectionStatus()),
    [lowData, setLowDataState] = useState(() => isLowDataMode());

  const toggleLowDataMode = useCallback(() => {
    setLowDataState((prev) => {
      const next = !prev;
      setLowDataMode(next);
      return next;
    });
  }, []);

  const setForecastSource = useCallback((s: string) => {
    setForecastSourceState(s);
    writeLocal("wg.forecastSource", s);
    setWeather(null);
  }, []);
  const notifyPrefs = useRef(notifications);
  notifyPrefs.current = notifications;
  const loadedProfile = useRef<number | null>(null);
  useEffect(() => {
    if (!user || loadedProfile.current === user.id) return;
    loadedProfile.current = user.id;
    const p = user.preferences || {};
    if (p.language) setLanguage(p.language);
    if (p.theme) setTheme(p.theme);
    if (p.notifications) setNotifications(p.notifications);
    if (p.default_location) setPlaceState(p.default_location);
  }, [user]);
  const navigate = useCallback((path: string) => {
    history.pushState({}, "", path);
    setRoute(path.split("?")[0]);
    window.scrollTo(0, 0);
  }, []);
  const toast = useCallback((s: string) => setToastText(s), []);
  const setPlace = useCallback((p: Place) => {
    setPlaceState(p);
    writeLocal("wg.place", p);
    setWeather(null);
    setAlerts([]);
  }, []);
  useEffect(() => {
    const pop = () => setRoute(location.pathname);
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);

  // Network connection status listeners (Section 31)
  useEffect(() => {
    const onOnline = () => {
      setConnStatus("ONLINE");
      setTick((t) => t + 1);
    };
    const onOffline = () => setConnStatus("OFFLINE");
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  // Android hardware back button handling (Section 34)
  useEffect(() => {
    let sub: any;
    if (Capacitor.isNativePlatform()) {
      import("@capacitor/app").then(({ App }) => {
        sub = App.addListener("backButton", () => {
          if (showMoreSheet) {
            setShowMoreSheet(false);
          } else if (route !== "/dashboard" && route !== "/") {
            navigate("/dashboard");
          } else {
            App.exitApp();
          }
        });
      });
    }
    return () => {
      if (sub?.remove) sub.remove();
    };
  }, [showMoreSheet, route, navigate]);

  // Push Notifications & Deep Link Listener (Sections 10, 17, 18)
  useEffect(() => {
    if (user) {
      pushManager.initPush((notification) => {
        setToastText(`🚨 ${notification.title || "Alert"}: ${notification.body || ""}`);
        setTick((t) => t + 1);
      });
    }
    const onNav = (e: any) => {
      if (e.detail?.url) {
        navigate(e.detail.url);
      }
    };
    window.addEventListener("wg:navigate", onNav);
    return () => window.removeEventListener("wg:navigate", onNav);
  }, [user, navigate]);

  useEffect(() => {
    if (!toastText) return;
    const t = setTimeout(() => setToastText(""), 4500);
    return () => clearTimeout(t);
  }, [toastText]);
  useEffect(() => {
    writeLocal("wg.language", language);
    document.documentElement.lang = language;
    document.documentElement.dir = isRTL(language) ? "rtl" : "ltr";
  }, [language]);
  useEffect(() => {
    writeLocal("wg.theme", theme);
    const media = matchMedia("(prefers-color-scheme:light)");
    const apply = () => {
      const light = theme === "light" || (theme === "system" && media.matches);
      document.documentElement.classList.toggle("light", light);
      document.documentElement.classList.toggle("dark", !light);
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  useEffect(() => {
    writeLocal("wg.notifications", notifications);
  }, [notifications]);
  useEffect(() => {
    api<Row>("/api/profile")
      .then((u) => {
        setUser(u);
        setAuthChecked(true);
      })
      .catch(() => {
        setUser(null);
        setAuthChecked(true);
      });
  }, []);
  useEffect(() => {
    if (!authChecked) return;
    const isAuthRoute = route === "/register" || route === "/login" || route === "/onboarding";
    if (!user && !isAuthRoute) {
      navigate("/login");
    } else if (user && (route === "/register" || route === "/login" || route === "/")) {
      navigate("/dashboard");
    }
  }, [authChecked, user, route, navigate]);
  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");

    // Stale-While-Revalidate: Instant cached weather display (Sections 28, 29)
    const cached = getCachedWeather(place);
    if (cached && !weather) {
      setWeather(cached);
    }

    const srcParam =
      forecastSource === "WEATHERGPT ML"
        ? "&source=weathergpt_ml"
        : forecastSource === "OPEN-METEO"
          ? "&source=open-meteo"
          : forecastSource === "IMD"
            ? "&source=imd"
            : "";
    api<Weather>(`/api/weather/forecast?${locationQuery(place)}${srcParam}`, { signal: controller.signal })
      .then((w) => {
        setWeather(w);
        setCachedWeather(place, w);
        if (w.status !== "live") setError(w.message || "Weather unavailable");
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          if (cached) {
            setError(`Offline/Low Connectivity — Showing cached weather from ${cached._cached_at || "earlier"}`);
          } else {
            setError(e.message);
          }
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    api(`/api/alerts?${locationQuery(place)}`, { signal: controller.signal })
      .then((d) => setAlerts(d.alerts))
      .catch(() => {});
    return () => controller.abort();
  }, [user, place, tick, forecastSource]);
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 600000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!user) return;
    let socket: WebSocket,
      timer: ReturnType<typeof setTimeout>,
      stopped = false,
      attempt = 0;
    const seen = new Set<string>();
    const connect = () => {
      socket = new WebSocket(
        `${getWsBaseUrl()}/ws/alerts?${locationQuery(place)}`,
      );
      socket.onopen = () => {
        attempt = 0;
      };
      socket.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.type !== "alerts") return;
          setAlerts(d.alerts);
          for (const a of d.alerts) {
            if (
              !seen.has(a.id) &&
              notifyPrefs.current[a.alert_type] &&
              "Notification" in window &&
              Notification.permission === "granted"
            )
              new Notification(`${a.severity}: ${a.description}`, {
                body: a.recommendation,
                tag: a.id,
              });
            seen.add(a.id);
          }
        } catch {}
      };
      socket.onclose = () => {
        if (!stopped) timer = setTimeout(connect, Math.min(30000, 1000 * 2 ** attempt++));
      };
      socket.onerror = () => socket.close();
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [place]);
  useEffect(() => {
    const ctx = (document as any).modelContext;
    if (!ctx?.registerTool) return;
    const ctrl = new AbortController();
    Promise.resolve(
      ctx.registerTool(
        {
          name: "select_weather_location",
          description: "Select coordinates and update the visible weather context.",
          inputSchema: {
            type: "object",
            properties: {
              latitude: { type: "number", minimum: -90, maximum: 90 },
              longitude: { type: "number", minimum: -180, maximum: 180 },
              name: { type: "string" },
            },
            required: ["latitude", "longitude", "name"],
            additionalProperties: false,
          },
          annotations: { readOnlyHint: false, untrustedContentHint: false },
          execute: async (p: Place) => {
            if (
              !Number.isFinite(p.latitude) ||
              Math.abs(p.latitude) > 90 ||
              !Number.isFinite(p.longitude) ||
              Math.abs(p.longitude) > 180 ||
              typeof p.name !== "string" ||
              p.name.length > 160
            )
              throw Error("Invalid location");
            setPlace(p);
            return { selected: p };
          },
        },
        { signal: ctrl.signal },
      ),
    ).catch(() => {});
    return () => ctrl.abort();
  }, [setPlace]);
  const geo = () => {
    if (!navigator.geolocation) {
      toast("Geolocation is not available. Use location search.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) =>
        setPlace({
          name: "Current location",
          latitude: p.coords.latitude,
          longitude: p.coords.longitude,
        }),
      (e) =>
        toast(
          e.code === 1
            ? "Location permission denied. Search for a city instead."
            : "Could not locate this device. Try city search.",
        ),
      { timeout: 12000 },
    );
  };
  const ctx = {
    place,
    setPlace,
    weather,
    forecastSource,
    setForecastSource,
    loading,
    reload: () => setTick((t) => t + 1),
    error,
    alerts,
    user,
    setUser,
    language,
    setLanguage,
    theme,
    setTheme,
    toast,
    navigate,
    route,
    geo,
    notifications,
    setNotifications,
  };
  if (!authChecked) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#080c14",
          color: "#f8fafc",
          fontFamily: "Inter, sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <CloudSun size={38} style={{ color: "#38bdf8" }} />
          <span style={{ fontSize: 13, letterSpacing: "0.08em", textTransform: "uppercase", color: "#94a3b8" }}>
            WeatherGPT
          </span>
        </div>
      </div>
    );
  }

  if (route === "/register") {
    return (
      <Context.Provider value={ctx}>
        <Suspense fallback={<div className="loading" aria-label="Loading..." />}>
          <Register />
        </Suspense>
        {toastText && <div className="toast" role="status">{toastText}</div>}
      </Context.Provider>
    );
  }
  if (route === "/login") {
    return (
      <Context.Provider value={ctx}>
        <Suspense fallback={<div className="loading" aria-label="Loading..." />}>
          <Login />
        </Suspense>
        {toastText && <div className="toast" role="status">{toastText}</div>}
      </Context.Provider>
    );
  }
  if (route === "/onboarding") {
    return (
      <Context.Provider value={ctx}>
        <Suspense fallback={<div className="loading" aria-label="Loading..." />}>
          <Onboarding />
        </Suspense>
        {toastText && <div className="toast" role="status">{toastText}</div>}
      </Context.Provider>
    );
  }
  if (!user) {
    if (route === "/register") {
      return (
        <Context.Provider value={ctx}>
          <Suspense fallback={<div className="loading" aria-label="Loading..." />}>
            <Register />
          </Suspense>
          {toastText && <div className="toast" role="status">{toastText}</div>}
        </Context.Provider>
      );
    }
    return (
      <Context.Provider value={ctx}>
        <Suspense fallback={<div className="loading" aria-label="Loading..." />}>
          <Login />
        </Suspense>
        {toastText && <div className="toast" role="status">{toastText}</div>}
      </Context.Provider>
    );
  }

  let page: React.ReactNode;
  switch (route) {
    case "/":
    case "/dashboard":
      page = <Dashboard />;
      break;
    case "/forecast":
      page = <Forecast />;
      break;
    case "/globe":
      page = <GlobePage />;
      break;
    case "/chat":
      page = <Chat />;
      break;
    case "/alerts":
      page = <Alerts />;
      break;
    case "/climate":
      page = <Climate />;
      break;
    case "/agriculture":
    case "/aviation":
    case "/marine":
      page = <Specialist key={route} />;
      break;
    case "/city-monitor":
      page = <CityMonitor />;
      break;
    case "/data-lab":
      page = <DataLab />;
      break;
    case "/model-lab":
      page = <ModelLab />;
      break;
    case "/setup":
      page = <Setup />;
      break;
    case "/notifications":
      page = <Notifications />;
      break;
    case "/nwp":
      page = <NWP />;
      break;
    case "/dissemination":
      page = <Dissemination />;
      break;
    case "/rural":
    case "/voice":
      page = <RuralVoice />;
      break;
    case "/sources":
      page = <Sources />;
      break;
    case "/sih-readiness":
      page = <SIHReadiness />;
      break;
    case "/profile":
    case "/settings":
      page = <Account />;
      break;
    case "/admin":
      page = <Admin />;
      break;
    default:
      page = (
        <div className="empty-state">
          <h1>Page not found</h1>
          <button className="button" onClick={() => navigate("/dashboard")}>
            Back to dashboard
          </button>
        </div>
      );
  }
  return (
    <Context.Provider value={ctx}>
      <SidebarProvider style={{ "--sidebar-width": "230px" } as React.CSSProperties}>
        <Sidebar>
          <Nav route={route} navigate={navigate} language={language} />
        </Sidebar>
        <div className="shell">
          {alerts.some((a) =>
            ["SEVERE", "WARNING", "EXTREME", "RED", "EMERGENCY"].includes(a.severity?.toUpperCase()),
          ) && (
            <div className="top-warning-banner" role="alert">
              <div className="banner-left">
                <span className="banner-pulse" />
                <span style={{ fontWeight: 800, color: "#fca5a5", letterSpacing: "0.05em" }}>
                  🔴 SEVERE WEATHER WARNING:
                </span>
                <span>
                  {(() => {
                    const w = alerts.find((a) =>
                      ["SEVERE", "WARNING", "EXTREME", "RED", "EMERGENCY"].includes(
                        a.severity?.toUpperCase(),
                      ),
                    );
                    return `${w?.description || w?.event || "Critical Alert"} for ${w?.location || place.name}. ${
                      w?.expires ? `Valid until ${new Date(w.expires).toLocaleTimeString()}` : ""
                    }`;
                  })()}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <button
                  className="button"
                  style={{
                    background: "#fff",
                    color: "#991b1b",
                    fontWeight: 700,
                    padding: "3px 10px",
                    fontSize: 11,
                  }}
                  onClick={() => navigate("/alerts")}
                >
                  View Details
                </button>
              </div>
            </div>
          )}

          <header className="topbar">
            <SidebarTrigger aria-label="Toggle navigation" />
            <span className="topbar-label">Weather intelligence</span>
            <span
              className={`network-badge ${connStatus === "ONLINE" ? "online" : connStatus === "SLOW CONNECTION" ? "slow" : "offline"}`}
              title={`Network Connectivity: ${connStatus}`}
              style={{ cursor: "default", marginRight: 4 }}
            >
              {connStatus === "ONLINE" ? <Wifi size={11} /> : <WifiOff size={11} />}
              <span style={{ fontSize: 9 }}>{connStatus}</span>
            </span>
            <Search />
            <div
              className="forecast-source-pills"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                background: "rgba(255,255,255,0.06)",
                padding: "3px 6px",
                borderRadius: 8,
                border: "1px solid var(--line)",
              }}
            >
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  padding: "0 4px",
                }}
              >
                Engine:
              </span>
              {[
                { id: "AUTO", label: "✨ Auto" },
                { id: "WEATHERGPT ML", label: "⚡ ML Model" },
                { id: "OPEN-METEO", label: "🌐 Open-Meteo" },
              ].map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setForecastSource(s.id)}
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "3px 8px",
                    borderRadius: 6,
                    cursor: "pointer",
                    border: "none",
                    background:
                      forecastSource === s.id
                        ? s.id === "WEATHERGPT ML"
                          ? "#10b981"
                          : "var(--accent)"
                        : "transparent",
                    color: forecastSource === s.id ? "#fff" : "var(--muted)",
                    transition: "all 0.15s ease",
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <button className="icon-btn" aria-label="Use current location" onClick={geo}>
              <LocateFixed size={17} />
            </button>
            <div className="language-select" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Globe size={15} style={{ color: "var(--muted)" }} />
              <select
                aria-label="Application language"
                value={language}
                onChange={(e) => {
                  const newLang = e.target.value;
                  setLanguage(newLang);
                  if (user) {
                    const prefs = { ...(user.preferences || {}), language: newLang };
                    api("/api/profile", {
                      method: "PATCH",
                      body: JSON.stringify({ preferences: prefs }),
                    }).then((u) => setUser(u as Row)).catch(() => {});
                  }
                }}
                style={{
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  padding: "4px 8px",
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  outline: "none",
                }}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code} style={{ background: "#111827", color: "#f8fafc" }}>
                    {l.nativeName} ({l.code.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>
            <button
              className="icon-btn"
              aria-label="Open notifications"
              onClick={() => navigate("/notifications")}
              title="Notification Center"
            >
              <Bell size={17} />
              {alerts.length > 0 && <span className="dot" />}
            </button>
            <button
              className="icon-btn avatar"
              aria-label="Open profile"
              onClick={() => navigate("/profile")}
            >
              {user ? user.name.slice(0, 2).toUpperCase() : <User size={17} />}
            </button>
          </header>
          <main className="content">
            {error && (
              <div className="error-note" role="status">
                {error}{" "}
                <button
                  onClick={() => setTick((t) => t + 1)}
                  style={{ textDecoration: "underline" }}
                >
                  Retry weather
                </button>
              </div>
            )}
            <Suspense fallback={<div className="loading" aria-label="Loading page" />}>
              {page}
            </Suspense>
            <footer>
              <span>© {new Date().getFullYear()} WeatherGPT · A clearer view of your world.</span>
              <span>Weather: Open-Meteo · Earthquakes: USGS · Boundaries: Natural Earth</span>
            </footer>
          </main>
        </div>
      </SidebarProvider>

      {/* Mobile Bottom Navigation Bar (Section 4) */}
      <nav className="mobile-bottom-nav" aria-label="Mobile Bottom Navigation">
        <button
          className={`mobile-nav-item ${route === "/dashboard" || route === "/" ? "active" : ""}`}
          onClick={() => { setShowMoreSheet(false); navigate("/dashboard"); }}
        >
          <LayoutDashboard size={18} />
          <span>Home</span>
        </button>
        <button
          className={`mobile-nav-item ${route === "/forecast" ? "active" : ""}`}
          onClick={() => { setShowMoreSheet(false); navigate("/forecast"); }}
        >
          <CloudSun size={18} />
          <span>Forecast</span>
        </button>
        <button
          className={`mobile-nav-item ${route === "/chat" ? "active" : ""}`}
          onClick={() => { setShowMoreSheet(false); navigate("/chat"); }}
        >
          <Sparkles size={18} />
          <span>WeatherGPT</span>
        </button>
        <button
          className={`mobile-nav-item ${route === "/alerts" ? "active" : ""}`}
          onClick={() => { setShowMoreSheet(false); navigate("/alerts"); }}
        >
          <ShieldAlert size={18} />
          <span>Alerts</span>
        </button>
        <button
          className={`mobile-nav-item ${showMoreSheet ? "active" : ""}`}
          onClick={() => setShowMoreSheet((s) => !s)}
        >
          <MoreHorizontal size={18} />
          <span>More</span>
        </button>
      </nav>

      {/* Mobile More Sheet / Drawer (Section 4, 33) */}
      {showMoreSheet && (
        <>
          <div className="mobile-more-backdrop" onClick={() => setShowMoreSheet(false)} />
          <div className="mobile-more-sheet" role="dialog" aria-modal="true" aria-label="More Features">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--line)", paddingBottom: 10 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <CloudSun size={20} style={{ color: "var(--cyan)" }} />
                <span style={{ fontWeight: 800, fontSize: 16 }}>More WeatherGPT Services</span>
              </div>
              <button className="icon-btn" onClick={() => setShowMoreSheet(false)} aria-label="Close menu">
                <X size={18} />
              </button>
            </div>

            {/* Quick Status & Low Data Toggle */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "12px 0 6px", padding: "8px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 10, border: "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className={`network-badge ${connStatus === "ONLINE" ? "online" : connStatus === "SLOW CONNECTION" ? "slow" : "offline"}`}>
                  {connStatus === "ONLINE" ? <Wifi size={11} /> : <WifiOff size={11} />}
                  <span>{connStatus}</span>
                </span>
              </div>
              <button
                type="button"
                onClick={toggleLowDataMode}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  background: lowData ? "rgba(16,185,129,0.2)" : "rgba(255,255,255,0.06)",
                  border: `1px solid ${lowData ? "#10b981" : "var(--line)"}`,
                  color: lowData ? "#10b981" : "var(--muted)",
                  borderRadius: 8,
                  padding: "4px 10px",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                <Zap size={13} />
                <span>Low Data: {lowData ? "ON" : "OFF"}</span>
              </button>
            </div>

            <div className="mobile-more-grid">
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/globe"); }}>
                <Globe2 size={22} style={{ color: "#38bdf8" }} />
                <span>Live Globe</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/climate"); }}>
                <ChartNoAxesCombined size={22} style={{ color: "#f59e0b" }} />
                <span>Climate</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/agriculture"); }}>
                <Leaf size={22} style={{ color: "#10b981" }} />
                <span>Agriculture</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/aviation"); }}>
                <Plane size={22} style={{ color: "#a855f7" }} />
                <span>Aviation</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/marine"); }}>
                <Waves size={22} style={{ color: "#06b6d4" }} />
                <span>Marine</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/city-monitor"); }}>
                <Building2 size={22} style={{ color: "#ec4899" }} />
                <span>Smart City</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/nwp"); }}>
                <Layers size={22} style={{ color: "#6366f1" }} />
                <span>NWP / GFS</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/rural"); }}>
                <Mic size={22} style={{ color: "#ef4444" }} />
                <span>Rural Voice</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/data-lab"); }}>
                <Database size={22} style={{ color: "#14b8a6" }} />
                <span>Data Lab</span>
              </div>
              {(user?.role === "admin" || true) && (
                <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/model-lab"); }}>
                  <Cpu size={22} style={{ color: "#8b5cf6" }} />
                  <span>Model Lab</span>
                </div>
              )}
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/notifications"); }}>
                <Bell size={22} style={{ color: "#eab308" }} />
                <span>Notifications</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/profile"); }}>
                <User size={22} style={{ color: "#94a3b8" }} />
                <span>Profile</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/sources"); }}>
                <Database size={22} style={{ color: "#64748b" }} />
                <span>Data Sources</span>
              </div>
              <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/sih-readiness"); }}>
                <ShieldCheck size={22} style={{ color: "#22c55e" }} />
                <span>SIH Matrix</span>
              </div>
              {user?.role === "admin" && (
                <div className="mobile-more-card" onClick={() => { setShowMoreSheet(false); navigate("/admin"); }}>
                  <Key size={22} style={{ color: "#f97316" }} />
                  <span>Admin</span>
                </div>
              )}
            </div>

            <div style={{ marginTop: 16, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
              <button
                className="button secondary"
                style={{ width: "100%", justifyContent: "center", color: "#f87171", borderColor: "rgba(239, 68, 68, 0.3)" }}
                onClick={async () => {
                  try {
                    await api("/api/auth/logout", { method: "POST" });
                  } catch {}
                  localStorage.removeItem("wg.token");
                  setUser(null);
                  setShowMoreSheet(false);
                  navigate("/login");
                }}
              >
                <LogOut size={16} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </>
      )}

      {toastText && (
        <div className="toast" role="status">
          {toastText}
        </div>
      )}
    </Context.Provider>
  );
}
