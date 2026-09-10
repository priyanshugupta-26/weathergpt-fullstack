import { useEffect, useState } from "react";
import {
  ChartNoAxesCombined,
  Calendar,
  TrendingUp,
  Thermometer,
  CloudRain,
  Flame,
  Droplets,
  RefreshCw,
  Info,
  ChevronRight,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { api, number } from "@/lib/api";
import { Heading, Chart } from "@/components/WeatherUI";

export default function Climate() {
  const { place } = useApp();
  const [years, setYears] = useState<10 | 20 | 30>(30);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [activeMetric, setActiveMetric] = useState<"temperature" | "precipitation">("temperature");

  const loadClimate = async () => {
    setLoading(true);
    try {
      const res = await api(
        `/api/climate/multi-decade?latitude=${place.latitude}&longitude=${place.longitude}&years=${years}`,
      );
      setData(res);
      if (res.annual_series?.length > 0) {
        setSelectedYear(res.annual_series[res.annual_series.length - 1].year);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClimate();
  }, [place, years]);

  const yearRecord = data?.annual_series?.find((y: any) => y.year === selectedYear);

  return (
    <>
      <Heading
        title="Multi-Decade Climate & Reanalysis Analytics"
        subtitle={`Long-term atmospheric baseline for ${place.name} · ECMWF ERA5 10 to 30 year reanalysis climatology.`}
      >
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
            Timespan:
          </span>
          {[10, 20, 30].map((yr) => (
            <button
              key={yr}
              className={`button ${years === yr ? "primary" : "secondary"}`}
              style={{ fontSize: 12, padding: "4px 10px" }}
              onClick={() => setYears(yr as any)}
            >
              {yr} Years
            </button>
          ))}
          <button className="button secondary" onClick={loadClimate} disabled={loading} style={{ marginLeft: 4 }}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
          </button>
        </div>
      </Heading>

      {/* Reanalysis Normals Metric Strip */}
      <div className="metric-strip" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <section className="card">
          <div className="eyebrow">CLIMATOLOGICAL MEAN TEMP</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 8 }}>
            <h1 style={{ fontSize: 30, margin: 0, color: "var(--cyan)" }}>
              {number(data?.normals?.annual_mean_temperature)}
            </h1>
            <span style={{ fontSize: 16, color: "var(--muted)" }}>°C</span>
          </div>
          <small>{years}-year normal ({data?.start_year}–{data?.end_year})</small>
        </section>

        <section className="card">
          <div className="eyebrow">ANNUAL PRECIPITATION NORMAL</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 8 }}>
            <h1 style={{ fontSize: 30, margin: 0, color: "#38bdf8" }}>
              {number(data?.normals?.annual_rainfall_mm)}
            </h1>
            <span style={{ fontSize: 16, color: "var(--muted)" }}>mm/yr</span>
          </div>
          <small>Mean cumulative annual rainfall</small>
        </section>

        <section className="card">
          <div className="eyebrow">EXTREME HEAT DAYS (&gt;40°C)</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 8 }}>
            <h1 style={{ fontSize: 30, margin: 0, color: "#f97316" }}>
              {number(data?.normals?.extreme_heat_days_per_year, 1)}
            </h1>
            <span style={{ fontSize: 16, color: "var(--muted)" }}>days/yr</span>
          </div>
          <small>Thermal stress baseline</small>
        </section>

        <section className="card">
          <div className="eyebrow">HEAVY RAINFALL DAYS (&gt;50mm)</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 8 }}>
            <h1 style={{ fontSize: 30, margin: 0, color: "#10b981" }}>
              {number(data?.normals?.heavy_rain_days_per_year, 1)}
            </h1>
            <span style={{ fontSize: 16, color: "var(--muted)" }}>days/yr</span>
          </div>
          <small>High intensity rainfall events</small>
        </section>
      </div>

      {/* Linear Trend & Statistical Confidence Card */}
      <section
        className="card"
        style={{
          margin: "16px 0",
          background: "rgba(56, 189, 248, 0.04)",
          border: "1px solid rgba(56, 189, 248, 0.25)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <TrendingUp size={24} style={{ color: "var(--cyan)" }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)" }}>
              Decadal Linear Regression Trend ({data?.trend?.data_period || `${years} Years`})
            </div>
            <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>
              Linear rate of change derived from ERA5 reanalysis grid points.
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
              Temperature Trend
            </div>
            <div style={{ fontSize: 18, fontWeight: 800, color: (data?.trend?.temperature_trend_c_per_decade || 0) >= 0 ? "#f97316" : "#38bdf8" }}>
              {(data?.trend?.temperature_trend_c_per_decade || 0) >= 0 ? "+" : ""}
              {number(data?.trend?.temperature_trend_c_per_decade, 2)} °C / decade
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
              Precipitation Trend
            </div>
            <div style={{ fontSize: 18, fontWeight: 800, color: "#38bdf8" }}>
              {(data?.trend?.rainfall_trend_mm_per_decade || 0) >= 0 ? "+" : ""}
              {number(data?.trend?.rainfall_trend_mm_per_decade, 1)} mm / decade
            </div>
          </div>
        </div>
      </section>

      {/* Anomaly Comparison & Annual Series */}
      <div className="below-grid">
        {/* Left: Climate Anomaly Inspector */}
        <section className="card">
          <div className="card-head">
            <h2>Annual Climate Anomaly Inspector</h2>
            <span className="badge neutral">ERA5 BASELINE</span>
          </div>

          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 12 }}>
            Select any year to compare against the {years}-year climatological baseline ({data?.start_year}–{data?.end_year}).
          </p>

          <div style={{ display: "flex", gap: 6, overflowX: "auto", paddingBottom: 8, marginBottom: 14 }}>
            {(data?.annual_series || []).map((y: any) => (
              <button
                key={y.year}
                className={`button ${selectedYear === y.year ? "primary" : "secondary"}`}
                style={{ fontSize: 11, padding: "3px 8px" }}
                onClick={() => setSelectedYear(y.year)}
              >
                {y.year}
              </button>
            ))}
          </div>

          {yearRecord ? (
            <div
              style={{
                padding: 16,
                borderRadius: 10,
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid var(--line)",
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0, fontSize: 18 }}>Year {yearRecord.year} Departure</h3>
                <span className="badge cyan">ANOMALY CALCULATION</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div style={{ padding: 10, borderRadius: 8, background: "rgba(255, 255, 255, 0.02)" }}>
                  <small style={{ color: "var(--muted)" }}>Temperature Departure</small>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 800,
                      marginTop: 4,
                      color: (yearRecord.temperature_anomaly || 0) >= 0 ? "#f97316" : "#38bdf8",
                    }}
                  >
                    {(yearRecord.temperature_anomaly || 0) >= 0 ? "+" : ""}
                    {number(yearRecord.temperature_anomaly, 2)} °C
                  </div>
                  <small style={{ color: "var(--muted)" }}>
                    Annual mean: {number(yearRecord.temperature_mean, 1)} °C
                  </small>
                </div>

                <div style={{ padding: 10, borderRadius: 8, background: "rgba(255, 255, 255, 0.02)" }}>
                  <small style={{ color: "var(--muted)" }}>Rainfall Departure</small>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 800,
                      marginTop: 4,
                      color: (yearRecord.rainfall_departure || 0) >= 0 ? "#10b981" : "#ef4444",
                    }}
                  >
                    {(yearRecord.rainfall_departure || 0) >= 0 ? "+" : ""}
                    {number(yearRecord.rainfall_departure, 1)} mm
                  </div>
                  <small style={{ color: "var(--muted)" }}>
                    Total rain: {number(yearRecord.precipitation_sum, 1)} mm
                  </small>
                </div>
              </div>
            </div>
          ) : null}
        </section>

        {/* Right: Decadal Annual Series Chart/List */}
        <section className="card">
          <div className="card-head">
            <h2>{years}-Year Annual Series</h2>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                className={`button ${activeMetric === "temperature" ? "primary" : "secondary"}`}
                style={{ fontSize: 11, padding: "2px 8px" }}
                onClick={() => setActiveMetric("temperature")}
              >
                Temp
              </button>
              <button
                className={`button ${activeMetric === "precipitation" ? "primary" : "secondary"}`}
                style={{ fontSize: 11, padding: "2px 8px" }}
                onClick={() => setActiveMetric("precipitation")}
              >
                Rain
              </button>
            </div>
          </div>

          <div style={{ maxHeight: 360, overflowY: "auto" }}>
            <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--line)", color: "var(--muted)" }}>
                  <th style={{ padding: "8px 6px" }}>Year</th>
                  <th style={{ padding: "8px 6px" }}>Mean Temp (°C)</th>
                  <th style={{ padding: "8px 6px" }}>Rain (mm)</th>
                  <th style={{ padding: "8px 6px" }}>Heat Days</th>
                  <th style={{ padding: "8px 6px" }}>Heavy Rain Days</th>
                </tr>
              </thead>
              <tbody>
                {(data?.annual_series || []).map((row: any) => (
                  <tr
                    key={row.year}
                    style={{
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                      background: row.year === selectedYear ? "rgba(56,189,248,0.12)" : undefined,
                      cursor: "pointer",
                    }}
                    onClick={() => setSelectedYear(row.year)}
                  >
                    <td style={{ padding: "8px 6px", fontWeight: 700, color: "var(--cyan)" }}>
                      {row.year}
                    </td>
                    <td style={{ padding: "8px 6px" }}>{number(row.temperature_mean, 1)}</td>
                    <td style={{ padding: "8px 6px" }}>{number(row.precipitation_sum, 1)}</td>
                    <td style={{ padding: "8px 6px" }}>{row.extreme_heat_days}</td>
                    <td style={{ padding: "8px 6px" }}>{row.heavy_rain_days}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Mandatory Scientific Disclaimer */}
      <div
        style={{
          margin: "24px 0 10px",
          padding: "12px 18px",
          borderRadius: 8,
          background: "rgba(255, 255, 255, 0.02)",
          border: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          gap: 12,
          fontSize: 12,
          color: "var(--muted)",
        }}
      >
        <Info size={18} style={{ color: "var(--cyan)", flexShrink: 0 }} />
        <span>
          <strong>Scientific Climatology Disclaimer:</strong> Trend describes this dataset/location ({place.name}) and period ({data?.start_year}–{data?.end_year}). Do not make climate-change causal conclusions solely from local short datasets. Reanalysis data sourced from ECMWF ERA5.
        </span>
      </div>
    </>
  );
}
