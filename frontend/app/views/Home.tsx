import { useState, useEffect } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  Sparkles,
  Leaf,
  Plane,
  Waves,
  ChartNoAxesCombined,
  ShieldAlert,
  Eye,
  Sun,
  Droplets,
  Wind,
  Globe2,
} from "lucide-react";
import Globe from "@/components/Globe";
import { CurrentCard, Chart, Metric } from "@/components/WeatherUI";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApp } from "@/lib/context";
import { api, locationQuery, type Row } from "@/lib/api";
export default function Home() {
  const { place, setPlace, weather, navigate, alerts } = useApp();
  const [parameter, setParameter] = useState("temperature_2m"),
    [grid, setGrid] = useState<Row[]>([]),
    [air, setAir] = useState<Row>({});
  useEffect(() => {
    const c = new AbortController();
    setGrid([]);
    setAir({});
    api(`/api/globe/grid?${locationQuery(place)}`, { signal: c.signal })
      .then((d) => setGrid(d.cells))
      .catch(() => {});
    api(`/api/weather/air-quality?${locationQuery(place)}`, { signal: c.signal })
      .then(setAir)
      .catch(() => {});
    return () => c.abort();
  }, [place]);
  const current = weather?.current || {};
  const hourly =
    weather?.hourly
      .filter((h) => !weather.timestamp || h.time >= weather.timestamp.slice(0, 13) + ":00")
      .slice(0, 24) || [];
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            YOUR WORLD, IN PERSPECTIVE
          </div>
          <h1>A clearer view of your weather.</h1>
          <p>Local conditions. Global perspective. Intelligence for what’s next.</p>
        </div>
        <button className="button primary" onClick={() => navigate("/chat")}>
          <Sparkles size={16} />
          Ask WeatherGPT <ArrowUpRight size={15} />
        </button>
      </div>
      <div className="hero-grid">
        <CurrentCard />
        <section className="card globe-card">
          <div className="card-head">
            <h2 style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <Globe2 size={18} />
              Your world, live
            </h2>
            <span className={`badge ${grid.length ? "" : "neutral"}`}>
              {grid.length ? "REGIONAL WIND" : "BASE GLOBE"}
            </span>
          </div>
          <div className="globe-tag">
            EARTH EXPLORER
            <br />
            {place.latitude.toFixed(2)}° N · {place.longitude.toFixed(2)}° E
          </div>
          <Globe place={place} onSelect={setPlace} cells={grid} />
          <div className="globe-footer">
            <span>Drag to rotate · Scroll to zoom</span>
            <button
              onClick={() => navigate("/globe")}
              style={{ display: "flex", alignItems: "center", gap: 7, color: "#88e1d4" }}
            >
              Explore live globe <ArrowUpRight size={14} />
            </button>
          </div>
        </section>
      </div>
      <div className="metric-strip">
        <Metric icon={Droplets} label="Precipitation" value={current.precipitation} unit="mm" />
        <Metric
          icon={Eye}
          label="Visibility"
          value={current.visibility == null ? null : current.visibility / 1000}
          unit="km"
        />
        <Metric
          icon={Sun}
          label="UV index · daily max"
          value={weather?.daily[0]?.uv_index_max}
          unit=""
        />
        <Metric icon={Wind} label="Air quality · EU AQI" value={air.european_aqi} unit="" />
      </div>
      <div className="below-grid">
        <section className="card">
          <div className="card-head">
            <h2>Next 24 hours</h2>
            <Tabs value={parameter} onValueChange={(v) => setParameter(String(v))}>
              <TabsList className="chart-switch">
                <TabsTrigger value="temperature_2m">Temperature</TabsTrigger>
                <TabsTrigger value="precipitation_probability">Rain</TabsTrigger>
                <TabsTrigger value="wind_speed_10m">Wind</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          <Chart
            data={hourly}
            field={parameter}
            unit={
              parameter === "temperature_2m" ? "°C" : parameter === "wind_speed_10m" ? "km/h" : "%"
            }
          />
          <button
            onClick={() => navigate("/forecast")}
            className="cyan"
            style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 7, marginTop: 12 }}
          >
            View full forecast <ArrowRight size={13} />
          </button>
        </section>
        <section className="card assistant-card">
          <div className="card-head">
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="assistant-icon">
                <Sparkles size={20} />
              </span>
              <h2>Meet your weather copilot</h2>
            </div>
          </div>
          <p>
            Turn weather data into everyday clarity.
            <br />
            Just ask, in English or Hindi.
          </p>
          {["Will it rain here tomorrow?", "What does today’s weather mean for me?"].map((q) => (
            <button
              key={q}
              className="prompt"
              onClick={() => navigate("/chat?q=" + encodeURIComponent(q))}
            >
              {q}
              <ArrowUpRight size={14} />
            </button>
          ))}
          <small style={{ display: "block", marginTop: 17 }}>
            Grounded in weather data · Works without an AI key
          </small>
        </section>
      </div>
      <div className="alert-banner">
        <ShieldAlert size={22} />
        <div>
          <h3>
            {alerts.length
              ? `${alerts.length} weather screening alert${alerts.length > 1 ? "s" : ""}`
              : "Stay one step ahead of changing conditions"}
          </h3>
          <p>
            {alerts.length
              ? alerts[0].description
              : "Local threshold screening is active. Official warning feeds are not connected."}
          </p>
        </div>
        <a
          href="/alerts"
          onClick={(e) => {
            e.preventDefault();
            navigate("/alerts");
          }}
        >
          Alert center ↗
        </a>
      </div>
      <div className="section-heading">
        <h2>Intelligence for every horizon</h2>
        <span className="eyebrow" style={{ fontSize: 10 }}>
          GO BEYOND THE FORECAST
        </span>
      </div>
      <div className="feature-grid">
        {[
          [
            Leaf,
            "Agriculture",
            "Plan fieldwork around rain, wind, and growing conditions.",
            "/agriculture",
          ],
          [Plane, "Aviation", "A clear view of visibility, gusts, and pressure.", "/aviation"],
          [Waves, "Marine", "Explore waves, ocean conditions, and coastal weather.", "/marine"],
          [
            ChartNoAxesCombined,
            "Climate analytics",
            "Understand the patterns behind a changing climate.",
            "/climate",
          ],
        ].map(([Icon, title, desc, href]: any) => (
          <section key={href} className="card feature">
            <Icon size={22} />
            <h3>{title}</h3>
            <p>{desc}</p>
            <a
              href={href}
              onClick={(e) => {
                e.preventDefault();
                navigate(href);
              }}
            >
              Explore {title.toLowerCase()} ↗
            </a>
          </section>
        ))}
      </div>
    </>
  );
}
