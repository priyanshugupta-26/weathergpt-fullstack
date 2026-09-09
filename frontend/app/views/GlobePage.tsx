import { useEffect, useState } from "react";
import {
  Wind,
  Droplets,
  Thermometer,
  Gauge,
  Cloud,
  Orbit,
  Zap,
  Activity,
  Waves,
  ShieldAlert,
  LocateFixed,
  RefreshCw,
} from "lucide-react";
import Globe from "@/components/Globe";
import { Heading, Freshness, Empty } from "@/components/WeatherUI";
import { useApp } from "@/lib/context";
import { api, locationQuery, number, type Row } from "@/lib/api";
const layers = [
  ["Wind", Wind, "km/h", "0 — 60"],
  ["Rainfall", Droplets, "mm", "0 — 20"],
  ["Temperature", Thermometer, "°C", "−10 — 45"],
  ["Humidity", Droplets, "%", "0 — 100"],
  ["Pressure", Gauge, "hPa", "970 — 1040"],
  ["Cloud Cover", Cloud, "%", "0 — 100"],
  ["Cyclone", Orbit, "", ""],
  ["Storm", Zap, "", ""],
  ["Earthquake", Activity, "magnitude", "2.5+"],
  ["Air Quality", Wind, "EU AQI", ""],
  ["Ocean / Marine", Waves, "m", ""],
  ["Alerts", ShieldAlert, "", ""],
] as const;
export default function GlobePage() {
  const { place, setPlace, weather, geo, alerts } = useApp();
  const [layer, setLayer] = useState("Wind"),
    [grid, setGrid] = useState<Row>({ cells: [], status: "loading" }),
    [quakes, setQuakes] = useState<Row>({ events: [] }),
    [selected, setSelected] = useState<Row | null>(null),
    [tick, setTick] = useState(0),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    const c = new AbortController();
    setGrid({ cells: [], status: "loading" });
    setLoading(true);
    api(`/api/globe/grid?${locationQuery(place)}`, { signal: c.signal })
      .then(setGrid)
      .catch((e) => {
        if (e.name !== "AbortError")
          setGrid({ cells: [], status: "unavailable", message: e.message });
      })
      .finally(() => {
        if (!c.signal.aborted) setLoading(false);
      });
    return () => c.abort();
  }, [place, tick]);
  useEffect(() => {
    if (layer !== "Earthquake") return;
    const c = new AbortController();
    api("/api/earthquakes", { signal: c.signal })
      .then(setQuakes)
      .catch((e) => setQuakes({ events: [], status: "unavailable", message: e.message }));
    return () => c.abort();
  }, [layer, tick]);
  const info = layers.find((l) => l[0] === layer)!;
  const unavailable = ["Cyclone", "Storm", "Air Quality", "Ocean / Marine", "Alerts"].includes(
    layer,
  );
  return (
    <>
      <Heading
        title="A world in motion."
        subtitle="Explore Earth. Select a location. See the conditions behind the forecast."
      >
        <div className="button-row">
          <button className="button" onClick={geo}>
            <LocateFixed size={16} />
            My location
          </button>
          <button className="button" onClick={() => setTick((t) => t + 1)}>
            <RefreshCw size={15} />
            Refresh layers
          </button>
        </div>
      </Heading>
      <div className="globe-layout">
        <aside className="card layer-list">
          <div className="eyebrow" style={{ margin: "4px 10px 14px" }}>
            WEATHER LAYERS
          </div>
          {layers.map(([name, Icon]) => (
            <button
              key={name}
              className={layer === name ? "active" : ""}
              onClick={() => {
                setLayer(name);
                setSelected(null);
              }}
            >
              <Icon size={17} />
              {name}
            </button>
          ))}
          <div className="legend">
            <strong>
              {layer} · {info[2]}
            </strong>
            {info[3] && (
              <>
                <div className="legend-bar" />
                <span>{info[3]}</span>
              </>
            )}
            <p className="muted" style={{ fontSize: 11, marginTop: 10 }}>
              {layer === "Earthquake"
                ? "USGS · last 24 hours"
                : grid.source || "Open-Meteo regional samples"}
            </p>
            <small>
              {loading
                ? "Refreshing…"
                : grid.fetched_at
                  ? `Retrieved ${new Date(grid.fetched_at).toLocaleTimeString()}`
                  : "Data unavailable"}
            </small>
          </div>
        </aside>
        <div className="globe-big">
          <section className="card globe-card">
            <div className="card-head">
              <h2>{layer}</h2>
              <span className={`badge ${unavailable ? "neutral" : ""}`}>
                {unavailable
                  ? "LAYER UNAVAILABLE"
                  : loading
                    ? "UPDATING"
                    : layer === "Earthquake"
                      ? quakes.status?.toUpperCase() || "LOADING"
                      : grid.status?.toUpperCase()}
              </span>
            </div>
            <Globe
              place={place}
              onSelect={setPlace}
              layer={layer}
              cells={grid.cells}
              events={quakes.events}
              onEvent={setSelected}
            />
            <div className="globe-footer">
              <span>Drag · Zoom · Click to inspect</span>
              <span>
                {place.latitude.toFixed(3)}°, {place.longitude.toFixed(3)}°
              </span>
            </div>
          </section>
          {unavailable ? (
            <div className="error-note">
              {layer === "Cyclone" || layer === "Storm"
                ? "Official cyclone positions and storm tracks are not connected. No active storms are inferred."
                : layer === "Alerts"
                  ? `${alerts.length} local screening alerts. Open the Alert center for details. Official geospatial alert polygons are not connected.`
                  : layer === "Air Quality"
                    ? "Regional air-quality raster data is unavailable. The overview shows the selected location’s EU AQI when available."
                    : "Global ocean raster data is unavailable. Open Marine for provider-backed wave and ocean forecasts."}
            </div>
          ) : grid.status === "unavailable" && layer !== "Earthquake" ? (
            <div className="error-note">{grid.message}</div>
          ) : (
            <p className="freshness">
              {layer === "Wind"
                ? "Particles follow interpolated 10 m wind vectors from sparse 3° regional samples. Motion is accelerated for visibility; density is fixed at 180 particles."
                : layer === "Earthquake"
                  ? "Marker size reflects reported magnitude. Click a marker for source details."
                  : "Colored cells show regional model samples, not radar coverage. Select a location to refresh the sampled region."}
            </p>
          )}
        </div>
      </div>
      <div className="detail-grid">
        <section className="card">
          <h2>{selected ? "Earthquake report" : place.name}</h2>
          {selected ? (
            <>
              {[
                ["Place", selected.place],
                ["Magnitude", selected.magnitude],
                ["Depth", `${selected.depth} km`],
                ["Reported", selected.timestamp],
              ].map(([k, v]) => (
                <div className="detail-list" key={k}>
                  <span className="muted">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
              <a
                href={selected.url}
                target="_blank"
                rel="noreferrer"
                className="button"
                style={{ marginTop: 14 }}
              >
                Open USGS report ↗
              </a>
            </>
          ) : (
            <>
              {[
                ["Temperature", `${number(weather?.current.temperature_2m)} °C`],
                ["Wind", `${number(weather?.current.wind_speed_10m)} km/h`],
                ["Direction", `${number(weather?.current.wind_direction_10m)}° from`],
                ["Gusts", `${number(weather?.current.wind_gusts_10m)} km/h`],
              ].map(([k, v]) => (
                <div className="detail-list" key={k}>
                  <span className="muted">{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </>
          )}
        </section>
        <section className="card">
          <h2>Atmosphere</h2>
          {[
            ["Humidity", `${number(weather?.current.relative_humidity_2m)}%`],
            ["Pressure", `${number(weather?.current.pressure_msl)} hPa`],
            ["Cloud cover", `${number(weather?.current.cloud_cover)}%`],
            ["Precipitation", `${number(weather?.current.precipitation, 1)} mm`],
          ].map(([k, v]) => (
            <div className="detail-list" key={k}>
              <span className="muted">{k}</span>
              <span>{v}</span>
            </div>
          ))}
          <Freshness />
        </section>
        <section className="card">
          <h2>Reading the globe</h2>
          <p className="muted" style={{ fontSize: 14, marginTop: 16 }}>
            Weather cells cover a 12° region around your selection. Wind direction is
            meteorological: where the wind comes from.
          </p>
          <p className="muted" style={{ fontSize: 14, marginTop: 15 }}>
            Missing coverage is not evidence of safe conditions. Always consult official warnings.
          </p>
        </section>
      </div>
    </>
  );
}
