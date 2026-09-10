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
} from "lucide-react";
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
  locationQuery,
  readLocal,
  writeLocal,
  type Place,
  type Weather,
  type Row,
} from "@/lib/api";
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
const defaultPlace = { name: "Patna", latitude: 25.5941, longitude: 85.1376, country: "India" };
const nav = [
  ["/", "Overview", LayoutDashboard],
  ["/globe", "Live globe", Globe2],
  ["/forecast", "Forecast", CloudSun],
  ["/chat", "WeatherGPT", Sparkles],
  ["/alerts", "Alert center", ShieldAlert],
  ["/climate", "Climate analytics", ChartNoAxesCombined],
  ["/agriculture", "Agriculture", Leaf],
  ["/aviation", "Aviation", Plane],
  ["/marine", "Marine", Waves],
  ["/city-monitor", "Smart city", Building2],
  ["/data-lab", "Data & Learning Lab", Database],
  ["/model-lab", "Model lab", Cpu],
  ["/dashboard", "My dashboard", LayoutDashboard],
] as const;
function Nav({ route, navigate }: { route: string; navigate: (s: string) => void }) {
  const { setOpenMobile } = useSidebar();
  return (
    <>
      <SidebarContent>
        <a
          href="/"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            navigate("/");
          }}
        >
          <span className="brand-mark">
            <CloudSun size={24} />
          </span>
          WeatherGPT<small>BETA</small>
        </a>
        <nav className="nav-group">
          {nav.map(([href, label, Icon], i) => (
            <div key={href}>
              {[0, 5, 12].includes(i) && (
                <span
                  className="eyebrow"
                  style={{ display: "block", padding: "15px 12px 8px", fontSize: 10 }}
                >
                  {i === 0 ? "WORKSPACE" : i === 5 ? "INTELLIGENCE" : "PERSONAL"}
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
                {label}
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
            API setup
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
            Settings
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
            System status
          </a>
        </nav>
        <div className="provider-indicator" style={{ padding: "4px 24px 24px" }}>
          <span className="dot" />
          Weather intelligence, connected
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
    [language, setLanguage] = useState(() => readLocal("wg.language", "en")),
    [theme, setTheme] = useState(() => readLocal("wg.theme", "dark")),
    [notifications, setNotifications] = useState<Record<string, boolean>>(() =>
      readLocal("wg.notifications", {}),
    ),
    [toastText, setToastText] = useState(""),
    [forecastSource, setForecastSourceState] = useState(() => readLocal("wg.forecastSource", "AUTO"));
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
  useEffect(() => {
    if (!toastText) return;
    const t = setTimeout(() => setToastText(""), 4500);
    return () => clearTimeout(t);
  }, [toastText]);
  useEffect(() => {
    writeLocal("wg.language", language);
    document.documentElement.lang = language;
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
    api("/api/profile")
      .then(setUser)
      .catch(() => {});
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
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
        if (w.status !== "live") setError(w.message || "Weather unavailable");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    api(`/api/alerts?${locationQuery(place)}`, { signal: controller.signal })
      .then((d) => setAlerts(d.alerts))
      .catch(() => {});
    return () => controller.abort();
  }, [place, tick, forecastSource]);
  useEffect(() => {
    const timer = setInterval(() => setTick((t) => t + 1), 600000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let socket: WebSocket,
      timer: ReturnType<typeof setTimeout>,
      stopped = false,
      attempt = 0;
    const seen = new Set<string>();
    const connect = () => {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/alerts?${locationQuery(place)}`,
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
  let page: React.ReactNode;
  switch (route) {
    case "/":
      page = <Home />;
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
    case "/dashboard":
      page = <Dashboard />;
      break;
    case "/profile":
    case "/settings":
    case "/login":
      page = <Account />;
      break;
    case "/admin":
      page = <Admin />;
      break;
    default:
      page = (
        <div className="empty-state">
          <h1>Page not found</h1>
          <button className="button" onClick={() => navigate("/")}>
            Back to overview
          </button>
        </div>
      );
  }
  return (
    <Context.Provider value={ctx}>
      <SidebarProvider style={{ "--sidebar-width": "230px" } as React.CSSProperties}>
        <Sidebar>
          <Nav route={route} navigate={navigate} />
        </Sidebar>
        <div className="shell">
          <header className="topbar">
            <SidebarTrigger aria-label="Toggle navigation" />
            <span className="topbar-label">Weather intelligence</span>
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
            <div className="language-select">
              <Choice
                label="Response language"
                value={language}
                onChange={setLanguage}
                items={[
                  { value: "en", label: "EN" },
                  { value: "hi", label: "हिन्दी" },
                ]}
              />
            </div>
            <button
              className="icon-btn"
              aria-label="Open alert center"
              onClick={() => navigate("/alerts")}
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
      {toastText && (
        <div className="toast" role="status">
          {toastText}
        </div>
      )}
    </Context.Provider>
  );
}
