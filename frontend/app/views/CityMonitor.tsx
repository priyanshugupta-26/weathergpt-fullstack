import { useEffect, useState } from "react";
import { Building2, Droplets, Thermometer, Wind, AlertTriangle, ShieldCheck, RefreshCw, Eye } from "lucide-react";
import { Heading } from "@/components/WeatherUI";
import { api, type Row } from "@/lib/api";
import { useApp } from "@/lib/context";

export default function CityMonitor() {
  const { setPlace, navigate } = useApp();
  const [data, setData] = useState<{ cities: Row[]; timestamp: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  const load = () => {
    setLoading(true);
    setError("");
    api("/api/city-monitor")
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const selectCity = (city: Row) => {
    setPlace({
      name: city.name,
      latitude: city.latitude,
      longitude: city.longitude,
      admin1: city.state,
      country: "India",
    });
    navigate("/");
  };

  const cities = (data?.cities || []).filter((c) => {
    const matchesQuery =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.state.toLowerCase().includes(search.toLowerCase());
    if (riskFilter === "FLOOD") return matchesQuery && c.flood_risk !== "LOW";
    if (riskFilter === "HEAT") return matchesQuery && c.heat_risk !== "LOW";
    return matchesQuery;
  });

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 60 }}>
      <Heading
        title="Smart City Intelligence Center"
        subtitle="Real-time multi-city meteorological monitoring, urban flash flood vulnerability, and heat stress diagnostics across India."
      >
        <button className="button secondary" onClick={load} disabled={loading}>
          <RefreshCw size={15} />
          Refresh cities
        </button>
      </Heading>

      {error && <div className="error-note">{error}</div>}

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <input
          type="text"
          placeholder="Filter smart cities by name or state..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input"
          style={{ maxWidth: 360, flex: 1 }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          {[
            ["ALL", "All cities"],
            ["FLOOD", "Flood Risk Alert"],
            ["HEAT", "Heatwave Alert"],
          ].map(([val, label]) => (
            <button
              key={val}
              className={`button secondary ${riskFilter === val ? "active" : ""}`}
              onClick={() => setRiskFilter(val)}
              style={{
                background: riskFilter === val ? "var(--accent, rgba(56,189,248,0.2))" : undefined,
                borderColor: riskFilter === val ? "var(--brand, #38bdf8)" : undefined,
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading" aria-label="Loading cities" />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
          {cities.map((city) => {
            const hasFloodRisk = city.flood_risk === "HIGH" || city.flood_risk === "MODERATE";
            const hasHeatRisk = city.heat_risk === "HIGH" || city.heat_risk === "MODERATE";

            return (
              <div
                key={city.name}
                className="card hover-card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  transition: "transform 0.15s ease, border-color 0.15s ease",
                  borderLeft: hasFloodRisk
                    ? "4px solid #38bdf8"
                    : hasHeatRisk
                    ? "4px solid #f97316"
                    : "4px solid #22c55e",
                }}
                onClick={() => selectCity(city)}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <div>
                      <h3 style={{ fontSize: 18, margin: 0 }}>{city.name}</h3>
                      <small className="muted">{city.state} · India</small>
                    </div>
                    <span className="badge" style={{ fontSize: 11 }}>
                      {city.source || "Open-Meteo"}
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, margin: "14px 0" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Thermometer size={18} color="#f97316" />
                      <div>
                        <div style={{ fontSize: 18, fontWeight: 600 }}>{city.temperature}°C</div>
                        <small className="muted">Ambient</small>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Droplets size={18} color="#38bdf8" />
                      <div>
                        <div style={{ fontSize: 18, fontWeight: 600 }}>{city.precipitation} mm</div>
                        <small className="muted">Precipitation</small>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Wind size={18} color="#94a3b8" />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 500 }}>{city.wind_speed} km/h</div>
                        <small className="muted">Surface wind</small>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <Building2 size={18} color="#94a3b8" />
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 500 }}>{city.relative_humidity}%</div>
                        <small className="muted">Moisture</small>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                    <span
                      className="badge"
                      style={{
                        background:
                          city.flood_risk === "HIGH"
                            ? "rgba(239,68,68,0.2)"
                            : city.flood_risk === "MODERATE"
                            ? "rgba(245,158,11,0.2)"
                            : "rgba(34,197,94,0.1)",
                        color:
                          city.flood_risk === "HIGH"
                            ? "#ef4444"
                            : city.flood_risk === "MODERATE"
                            ? "#f59e0b"
                            : "#22c55e",
                        border: "none",
                        fontSize: 11,
                      }}
                    >
                      Flood: {city.flood_risk}
                    </span>

                    <span
                      className="badge"
                      style={{
                        background:
                          city.heat_risk === "HIGH"
                            ? "rgba(239,68,68,0.2)"
                            : city.heat_risk === "MODERATE"
                            ? "rgba(245,158,11,0.2)"
                            : "rgba(34,197,94,0.1)",
                        color:
                          city.heat_risk === "HIGH"
                            ? "#ef4444"
                            : city.heat_risk === "MODERATE"
                            ? "#f59e0b"
                            : "#22c55e",
                        border: "none",
                        fontSize: 11,
                      }}
                    >
                      Heat: {city.heat_risk}
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginTop: 16,
                    paddingTop: 10,
                    borderTop: "1px solid var(--border)",
                    fontSize: 12,
                    color: "var(--brand, #38bdf8)",
                  }}
                >
                  <span>Select location</span>
                  <Eye size={14} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
