import { useState, useEffect } from "react";
import { ShieldAlert, ShieldCheck, Bell, ArrowUpRight } from "lucide-react";
import { useApp } from "@/lib/context";
import { Heading, Empty } from "@/components/WeatherUI";
import { api, type Row } from "@/lib/api";
import { t, getLanguageInfo } from "@/lib/i18n";
export default function Alerts() {
  const { alerts, place, weather, navigate, setPlace, language } = useApp();
  const [filter, setFilter] = useState("All"),
    [quakes, setQuakes] = useState<Row>({ events: [] });
  useEffect(() => {
    if (filter !== "Earthquake") return;
    api("/api/earthquakes")
      .then(setQuakes)
      .catch(() => setQuakes({ events: [], status: "unavailable" }));
  }, [filter]);
  const shown = alerts.filter((a) => filter === "All" || a.alert_type === filter);
  return (
    <>
      <Heading
        title="Awareness starts here."
        subtitle={`Weather screening for ${place.name}. Live updates while this page is open.`}
      >
        <button className="button" onClick={() => navigate("/settings")}>
          <Bell size={15} />
          Notification settings
        </button>
      </Heading>
      <div className="metric-strip" style={{ gridTemplateColumns: "repeat(3,1fr)" }}>
        <section className="card">
          <div className="eyebrow">LOCAL SCREENING</div>
          <h1 style={{ marginTop: 10 }}>{alerts.length}</h1>
          <small>Threshold alerts</small>
        </section>
        <section className="card">
          <div className="eyebrow">WEATHER DATA</div>
          <h2 style={{ marginTop: 16 }}>
            {weather?.status === "live" ? "Available" : "Unavailable"}
          </h2>
          <small>Open-Meteo model conditions</small>
        </section>
        <section className="card">
          <div className="eyebrow">OFFICIAL WARNINGS</div>
          <h2 style={{ marginTop: 16 }}>Not connected</h2>
          <small>Check local meteorological authorities</small>
        </section>
      </div>
      <div className="alert-filters">
        {["All", "Weather", "Cyclone", "Flood", "Earthquake", "Heat", "Wind", "Marine"].map((f) => (
          <button key={f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
      </div>
      {filter === "Earthquake" ? (
        <>
          <h2>Global earthquake reports · USGS M2.5+ · past 24 hours</h2>
          {quakes.events.map((q: Row) => (
            <section key={q.id} className="card alert-item">
              <div className="card-head">
                <h3>
                  M{q.magnitude} · {q.place}
                </h3>
                <span className="badge warn">REPORTED EVENT</span>
              </div>
              <p>
                Depth {q.depth} km · {new Date(q.timestamp).toLocaleString()}
              </p>
              <button
                className="button"
                onClick={() => {
                  setPlace({ name: q.place, latitude: q.latitude, longitude: q.longitude });
                  navigate("/globe");
                }}
              >
                Inspect location <ArrowUpRight size={14} />
              </button>{" "}
              <a className="button" href={q.url} target="_blank" rel="noreferrer">
                USGS report
              </a>
            </section>
          ))}
          {!quakes.events.length && (
            <Empty
              title={quakes.status === "unavailable" ? "USGS unavailable" : "No reports loaded"}
            >
              The feed may be loading or contain no matching reports.
            </Empty>
          )}
        </>
      ) : shown.length ? (
        shown.map((a) => (
          <section key={a.id} className="card alert-item">
            <div className="card-head">
              <h2>{a.description}</h2>
              <span className="badge warn">{a.severity}</span>
            </div>
            <p>
              {a.location} · {a.timestamp}
            </p>
            {a.original_text || a.data_source?.toLowerCase().includes("imd") ? (
              <div style={{ margin: "10px 0", padding: "10px 14px", borderRadius: 8, background: "rgba(255,255,255,0.03)", border: "1px solid var(--line)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#f59e0b", letterSpacing: "0.05em", marginBottom: 4 }}>
                  {t("alerts.imdOriginal", language) || "IMD ORIGINAL"}
                </div>
                <div style={{ fontSize: 13, color: "var(--text)", marginBottom: 8 }}>
                  {a.original_text || a.description}
                </div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--cyan)", letterSpacing: "0.05em", marginBottom: 4 }}>
                  {t("alerts.weathergptTranslation", language) || "WEATHERGPT TRANSLATION"} — {getLanguageInfo(language).name.toUpperCase()}
                </div>
                <div style={{ fontSize: 13, color: "var(--muted)" }}>
                  {a.recommendation || a.description}
                </div>
              </div>
            ) : (
              <p>{a.recommendation}</p>
            )}
            <small>
              {a.data_source} · {a.model_source} · Expires{" "}
              {new Date(a.expires).toLocaleTimeString()}
            </small>
            <p>
              <button className="button" onClick={() => navigate("/globe")}>
                View location on globe ↗
              </button>
            </p>
          </section>
        ))
      ) : (
        <Empty
          title={
            weather?.status === "live"
              ? "No matching screening alerts"
              : "Conditions cannot currently be evaluated"
          }
        >
          <ShieldCheck size={36} style={{ margin: "12px auto", color: "var(--cyan)" }} />
          No alert here is not an all-clear. Cyclone, flood, marine, and official warning feeds
          require additional data.
        </Empty>
      )}
      <div className="alert-banner">
        <ShieldAlert size={20} />
        <p>
          Automated screening uses explicit temperature, rain, and wind thresholds. It is not an
          official warning service or a complete disaster prediction.
        </p>
      </div>
    </>
  );
}
