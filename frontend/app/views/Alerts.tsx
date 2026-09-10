import { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Bell,
  ArrowUpRight,
  AlertTriangle,
  Flame,
  CloudRain,
  Zap,
  Waves,
  Wind,
  Activity,
  Globe,
  MapPin,
  RefreshCw,
  FileCode,
  Radio,
  ExternalLink,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { Heading, Empty } from "@/components/WeatherUI";
import { api, type Row } from "@/lib/api";
import { t, getLanguageInfo } from "@/lib/i18n";

export interface DisasterAlert {
  id: string;
  identifier?: string;
  hazard_type?: string;
  event: string;
  headline?: string;
  description: string;
  instruction?: string;
  severity: string;
  urgency?: string;
  certainty?: string;
  location?: string;
  district?: string;
  state?: string;
  latitude?: number;
  longitude?: number;
  source: string;
  is_official?: boolean;
  effective?: string;
  expires?: string;
  timestamp?: string;
}

export default function Alerts() {
  const { alerts: localScreening, place, weather, navigate, setPlace, language, toast, user } = useApp();

  const [activeTab, setActiveTab] = useState("Overview");
  const [scope, setScope] = useState<"india" | "state" | "local" | "global">("india");
  const [aggregatedAlerts, setAggregatedAlerts] = useState<DisasterAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [includeGlobalQuakes, setIncludeGlobalQuakes] = useState(false);
  const [quakes, setQuakes] = useState<Row[]>([]);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const stateParam = scope === "state" && user?.state ? `&state=${encodeURIComponent(user.state)}` : "";
      const locParam = `latitude=${place.latitude}&longitude=${place.longitude}`;
      const globalParam = scope === "global" || includeGlobalQuakes ? "&include_global=true" : "&include_global=false";

      const [alertsRes, quakesRes] = await Promise.all([
        api(`/api/alerts/aggregated?${locParam}${stateParam}${globalParam}`),
        api(`/api/earthquakes?${includeGlobalQuakes || scope === "global" ? "include_global=true" : "include_global=false"}`),
      ]);

      setAggregatedAlerts(alertsRes.alerts || []);
      setQuakes(quakesRes.events || []);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (e) {
      toast(`Alert feed update: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
    const interval = setInterval(loadAlerts, 60000);
    return () => clearInterval(interval);
  }, [place, scope, includeGlobalQuakes]);

  // Filtering alerts by active tab
  const getFilteredAlerts = () => {
    if (activeTab === "Overview") return aggregatedAlerts;
    if (activeTab === "Warnings") return aggregatedAlerts.filter((a) => a.is_official || a.source.includes("CAP") || a.source.includes("IMD"));
    if (activeTab === "Cyclone") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("cyclone") || a.event.toLowerCase().includes("cyclone"));
    if (activeTab === "Flood") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("flood") || a.event.toLowerCase().includes("flood"));
    if (activeTab === "Lightning") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("thunder") || a.hazard_type?.toLowerCase().includes("lightning") || a.event.toLowerCase().includes("lightning"));
    if (activeTab === "Earthquake") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("earthquake") || a.event.toLowerCase().includes("earthquake"));
    if (activeTab === "Heat / Cold") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("heat") || a.hazard_type?.toLowerCase().includes("cold") || a.event.toLowerCase().includes("heat"));
    if (activeTab === "Marine") return aggregatedAlerts.filter((a) => a.hazard_type?.toLowerCase().includes("marine") || a.hazard_type?.toLowerCase().includes("wave") || a.source.includes("INCOIS"));
    if (activeTab === "CAP Feed") return aggregatedAlerts.filter((a) => a.source.toLowerCase().includes("cap") || a.source.toLowerCase().includes("sachet"));
    return aggregatedAlerts;
  };

  const displayedAlerts = getFilteredAlerts();
  const officialCount = aggregatedAlerts.filter((a) => a.is_official).length;
  const severeCount = aggregatedAlerts.filter((a) => ["EXTREME", "SEVERE", "RED", "WARNING"].includes(a.severity.toUpperCase())).length;

  const getSeverityBadgeClass = (sev = "NORMAL") => {
    const s = sev.toUpperCase();
    if (s === "EXTREME" || s === "SEVERE" || s === "RED") return "danger";
    if (s === "WARNING" || s === "ORANGE") return "warn";
    if (s === "ADVISORY" || s === "WATCH" || s === "YELLOW") return "accent";
    return "neutral";
  };

  return (
    <>
      <Heading
        title="Disaster Intelligence & Early Warning"
        subtitle={`Multi-hazard disaster aggregator for India. NDMA Sachet CAP · IMD Warnings · CWC Flood · INCOIS Marine · WeatherGPT ML.`}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button className="button" onClick={loadAlerts} disabled={loading}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            Refresh
          </button>
          <button className="button primary" onClick={() => navigate("/notifications")}>
            <Bell size={14} />
            Notifications Center
          </button>
        </div>
      </Heading>

      {/* Top Intelligence Metrics */}
      <div className="metric-strip" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <section className="card" style={{ borderLeft: "4px solid #ef4444" }}>
          <div className="eyebrow" style={{ color: "#ef4444" }}>HIGH PRIORITY ALERTS</div>
          <h1 style={{ marginTop: 8, fontSize: 32 }}>{severeCount}</h1>
          <small>Severe / Warning level events</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid #10b981" }}>
          <div className="eyebrow" style={{ color: "#10b981" }}>OFFICIAL INDIAN FEEDS</div>
          <h1 style={{ marginTop: 8, fontSize: 32 }}>{officialCount}</h1>
          <small>NDMA Sachet CAP & IMD Official</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid var(--cyan)" }}>
          <div className="eyebrow" style={{ color: "var(--cyan)" }}>ACTIVE LOCATION STATUS</div>
          <h2 style={{ marginTop: 12, fontSize: 18 }}>{place.name}</h2>
          <small>{localScreening.length} local threshold triggers</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid #f59e0b" }}>
          <div className="eyebrow" style={{ color: "#f59e0b" }}>LIVE SENSORS & BUS</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12 }}>
            <Radio size={16} className="blink" style={{ color: "#10b981" }} />
            <span style={{ fontSize: 13, fontWeight: 700 }}>WIS2 / CAP / USGS</span>
          </div>
          <small>Refreshed: {lastRefreshed || "Just now"}</small>
        </section>
      </div>

      {/* Scope Controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, margin: "16px 0" }}>
        <div className="button-row">
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
            Geographic Scope:
          </span>
          {[
            { id: "india", label: "🇮🇳 All India (Default)" },
            { id: "state", label: `📍 My State (${user?.state || "State"})` },
            { id: "local", label: `🎯 My Location (${place.name})` },
            { id: "global", label: "🌐 Global Explorer" },
          ].map((s) => (
            <button
              key={s.id}
              className={`button ${scope === s.id ? "primary" : "secondary"}`}
              style={{ fontSize: 12, padding: "4px 10px" }}
              onClick={() => setScope(s.id as any)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {activeTab === "Earthquake" && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, cursor: "pointer", color: "var(--text)" }}>
            <input
              type="checkbox"
              checked={includeGlobalQuakes}
              onChange={(e) => setIncludeGlobalQuakes(e.target.checked)}
            />
            Show Global Earthquakes (Default: India & Neighborhood only)
          </label>
        )}
      </div>

      {/* Tabs */}
      <div className="alert-filters" style={{ overflowX: "auto", paddingBottom: 6 }}>
        {[
          "Overview",
          "Warnings",
          "Cyclone",
          "Flood",
          "Lightning",
          "Earthquake",
          "Heat / Cold",
          "Marine",
          "CAP Feed",
        ].map((tab) => (
          <button
            key={tab}
            className={activeTab === tab ? "active" : ""}
            onClick={() => setActiveTab(tab)}
            style={{ whiteSpace: "nowrap" }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Disaster List Content */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 16 }}>
        {loading ? (
          <div className="loading" aria-label="Loading disaster intelligence…" />
        ) : displayedAlerts.length > 0 ? (
          displayedAlerts.map((a) => {
            const isSevere = ["EXTREME", "SEVERE", "RED", "WARNING"].includes(a.severity.toUpperCase());
            return (
              <section
                key={a.id}
                className="card alert-item"
                style={{
                  borderLeft: `5px solid ${
                    isSevere ? "#ef4444" : a.severity === "ADVISORY" ? "#f59e0b" : "var(--cyan)"
                  }`,
                  position: "relative",
                  background: isSevere ? "rgba(45, 15, 15, 0.45)" : undefined,
                }}
              >
                <div className="card-head">
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    {a.hazard_type?.toLowerCase().includes("cyclone") ? (
                      <Wind size={20} style={{ color: "#f97316" }} />
                    ) : a.hazard_type?.toLowerCase().includes("flood") ? (
                      <Waves size={20} style={{ color: "#38bdf8" }} />
                    ) : a.hazard_type?.toLowerCase().includes("lightning") || a.hazard_type?.toLowerCase().includes("thunder") ? (
                      <Zap size={20} style={{ color: "#eab308" }} />
                    ) : a.hazard_type?.toLowerCase().includes("heat") ? (
                      <Flame size={20} style={{ color: "#ef4444" }} />
                    ) : (
                      <AlertTriangle size={20} style={{ color: isSevere ? "#ef4444" : "#f59e0b" }} />
                    )}
                    <h2 style={{ fontSize: 17, margin: 0 }}>
                      {a.event || a.headline || "Disaster Alert"}
                    </h2>
                    {a.is_official && (
                      <span className="badge cyan" style={{ fontSize: 10 }}>
                        OFFICIAL GOVERNMENT ALERT
                      </span>
                    )}
                  </div>
                  <span className={`badge ${getSeverityBadgeClass(a.severity)}`}>
                    {a.severity}
                  </span>
                </div>

                <div style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 10px", display: "flex", gap: 14, flexWrap: "wrap" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <MapPin size={13} />
                    {a.location || `${a.district || ""}, ${a.state || "India"}`.replace(/^, /, "")}
                  </span>
                  {a.expires && (
                    <span>
                      Valid until: {new Date(a.expires).toLocaleString()}
                    </span>
                  )}
                  <span>Source: {a.source}</span>
                </div>

                {/* Description */}
                <p style={{ fontSize: 14, lineHeight: 1.5, color: "var(--text)" }}>
                  {a.description}
                </p>

                {/* What to do / Instruction */}
                {a.instruction && (
                  <div
                    style={{
                      margin: "12px 0",
                      padding: "10px 14px",
                      borderRadius: 8,
                      background: "rgba(16, 185, 129, 0.08)",
                      border: "1px solid rgba(16, 185, 129, 0.25)",
                      color: "#e2fbe8",
                      fontSize: 13,
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 4, color: "#10b981", letterSpacing: "0.04em", fontSize: 11 }}>
                      WHAT YOU SHOULD DO (OFFICIAL SAFETY INSTRUCTION)
                    </div>
                    {a.instruction}
                  </div>
                )}

                {/* Footer and Actions */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
                  <small style={{ color: "var(--muted)", fontSize: 11 }}>
                    CAP ID: {a.identifier || a.id.slice(0, 18)} · Certainty: {a.certainty || "Observed"} · Urgency: {a.urgency || "Immediate"}
                  </small>
                  <div style={{ display: "flex", gap: 8 }}>
                    {a.latitude && a.longitude && (
                      <button
                        className="button secondary"
                        style={{ fontSize: 12, padding: "4px 10px" }}
                        onClick={() => {
                          setPlace({
                            name: a.location || a.district || "Alert Area",
                            latitude: a.latitude!,
                            longitude: a.longitude!,
                          });
                          navigate("/globe");
                        }}
                      >
                        Inspect on Globe <ArrowUpRight size={13} />
                      </button>
                    )}
                    <button
                      className="button secondary"
                      style={{ fontSize: 12, padding: "4px 10px" }}
                      onClick={() => {
                        navigate(`/chat?q=${encodeURIComponent(`Explain this warning: ${a.event} for ${a.location || a.district || "my area"}`)}`);
                      }}
                    >
                      Ask WeatherGPT About This
                    </button>
                  </div>
                </div>
              </section>
            );
          })
        ) : (
          <Empty title="No Active Disaster Hazards in This Category">
            <ShieldCheck size={40} style={{ margin: "14px auto", color: "#10b981" }} />
            No active official warnings reported for this category. All clear from NDMA Sachet CAP, IMD bulletins, and INCOIS.
          </Empty>
        )}
      </div>

      {/* Dedicated Earthquake section when Earthquake tab is chosen */}
      {activeTab === "Earthquake" && (
        <div style={{ marginTop: 24 }}>
          <h3>Recent Seismological Events · USGS & India Seismology (M2.5+)</h3>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 12 }}>
            {includeGlobalQuakes
              ? "Showing global earthquake events. Foreign events are excluded from standard Indian push notifications."
              : "Filtered to Indian subcontinent and proximate fault lines (Lat 0°-40°N, Lon 60°-100°E)."}
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {quakes.slice(0, 15).map((q: any) => (
              <div key={q.id} className="card" style={{ padding: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>
                    M{q.magnitude} — {q.place}
                  </div>
                  <span className="badge neutral">Depth {q.depth} km</span>
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
                  {new Date(q.timestamp).toLocaleString()} · Coordinates: {q.latitude?.toFixed(2)}°, {q.longitude?.toFixed(2)}°
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
