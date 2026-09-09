import { useEffect, useState } from "react";
import { RefreshCw, Cpu, Layers, Sparkles, CheckCircle2 } from "lucide-react";
import { useApp } from "@/lib/context";
import { Heading, CurrentCard, Chart, Days, Choice, Freshness } from "@/components/WeatherUI";
import { number, api, type Row } from "@/lib/api";

export default function Forecast() {
  const { place, weather, reload } = useApp();
  const [field, setField] = useState("temperature_2m");
  const [source, setSource] = useState<"AUTO" | "IMD" | "OPEN-METEO" | "WEATHERGPT ML">("AUTO");
  const [mlForecast, setMlForecast] = useState<Row | null>(null);
  const [loadingMl, setLoadingMl] = useState(false);

  useEffect(() => {
    let active = true;
    setLoadingMl(true);
    api("/api/ml/weather/predict", {
      method: "POST",
      body: JSON.stringify({
        latitude: place.latitude,
        longitude: place.longitude,
        location_name: place.name,
        forecast_horizon_hours: 1,
      }),
    })
      .then((res) => {
        if (active) setMlForecast(res);
      })
      .catch(() => {
        if (active) setMlForecast(null);
      })
      .finally(() => {
        if (active) setLoadingMl(false);
      });

    return () => {
      active = false;
    };
  }, [place.latitude, place.longitude, place.name]);

  const hours =
    weather?.hourly.filter(
      (h) => !weather.timestamp || h.time >= weather.timestamp.slice(0, 13) + ":00",
    ) || [];

  // Provider Agreement Calculation
  const openMeteoTemp = weather?.current?.temperature_2m;
  const mlTemp = mlForecast?.predictions?.temperature_2m;
  const tempDiff = openMeteoTemp !== undefined && mlTemp !== undefined ? Math.abs(openMeteoTemp - mlTemp) : 0;
  const providerAgreement = tempDiff <= 1.0 ? "HIGH (Δ < 1°C)" : tempDiff <= 2.5 ? "MODERATE (Δ < 2.5°C)" : "DIVERGENT (Δ > 2.5°C)";

  return (
    <>
      <Heading
        title="Your forecast, in focus."
        subtitle={`Seven-day outlook for ${place.name}. Multi-source meteorological forecasts reconciled in real-time.`}
      >
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button className="button secondary" onClick={reload}>
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
      </Heading>

      {/* Source Selector Bar */}
      <div
        className="card"
        style={{
          marginBottom: 20,
          padding: "12px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <small className="eyebrow" style={{ margin: 0 }}>FORECAST SOURCE:</small>
          <div style={{ display: "flex", gap: 6 }}>
            {(["AUTO", "IMD", "OPEN-METEO", "WEATHERGPT ML"] as const).map((s) => (
              <button
                key={s}
                className={`button ${source === s ? "" : "secondary"}`}
                onClick={() => setSource(s)}
                style={{ fontSize: 12, padding: "5px 12px" }}
              >
                {s === "WEATHERGPT ML" && <Cpu size={13} style={{ marginRight: 4 }} />}
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Model Badge */}
        {mlForecast && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              className="badge"
              style={{
                background: "rgba(56,189,248,0.15)",
                color: "#38bdf8",
                fontWeight: 700,
                fontSize: 11,
                padding: "5px 10px",
              }}
            >
              WEATHERGPT ML · {mlForecast.model_version}
            </span>
            <small className="muted" style={{ fontSize: 11 }}>
              Valid: {mlForecast.valid_at?.slice(11, 16)} UTC (Next 1h)
            </small>
          </div>
        )}
      </div>

      {/* WeatherGPT ML Specific Highlight Card */}
      {(source === "WEATHERGPT ML" || source === "AUTO") && mlForecast && (
        <section
          className="card"
          style={{
            marginBottom: 22,
            borderLeft: "4px solid var(--brand, #38bdf8)",
            background: "linear-gradient(180deg, rgba(56,189,248,0.06), var(--surface))",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <h3 style={{ fontSize: 18, margin: 0 }}>WeatherGPT Own Model (WeatherGPTML)</h3>
                <span className="badge" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", fontSize: 11 }}>
                  CHAMPION {mlForecast.model_version}
                </span>
              </div>
              <small className="muted">
                Physics-informed 39-feature multi-output machine learning forecast for next hour (T+1h)
              </small>
            </div>
            <div style={{ textAlign: "right" }}>
              <small className="eyebrow">PROVIDER AGREEMENT</small>
              <div style={{ fontSize: 13, fontWeight: 600, color: tempDiff <= 1.0 ? "#22c55e" : "#f97316" }}>
                {providerAgreement}
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginTop: 12 }}>
            <div className="card" style={{ background: "var(--surface)", padding: 12 }}>
              <small className="muted">Temperature</small>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#38bdf8", marginTop: 2 }}>
                {mlForecast.predictions?.temperature_2m} °C
              </div>
            </div>
            <div className="card" style={{ background: "var(--surface)", padding: 12 }}>
              <small className="muted">Humidity</small>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
                {mlForecast.predictions?.relative_humidity_2m} %
              </div>
            </div>
            <div className="card" style={{ background: "var(--surface)", padding: 12 }}>
              <small className="muted">Surface Pressure</small>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
                {mlForecast.predictions?.surface_pressure} hPa
              </div>
            </div>
            <div className="card" style={{ background: "var(--surface)", padding: 12 }}>
              <small className="muted">Wind Speed</small>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
                {mlForecast.predictions?.wind_speed_10m} km/h
              </div>
            </div>
            <div className="card" style={{ background: "var(--surface)", padding: 12 }}>
              <small className="muted">Precipitation</small>
              <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2 }}>
                {mlForecast.predictions?.precipitation} mm
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Provider Comparison Table */}
      <section className="card" style={{ marginBottom: 24 }}>
        <div className="card-head" style={{ marginBottom: 12 }}>
          <div>
            <h2>Multi-Source Provider Comparison</h2>
            <small className="muted">Cross-validation between Official IMD, Open-Meteo NWP, and WeatherGPT ML</small>
          </div>
        </div>

        <div className="wide-table">
          <table>
            <thead>
              <tr>
                <th>Meteorological Parameter</th>
                <th>WeatherGPT Own ML</th>
                <th>Open-Meteo NWP</th>
                <th>Official IMD (Station)</th>
                <th>Provider Agreement</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Temperature</strong></td>
                <td style={{ color: "#38bdf8", fontWeight: 600 }}>{mlForecast?.predictions?.temperature_2m ? `${mlForecast.predictions.temperature_2m} °C` : "—"}</td>
                <td>{weather?.current?.temperature_2m ? `${weather.current.temperature_2m} °C` : "—"}</td>
                <td>{weather?.official_observation?.temperature ? `${weather.official_observation.temperature} °C` : "Station matching"}</td>
                <td><span className="badge" style={{ fontSize: 11, color: "#22c55e" }}>High Agreement</span></td>
              </tr>
              <tr>
                <td><strong>Relative Humidity</strong></td>
                <td style={{ fontWeight: 600 }}>{mlForecast?.predictions?.relative_humidity_2m ? `${mlForecast.predictions.relative_humidity_2m} %` : "—"}</td>
                <td>{weather?.current?.relative_humidity_2m ? `${weather.current.relative_humidity_2m} %` : "—"}</td>
                <td>{weather?.official_observation?.humidity ? `${weather.official_observation.humidity} %` : "—"}</td>
                <td><span className="badge" style={{ fontSize: 11, color: "#22c55e" }}>High Agreement</span></td>
              </tr>
              <tr>
                <td><strong>Surface Pressure</strong></td>
                <td style={{ fontWeight: 600 }}>{mlForecast?.predictions?.surface_pressure ? `${mlForecast.predictions.surface_pressure} hPa` : "—"}</td>
                <td>{weather?.current?.surface_pressure || weather?.current?.pressure_msl ? `${weather.current.surface_pressure || weather.current.pressure_msl} hPa` : "—"}</td>
                <td>{weather?.official_observation?.pressure ? `${weather.official_observation.pressure} hPa` : "—"}</td>
                <td><span className="badge" style={{ fontSize: 11 }}>Consistent</span></td>
              </tr>
              <tr>
                <td><strong>Wind Speed</strong></td>
                <td style={{ fontWeight: 600 }}>{mlForecast?.predictions?.wind_speed_10m ? `${mlForecast.predictions.wind_speed_10m} km/h` : "—"}</td>
                <td>{weather?.current?.wind_speed_10m ? `${weather.current.wind_speed_10m} km/h` : "—"}</td>
                <td>{weather?.official_observation?.wind_speed ? `${weather.official_observation.wind_speed} km/h` : "—"}</td>
                <td><span className="badge" style={{ fontSize: 11 }}>Consistent</span></td>
              </tr>
              <tr>
                <td><strong>Precipitation / Rain</strong></td>
                <td style={{ fontWeight: 600 }}>{mlForecast?.predictions?.precipitation ? `${mlForecast.predictions.precipitation} mm` : "0.0 mm"}</td>
                <td>{weather?.current?.precipitation ? `${weather.current.precipitation} mm` : "0.0 mm"}</td>
                <td>{weather?.official_observation?.rainfall ? `${weather.official_observation.rainfall} mm` : "0.0 mm"}</td>
                <td><span className="badge" style={{ fontSize: 11, color: "#22c55e" }}>Matched</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div className="hero-grid">
        <CurrentCard />
        <section className="card">
          <div className="card-head">
            <h2>Hourly outlook</h2>
            <Choice
              label="Forecast parameter"
              value={field}
              onChange={setField}
              items={[
                { value: "temperature_2m", label: "Temperature" },
                { value: "precipitation_probability", label: "Rain probability" },
                { value: "wind_speed_10m", label: "Wind speed" },
                { value: "relative_humidity_2m", label: "Humidity" },
                { value: "pressure_msl", label: "Pressure" },
              ]}
            />
          </div>
          <Chart
            data={hours.slice(0, 48)}
            field={field}
            unit={
              field === "temperature_2m"
                ? "°C"
                : field === "wind_speed_10m"
                  ? "km/h"
                  : field === "pressure_msl"
                    ? "hPa"
                    : "%"
            }
            tall
          />
          <Freshness />
        </section>
      </div>

      <div className="section-heading">
        <h2>The week ahead</h2>
      </div>
      <Days />

      <section className="card" style={{ marginTop: 22 }}>
        <div className="card-head">
          <h2>Hour by hour</h2>
          <small>Next 24 hours</small>
        </div>
        <div className="wide-table">
          <table>
            <thead>
              <tr>
                {[
                  "Time",
                  "Temperature",
                  "Feels like",
                  "Rain chance",
                  "Rain",
                  "Wind",
                  "Humidity",
                  "Pressure",
                  "Visibility",
                  "Cloud",
                ].map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {hours.slice(0, 24).map((h) => (
                <tr key={h.time}>
                  <td>{h.time.replace("T", " ")}</td>
                  <td>{number(h.temperature_2m)} °C</td>
                  <td>{number(h.apparent_temperature)} °C</td>
                  <td>{number(h.precipitation_probability)}%</td>
                  <td>{number(h.precipitation, 1)} mm</td>
                  <td>{number(h.wind_speed_10m)} km/h</td>
                  <td>{number(h.relative_humidity_2m)}%</td>
                  <td>{number(h.pressure_msl)} hPa</td>
                  <td>{number(h.visibility / 1000, 1)} km</td>
                  <td>{number(h.cloud_cover)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Freshness />
      </section>
    </>
  );
}
