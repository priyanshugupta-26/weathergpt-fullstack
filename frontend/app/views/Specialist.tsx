import { useEffect, useState, useRef } from "react";
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
  Sparkles,
  ArrowUp,
  Volume2,
  CheckCircle2,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  HelpCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useApp } from "@/lib/context";
import { api, locationQuery, number, type Row } from "@/lib/api";
import { Heading, Metric, Chart, Freshness, Empty } from "@/components/WeatherUI";
import { getSpeechLocale } from "@/lib/i18n";
import type { StructuredAnswerData } from "./Chat";

interface SectorMessage {
  role: "user" | "assistant";
  content: string;
  structured?: StructuredAnswerData;
  showTechnical?: boolean;
}

export default function Specialist() {
  const { route, place, weather, setPlace, alerts, language, toast } = useApp();
  const [marine, setMarine] = useState<Row>({ hourly: [] });
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  // Sector chat state
  const isMarine = route === "/marine";
  const aviation = route === "/aviation";
  const sector = isMarine ? "marine" : aviation ? "aviation" : "agriculture";

  const [chatText, setChatText] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<SectorMessage[]>([]);
  const chatBottomRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    // Reset or seed fresh sector greeting when sector changes
    setChatMessages([]);
  }, [sector]);

  const sendSectorQuery = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || chatBusy) return;

    setChatText("");
    setChatMessages((prev) => [...prev, { role: "user", content: q }]);
    setChatBusy(true);

    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          ...place,
          message: q,
          language,
          sector,
          conversation: `sector_${sector}_${place.name}`,
        }),
      });

      const structured: StructuredAnswerData | undefined = result.structured;
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.message || structured?.summary || "Advice generated.",
          structured,
          showTechnical: false,
        },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Unable to retrieve advice: ${(err as Error).message}`,
        },
      ]);
    } finally {
      setChatBusy(false);
      setTimeout(() => {
        chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  };

  const toggleTechnical = (idx: number) => {
    setChatMessages((prev) =>
      prev.map((msg, i) => (i === idx ? { ...msg, showTechnical: !msg.showTechnical } : msg)),
    );
  };

  const speak = (content: string) => {
    if (!("speechSynthesis" in window)) {
      toast("Text-to-speech is not supported on this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const clean = content.replace(/[*_#|`-]/g, "").trim();
    const utterance = new SpeechSynthesisUtterance(clean);
    const locale = getSpeechLocale(language);
    utterance.lang = locale;
    window.speechSynthesis.speak(utterance);
  };

  const c = weather?.current || {};
  const d = weather?.daily[0] || {};
  const m =
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
        { name: "Visakhapatnam coast", latitude: 17.6868, longitude: 83.2185 },
      ]
    : aviation
      ? [
          { name: "DEL · Delhi airport", latitude: 28.5562, longitude: 77.1 },
          { name: "BOM · Mumbai airport", latitude: 19.0896, longitude: 72.8656 },
          { name: "PAT · Patna airport", latitude: 25.5913, longitude: 85.087 },
        ]
      : [];

  const sectorPrompts = isMarine
    ? [
        "Is the sea safe for a small fishing boat near Visakhapatnam tomorrow?",
        "Kal machhli pakadne jana safe hai kya?",
        "What wave conditions are expected on this coast?",
        "Compare wave height today vs tomorrow",
      ]
    : aviation
      ? [
          "Can I travel from Patna to Ranchi tomorrow morning?",
          "What is the cloud base and visibility at Patna airport?",
          "Are thunderstorm gusts expected along flight paths?",
          "What will happen if pressure keeps falling?",
        ]
      : [
          "Should I spray pesticide tomorrow morning?",
          "Will strong winds affect spraying near my farm?",
          "I am growing rice, should I irrigate tomorrow?",
          "Rain aa rahi hai to fertilizer kab dalu?",
        ];

  const getSeverityClass = (sev = "NORMAL") => {
    const s = sev.toUpperCase();
    if (s === "SEVERE" || s === "EMERGENCY" || s === "RED") return "severe";
    if (s === "WARNING" || s === "ORANGE") return "warning";
    if (s === "ADVISORY" || s === "WATCH" || s === "YELLOW") return "advisory";
    return "normal";
  };

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
            <span className="badge neutral">PHYSICAL MODEL DATA</span>
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

        {/* Dynamic Sector WeatherGPT Orchestrator Chat */}
        <section className="card" style={{ display: "flex", flexDirection: "column" }}>
          <div className="card-head">
            <div className="button-row">
              <span className="assistant-icon">
                {isMarine ? <Waves size={18} /> : aviation ? <Plane size={18} /> : <Leaf size={18} />}
              </span>
              <h2>
                WeatherGPT {isMarine ? "Marine" : aviation ? "Aviation" : "Agri"} Intelligence
              </h2>
            </div>
            <span className="badge cyan">RAG + GROUNDED</span>
          </div>

          <p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 12px" }}>
            Ask free-form questions. WeatherGPT synthesizes live conditions with official{" "}
            {isMarine ? "INCOIS / IMD marine advisories" : aviation ? "NWP / synoptic charts" : "IMD Agromet bulletins"}.
          </p>

          {/* Suggested question chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 14 }}>
            {sectorPrompts.map((p, i) => (
              <button
                key={i}
                type="button"
                className="prompt"
                style={{ fontSize: 12, padding: "5px 10px", textAlign: "left" }}
                disabled={chatBusy}
                onClick={() => sendSectorQuery(p)}
              >
                {p} ↗
              </button>
            ))}
          </div>

          {/* Message history */}
          <div
            style={{
              flex: 1,
              maxHeight: 420,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 12,
              paddingRight: 4,
              marginBottom: 12,
            }}
          >
            {chatMessages.length === 0 && (
              <div
                style={{
                  padding: 20,
                  textAlign: "center",
                  borderRadius: 8,
                  border: "1px dashed var(--line)",
                  color: "var(--muted)",
                  fontSize: 13,
                }}
              >
                Click any suggestion above or type your question below.
              </div>
            )}

            {chatMessages.map((msg, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: msg.role === "user" ? "rgba(56, 189, 248, 0.12)" : "rgba(255, 255, 255, 0.03)",
                  border: `1px solid ${msg.role === "user" ? "rgba(56, 189, 248, 0.3)" : "var(--line)"}`,
                  alignSelf: msg.role === "user" ? "flex-end" : "stretch",
                  maxWidth: msg.role === "user" ? "85%" : "100%",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: msg.role === "user" ? "var(--cyan)" : "var(--muted)",
                      letterSpacing: "0.05em",
                    }}
                  >
                    {msg.role === "user" ? "YOU" : "WEATHERGPT SECTOR AI"}
                  </span>
                  {msg.role === "assistant" && (
                    <button
                      type="button"
                      onClick={() => speak(msg.structured?.summary || msg.content)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "var(--muted)",
                        cursor: "pointer",
                        padding: 2,
                      }}
                      title="Read aloud"
                    >
                      <Volume2 size={13} />
                    </button>
                  )}
                </div>

                {msg.role === "assistant" && msg.structured ? (
                  <div className="structured-answer-container" style={{ gap: 10 }}>
                    {/* Quick Answer */}
                    <div className={`quick-answer-card ${getSeverityClass(msg.structured.severity)}`}>
                      <div className="quick-answer-header">
                        <span className="quick-answer-title">
                          <Sparkles size={14} /> QUICK ADVICE
                        </span>
                        <span className={`badge ${getSeverityClass(msg.structured.severity)}`}>
                          {msg.structured.severity}
                        </span>
                      </div>
                      <p className="quick-answer-summary" style={{ fontSize: 14 }}>
                        {msg.structured.summary}
                      </p>

                      {msg.structured.metrics && msg.structured.metrics.length > 0 && (
                        <div className="metric-chips-row" style={{ marginTop: 6 }}>
                          {msg.structured.metrics.map((mc, idx) => (
                            <span key={idx} className="metric-chip" style={{ fontSize: 11, padding: "3px 8px" }}>
                              <span>{mc.label}:</span>
                              <span className="chip-val">{mc.value} {mc.unit}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    {msg.structured.actions && msg.structured.actions.length > 0 && (
                      <div className="structured-section">
                        <span className="section-label">RECOMMENDED ACTIONS</span>
                        <div className="actions-checklist">
                          {msg.structured.actions.map((act, idx) => (
                            <div key={idx} className="action-item" style={{ fontSize: 12, padding: "6px 10px" }}>
                              <CheckCircle2 size={14} style={{ color: "#10b981", flexShrink: 0 }} />
                              <span>{act.replace(/^[✓•\s]+/, "")}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Sources */}
                    {msg.structured.sources && msg.structured.sources.length > 0 && (
                      <div className="sources-bar" style={{ fontSize: 10 }}>
                        <span>SOURCE:</span>
                        {msg.structured.sources.map((s, idx) => (
                          <span key={idx} className="source-chip" style={{ fontSize: 10 }}>
                            <Info size={10} />
                            {s.organization || s.title || s.type} {s.dataset ? `(${s.dataset})` : ""}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Technical Drawer */}
                    {msg.structured.technical_details && (
                      <div>
                        <button
                          type="button"
                          className="explain-more-btn"
                          style={{ fontSize: 11, padding: "4px 8px" }}
                          onClick={() => toggleTechnical(i)}
                        >
                          {msg.showTechnical ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                          {msg.showTechnical ? "Hide Model Details" : "Explain More"}
                        </button>
                        {msg.showTechnical && (
                          <div className="technical-drawer" style={{ marginTop: 6, fontSize: 12 }}>
                            <ReactMarkdown>{msg.structured.technical_details}</ReactMarkdown>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                )}
              </div>
            ))}

            {chatBusy && (
              <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--cyan)", fontSize: 12 }}>
                <Sparkles size={14} className="spin" />
                Querying {sector} RAG knowledge & weather tools…
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Chat input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendSectorQuery(chatText);
            }}
            style={{ display: "flex", gap: 8 }}
          >
            <input
              type="text"
              className="input"
              style={{ flex: 1, padding: "8px 12px", fontSize: 13 }}
              placeholder={`Ask any ${sector} question in natural language…`}
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              disabled={chatBusy}
            />
            <button
              type="submit"
              className="button primary"
              disabled={chatBusy || !chatText.trim()}
              style={{ padding: "0 14px" }}
            >
              <ArrowUp size={16} />
            </button>
          </form>
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
                  : "Wave height is within ordinary thresholds; check INCOIS small craft advisories."
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
            These views support decisions; they do not replace certified human meteorologists or
            official warnings. Verify local conditions before safety-critical operations.
          </p>
        </section>
      </div>
    </>
  );
}
