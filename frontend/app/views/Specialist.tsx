import { useEffect, useState } from "react";
import {
  Leaf,
  Plane,
  Waves,
  Wind,
  Droplets,
  Thermometer,
  Eye,
  Gauge,
  Cloud,
  Sun,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { api, locationQuery, number, type Row } from "@/lib/api";
import { Heading, Metric, Chart, Freshness, Empty } from "@/components/WeatherUI";
export default function Specialist() {
  const { route, place, weather, setPlace, alerts } = useApp();
  const [marine, setMarine] = useState<Row>({ hourly: [] }),
    [busy, setBusy] = useState(false),
    [tick, setTick] = useState(0);
  const isMarine = route === "/marine",
    aviation = route === "/aviation";
  useEffect(() => {
    if (!isMarine) return;
    const c = new AbortController();
    setMarine({ hourly: [] });
    setBusy(true);
    api(`/api/weather/marine?${locationQuery(place)}`, { signal: c.signal })
      .then(setMarine)
      .catch((e) => {
        if (e.name !== "AbortError")
          setMarine({ hourly: [], status: "unavailable", message: e.message });
      })
      .finally(() => {
        if (!c.signal.aborted) setBusy(false);
      });
    return () => c.abort();
  }, [place, isMarine, tick]);
  const c = weather?.current || {},
    d = weather?.daily[0] || {},
    m =
      marine.hourly.find(
        (h: Row) => !weather?.timestamp || h.time >= weather.timestamp.slice(0, 13) + ":00",
      ) || {};
  const title = isMarine
    ? "Conditions beyond the coast."
    : aviation
      ? "A clearer view of the sky."
      : "Weather for a growing world.";
  const suggestions = isMarine
    ? [
        { name: "Mumbai offshore", latitude: 18.6, longitude: 72.5 },
        { name: "Chennai offshore", latitude: 13, longitude: 80.6 },
      ]
    : aviation
      ? [
          { name: "DEL · Delhi airport", latitude: 28.5562, longitude: 77.1 },
          { name: "BOM · Mumbai airport", latitude: 19.0896, longitude: 72.8656 },
          { name: "PAT · Patna airport", latitude: 25.5913, longitude: 85.087 },
        ]
      : [];
  return (
    <>
      <Heading
        title={title}
        subtitle={`${isMarine ? "Marine" : aviation ? "Aviation" : "Agriculture"} intelligence · ${place.name}`}
      />
      {suggestions.length > 0 && (
        <div className="button-row" style={{ marginBottom: 20 }}>
          {suggestions.map((p) => (
            <button className="button" key={p.name} onClick={() => setPlace(p)}>
              {isMarine ? <Waves size={15} /> : <Plane size={15} />} {p.name}
            </button>
          ))}
        </div>
      )}
      <div className="metric-strip">
        {isMarine ? (
          <>
            <Metric icon={Waves} label="Wave height" value={m.wave_height} unit="m" />
            <Metric icon={Wind} label="Wave direction" value={m.wave_direction} unit="°" />
            <Metric
              icon={Thermometer}
              label="Sea temperature"
              value={m.sea_surface_temperature}
              unit="°C"
            />
            <Metric
              icon={Waves}
              label="Ocean current"
              value={m.ocean_current_velocity}
              unit="km/h"
            />
          </>
        ) : aviation ? (
          <>
            <Metric
              icon={Eye}
              label="Visibility"
              value={c.visibility == null ? null : c.visibility / 1000}
              unit="km"
            />
            <Metric icon={Wind} label="Wind gusts" value={c.wind_gusts_10m} unit="km/h" />
            <Metric icon={Cloud} label="Cloud cover" value={c.cloud_cover} unit="%" />
            <Metric
              icon={Gauge}
              label="Mean sea level pressure"
              value={c.pressure_msl}
              unit="hPa"
            />
          </>
        ) : (
          <>
            <Metric
              icon={Droplets}
              label="Forecast rain today"
              value={d.precipitation_sum}
              unit="mm"
            />
            <Metric icon={Thermometer} label="Temperature" value={c.temperature_2m} unit="°C" />
            <Metric icon={Droplets} label="Humidity" value={c.relative_humidity_2m} unit="%" />
            <Metric icon={Wind} label="Wind" value={c.wind_speed_10m} unit="km/h" />
          </>
        )}
      </div>
      <Freshness />
      <div className="below-grid">
        <section className="card">
          <div className="card-head">
            <h2>
              {isMarine
                ? "Wave forecast"
                : aviation
                  ? "Wind & operating conditions"
                  : "Rainfall outlook"}
            </h2>
            <span className="badge neutral">MODEL DATA</span>
          </div>
          {busy ? (
            <div className="loading" />
          ) : isMarine && marine.status === "unavailable" ? (
            <Empty title="Marine data unavailable here" retry={() => setTick((t) => t + 1)}>
              {marine.message || "Select a coastal or offshore location."}
            </Empty>
          ) : (
            <Chart
              data={
                isMarine
                  ? marine.hourly
                  : weather?.hourly
                      .filter(
                        (h) =>
                          !weather?.timestamp || h.time >= weather.timestamp.slice(0, 13) + ":00",
                      )
                      .slice(0, 48) || []
              }
              field={isMarine ? "wave_height" : aviation ? "wind_speed_10m" : "precipitation"}
              unit={isMarine ? "m" : aviation ? "km/h" : "mm"}
              bar={!isMarine && !aviation}
              tall
            />
          )}
          {isMarine && (
            <small>
              {marine.source} · {marine.fetched_at}
            </small>
          )}
        </section>
        <section className="card">
          <h2>{isMarine ? "At sea" : aviation ? "Atmospheric context" : "Fieldwork guidance"}</h2>
          {isMarine ? (
            <>
              <div className="detail-list">
                <span>Wave period</span>
                <span>{number(m.wave_period, 1)} s</span>
              </div>
              <div className="detail-list">
                <span>Current direction</span>
                <span>{number(m.ocean_current_direction)}°</span>
              </div>
              <p className="muted" style={{ marginTop: 20, fontSize: 14 }}>
                Wave forecasts are model estimates. Coastal bathymetry, tides, and local currents
                can change conditions. Official navigation warnings and cyclone bulletins are not
                connected.
              </p>
            </>
          ) : aviation ? (
            <>
              <div className="detail-list">
                <span>Wind</span>
                <span>
                  {number(c.wind_speed_10m)} km/h · {number(c.wind_direction_10m)}°
                </span>
              </div>
              <div className="detail-list">
                <span>Precipitation</span>
                <span>{number(c.precipitation, 1)} mm</span>
              </div>
              <p className="muted" style={{ marginTop: 20, fontSize: 14 }}>
                This view is situational awareness only. METAR, TAF, cloud base, runway conditions,
                and certified flight-planning data are not connected. Do not use it for flight
                clearance.
              </p>
            </>
          ) : (
            <>
              <div className="detail-list">
                <span>Surface soil temperature</span>
                <span>{number(c.soil_temperature_0cm)} °C</span>
              </div>
              <div className="detail-list">
                <span>Top 1 cm soil moisture</span>
                <span>{number(c.soil_moisture_0_to_1cm, 2)} m³/m³</span>
              </div>
              <p className="muted" style={{ marginTop: 18, fontSize: 14 }}>
                <strong className="cyan">Irrigation</strong>
                <br />
                {weather?.status !== "live"
                  ? "Current data is unavailable; irrigation cannot be assessed."
                  : d.precipitation_sum >= 5
                    ? "Rain is forecast today. Check actual soil moisture before scheduling irrigation."
                    : "Check root-zone moisture, crop stage, and local water requirements before irrigation."}
              </p>
              <p className="muted" style={{ marginTop: 14, fontSize: 14 }}>
                <strong className="cyan">Spraying</strong>
                <br />
                {weather?.status !== "live"
                  ? "Weather suitability is unknown."
                  : c.wind_speed_10m > 15 || c.precipitation > 0
                    ? "Rain or wind may increase drift and wash-off. Consider postponing and follow product guidance."
                    : "Check the product label, local wind, and rain forecast before spraying."}
              </p>
            </>
          )}
        </section>
      </div>
      <div className="detail-grid">
        <section className="card">
          <h3>
            {isMarine ? "Marine screening" : aviation ? "Weather screening" : "Crop heat stress"}
          </h3>
          <p className="muted" style={{ fontSize: 14, marginTop: 12 }}>
            {isMarine
              ? m.wave_height == null
                ? "Wave-height screening unavailable."
                : m.wave_height >= 3
                  ? "Elevated wave height. Consult official marine warnings."
                  : "No 3 m wave-height threshold triggered; this is not a safe-sailing assessment."
              : aviation
                ? `${alerts.length} local threshold alerts. Consult official airport weather.`
                : c.temperature_2m == null
                  ? "Temperature unavailable."
                  : c.temperature_2m >= 35
                    ? "High temperature may stress susceptible crops. Monitor field conditions."
                    : "Temperature is below the 35 °C screening threshold; crop-specific tolerance varies."}
          </p>
        </section>
        <section className="card">
          <h3>Sun & exposure</h3>
          <div className="detail-list">
            <span>Sunrise</span>
            <span>{d.sunrise?.slice(11) || "—"}</span>
          </div>
          <div className="detail-list">
            <span>Sunset</span>
            <span>{d.sunset?.slice(11) || "—"}</span>
          </div>
          <div className="detail-list">
            <span>UV daily max</span>
            <span>{number(d.uv_index_max)}</span>
          </div>
        </section>
        <section className="card">
          <h3>Know the limits</h3>
          <p className="muted" style={{ fontSize: 14, marginTop: 12 }}>
            These views support decisions; they do not guarantee outcomes. Verify local observations
            and official guidance. Unavailable parameters stay blank.
          </p>
        </section>
      </div>
    </>
  );
}
