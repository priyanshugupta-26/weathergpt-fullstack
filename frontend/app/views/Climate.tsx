import { useEffect, useState } from "react";
import { ChartNoAxesCombined, Download, RefreshCw } from "lucide-react";
import { useApp } from "@/lib/context";
import { api, locationQuery, number, type Row } from "@/lib/api";
import { Heading, Chart, Choice, Empty } from "@/components/WeatherUI";
export default function Climate() {
  const { place } = useApp();
  const ago = (days: number) => new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
  const [start, setStart] = useState(ago(40)),
    [end, setEnd] = useState(ago(10)),
    [data, setData] = useState<Row>({ daily: [] }),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [field, setField] = useState("temperature_2m_mean");
  const load = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await api(`/api/weather/history?${locationQuery(place)}&start=${start}&end=${end}`);
      setData(d);
      if (d.status === "unavailable") setError(d.message);
    } catch (e) {
      setError((e as Error).message);
      setData({ daily: [] });
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    setData({ daily: [] });
  }, [place]);
  const fields = [
    { value: "temperature_2m_mean", label: "Temperature · °C" },
    { value: "precipitation_sum", label: "Rainfall · mm" },
    { value: "relative_humidity_2m_mean", label: "Humidity · %" },
    { value: "wind_speed_10m_mean", label: "Wind · km/h" },
  ];
  const unit = field.startsWith("temperature")
    ? "°C"
    : field.startsWith("precipitation")
      ? "mm"
      : field.startsWith("wind")
        ? "km/h"
        : "%";
  const valid = data.daily.filter((d: Row) => typeof d[field] === "number");
  const average = valid.length
    ? valid.reduce((s: number, d: Row) => s + d[field], 0) / valid.length
    : null;
  const groups: Record<string, Row[]> = {};
  for (const d of data.daily) {
    const month = d.time.slice(0, 7);
    (groups[month] ??= []).push(d);
  }
  return (
    <>
      <Heading
        title="Look beyond today."
        subtitle={`Historical patterns for ${place.name}, using actual archive data.`}
      />
      <section className="card">
        <form
          className="date-form"
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
        >
          <label className="form-field">
            From
            <input
              aria-label="Start date"
              type="date"
              min="1940-01-01"
              max={ago(5)}
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </label>
          <label className="form-field">
            To
            <input
              aria-label="End date"
              type="date"
              min={start}
              max={ago(5)}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              required
            />
          </label>
          <button className="button primary" disabled={busy}>
            <RefreshCw size={15} />
            {busy ? "Loading archive…" : "Load historical data"}
          </button>
          <Choice label="Climate parameter" value={field} onChange={setField} items={fields} />
        </form>
        <small style={{ display: "block", marginTop: 14 }}>
          Up to two years per request. Archive availability ends five days ago.
        </small>
      </section>
      {error && <div className="error-note">{error}</div>}
      {data.daily.length ? (
        <>
          <div className="detail-grid">
            <section className="card">
              <small>Period mean</small>
              <h1>
                {number(average, 1)} <small>{unit}</small>
              </h1>
            </section>
            <section className="card">
              <small>Days with data</small>
              <h1>{valid.length}</h1>
            </section>
            <section className="card">
              <small>Days with ≥20 mm precipitation</small>
              <h1>{data.daily.filter((d: Row) => d.precipitation_sum >= 20).length}</h1>
              <small>Descriptive threshold, not disaster events</small>
            </section>
          </div>
          <section className="card" style={{ marginTop: 20 }}>
            <div className="card-head">
              <h2>{fields.find((f) => f.value === field)?.label}</h2>
              <span className="badge neutral">HISTORICAL</span>
            </div>
            <Chart
              data={data.daily}
              field={field}
              unit={unit}
              bar={field === "precipitation_sum"}
              tall
            />
            <small>
              {data.source} · Retrieved {data.fetched_at}
            </small>
          </section>
          <section className="card" style={{ marginTop: 20 }}>
            <h2>Monthly summary</h2>
            <div className="wide-table">
              <table>
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Mean temperature</th>
                    <th>Total rainfall</th>
                    <th>Mean humidity</th>
                    <th>Mean wind</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(groups).map(([month, days]) => {
                    const mean = (key: string) => {
                      const v = days.filter((d) => typeof d[key] === "number");
                      return v.length ? v.reduce((s, d) => s + d[key], 0) / v.length : null;
                    };
                    return (
                      <tr key={month}>
                        <td>{month}</td>
                        <td>{number(mean("temperature_2m_mean"), 1)} °C</td>
                        <td>
                          {number(
                            days.reduce((s, d) => s + (d.precipitation_sum || 0), 0),
                            1,
                          )}{" "}
                          mm
                        </td>
                        <td>{number(mean("relative_humidity_2m_mean"), 1)}%</td>
                        <td>{number(mean("wind_speed_10m_mean"), 1)} km/h</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <small>
              Partial months summarize only the selected days. Compare years by selecting a range
              spanning both years.
            </small>
          </section>
        </>
      ) : (
        <div style={{ marginTop: 20 }}>
          <Empty title="Choose a period to explore">
            <ChartNoAxesCombined size={36} style={{ margin: "15px auto" }} />
            Load an archive range to see trends, monthly averages, and rainfall-threshold counts.
          </Empty>
        </div>
      )}
    </>
  );
}
