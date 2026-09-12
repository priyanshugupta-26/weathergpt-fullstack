import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Plus,
  ArrowUp,
  Mic,
  Square,
  MapPin,
  MessageSquare,
  Volume2,
  CheckCircle2,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  CloudRain,
  Sun,
  Wind,
  ShieldAlert,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useApp } from "@/lib/context";
import { api, readLocal, writeLocal, number, type Row } from "@/lib/api";
import { Heading } from "@/components/WeatherUI";
import { getSpeechLocale, isRTL, getLanguageInfo } from "@/lib/i18n";

export interface MetricItem {
  label: string;
  value: any;
  unit: string;
  trend?: string;
}

export interface SourceItem {
  organization?: string;
  dataset?: string;
  timestamp?: string;
  type?: string;
  title?: string;
}

export interface StructuredAnswerData {
  summary: string;
  severity: "NORMAL" | "ADVISORY" | "WATCH" | "WARNING" | "SEVERE" | string;
  key_points: string[];
  timeline: string[];
  actions: string[];
  metrics: MetricItem[];
  sources: SourceItem[];
  technical_details?: string | null;
  confidence?: number | null;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  intent?: string;
  weather?: Row;
  mode?: string;
  structured?: StructuredAnswerData;
  showTechnical?: boolean;
}

export default function Chat() {
  const { place, language, toast } = useApp();
  const [conversations, setConversations] = useState<Record<string, Message[]>>(() =>
    readLocal("wg.chats", {}),
  );
  const [conversation, setConversation] = useState(() =>
    readLocal("wg.activeChat", "default"),
  );
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [chatMode, setChatMode] = useState<"standard" | "simple" | "technical">("standard");
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);

  const recognition = useRef<any>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const messages = conversations[conversation] || [];
  const initial = useRef(false);

  useEffect(() => {
    setSupported(
      Boolean((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition),
    );
    return () => recognition.current?.abort();
  }, []);

  useEffect(() => {
    writeLocal("wg.chats", conversations);
    writeLocal("wg.activeChat", conversation);
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [conversations, conversation]);

  useEffect(() => {
    const q = new URLSearchParams(location.search).get("q");
    if (q && !initial.current) {
      setText(q);
      initial.current = true;
    }
  }, []);

  const toggleTechnical = (index: number) => {
    setConversations((prev) => {
      const current = prev[conversation] || [];
      const updated = current.map((m, i) =>
        i === index ? { ...m, showTechnical: !m.showTechnical } : m,
      );
      return { ...prev, [conversation]: updated };
    });
  };

  const send = async (message = text, modeOverride?: string) => {
    const query = message.trim();
    if (!query || busy) return;
    const id = conversation;
    setText("");
    setConversations((c) => ({
      ...c,
      [id]: [...(c[id] || []), { role: "user", content: query }],
    }));
    setBusy(true);

    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          message: query,
          language,
          conversation: id,
          mode: modeOverride || chatMode,
          latitude: place?.latitude,
          longitude: place?.longitude,
          name: place?.name,
        }),
      });

      const isWeather = result.type === "weather" || (result.intent && result.intent !== "GENERAL" && Boolean(result.structured));
      const structured: StructuredAnswerData | undefined = isWeather ? result.structured || undefined : undefined;
      const intent: string = isWeather ? (result.intent || "WEATHER") : "GENERAL";
      const content: string = result.content || result.message || (isWeather ? structured?.summary : "") || "No response generated.";

      setConversations((c) => ({
        ...c,
        [id]: [
          ...(c[id] || []),
          {
            role: "assistant",
            content,
            intent,
            weather: isWeather ? result.weather : undefined,
            mode: result.mode,
            structured,
            showTechnical: false,
          },
        ],
      }));
    } catch (e) {
      setConversations((c) => ({
        ...c,
        [id]: [
          ...(c[id] || []),
          {
            role: "assistant",
            content: `Unable to answer: ${(e as Error).message}. Please try again.`,
          },
        ],
      }));
    } finally {
      setBusy(false);
    }
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
    const voices = window.speechSynthesis.getVoices();
    const matched = voices.find((v) =>
      v.lang.replace("_", "-").toLowerCase().startsWith(locale.split("-")[0].toLowerCase()),
    );
    if (matched) utterance.voice = matched;
    window.speechSynthesis.speak(utterance);
  };

  const voice = () => {
    if (listening) {
      recognition.current?.stop();
      return;
    }
    const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Speech) {
      toast("Voice recognition is not supported on this browser.");
      return;
    }
    const r = new Speech();
    recognition.current = r;
    const locale = getSpeechLocale(language);
    r.lang = locale;
    r.interimResults = true;
    r.onstart = () => setListening(true);
    r.onend = () => setListening(false);
    r.onresult = (event: any) =>
      setText(
        Array.from(event.results)
          .map((res: any) => res[0].transcript)
          .join(" "),
      );
    r.onerror = (event: any) => {
      setListening(false);
      if (event.error === "language-not-supported") {
        toast(`Voice recognition is not available for ${getLanguageInfo(language).name} on this browser.`);
      } else if (event.error === "not-allowed") {
        toast("Microphone permission denied. You can still type your question.");
      } else {
        toast(`Voice input: ${event.error}. You can type your question.`);
      }
    };
    try {
      r.start();
    } catch {
      toast("Voice recognition is not available for this language on this browser.");
    }
  };

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
        title="Weather, in your words."
        subtitle={`Grounded meteorological assistant for India. Active: ${getLanguageInfo(language).nativeName} (${getLanguageInfo(language).name}). No AI hallucinated weather.`}
      >
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase" }}>
            Mode:
          </span>
          {[
            { id: "simple", label: "🌾 Simple" },
            { id: "standard", label: "🌤 Standard" },
            { id: "technical", label: "📊 Technical" },
          ].map((m) => (
            <button
              key={m.id}
              className={`button ${chatMode === m.id ? "primary" : "secondary"}`}
              style={{ padding: "4px 10px", fontSize: 12 }}
              onClick={() => setChatMode(m.id as any)}
            >
              {m.label}
            </button>
          ))}
        </div>
      </Heading>

      <div className="chat-layout" dir={isRTL(language) ? "rtl" : "ltr"}>
        <aside className="card chat-history">
          <button
            className="button"
            disabled={busy}
            onClick={() => {
              const id = crypto.randomUUID();
              setConversation(id);
              setConversations((c) => ({ ...c, [id]: [] }));
            }}
          >
            <Plus size={15} />
            New conversation
          </button>
          <div className="eyebrow" style={{ marginTop: 25 }}>
            ON THIS DEVICE
          </div>
          {Object.entries(conversations)
            .slice(-12)
            .reverse()
            .map(([id, msgs]) => (
              <button
                className={`prompt ${id === conversation ? "cyan" : ""}`}
                key={id}
                disabled={busy}
                onClick={() => setConversation(id)}
              >
                <MessageSquare size={14} />
                <span
                  style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                >
                  {msgs[0]?.content || "New conversation"}
                </span>
              </button>
            ))}
          <small style={{ display: "block", marginTop: 20 }}>
            Multi-turn conversation context is retained across queries.
          </small>
        </aside>

        <section className="card chat-main">
          <div className="card-head">
            <div className="button-row">
              <span className="assistant-icon">
                <Sparkles size={19} />
              </span>
              <h2>WeatherGPT</h2>
              <span className="badge neutral">TOOL GROUNDED</span>
              <span className="badge cyan" style={{ textTransform: "uppercase" }}>
                {chatMode}
              </span>
            </div>
            <span
              className="muted"
              style={{ fontSize: 12, display: "flex", gap: 6, alignItems: "center" }}
            >
              <MapPin size={13} />
              {place.name}
            </span>
          </div>

          {!messages.length ? (
            <div className="chat-welcome">
              <span className="assistant-icon">
                <Sparkles size={30} />
              </span>
              <h1>
                {language === "hi"
                  ? "आज मौसम के बारे में क्या जानना चाहेंगे?"
                  : "What’s on your horizon?"}
              </h1>
              <p>
                Ask free-form questions about rain, farm spraying, sea conditions, travel, or disaster warnings.
              </p>
              <div className="suggestions">
                {[
                  "Should I spray pesticide tomorrow morning?",
                  "Rain aa rahi hai to fertilizer kab dalu?",
                  "Is the sea safe for a small fishing boat near Visakhapatnam tomorrow?",
                  "Can I travel from Patna to Ranchi tomorrow morning?",
                  "Compare today's wind with yesterday.",
                  "Which part of the day has lowest rain risk?",
                ].map((q) => (
                  <button key={q} onClick={() => send(q)}>
                    {q} ↗
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages" aria-live="polite">
              {messages.map((m, i) => (
                <article key={i} className={`message ${m.role}`}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      marginBottom: 8,
                    }}
                  >
                    <small style={{ fontWeight: 700, letterSpacing: "0.06em", color: "var(--muted)" }}>
                      {m.role === "user"
                        ? "YOU"
                        : m.intent === "GENERAL" || !m.structured
                        ? "WEATHERGPT"
                        : "WEATHERGPT INTELLIGENCE"}
                    </small>
                    {m.role === "assistant" && (
                      <button
                        type="button"
                        onClick={() => speak(m.structured?.summary || m.content)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--muted)",
                          cursor: "pointer",
                          padding: "2px 4px",
                          display: "inline-flex",
                          alignItems: "center",
                        }}
                        aria-label="Read answer aloud"
                        title="Read aloud"
                      >
                        <Volume2 size={15} />
                      </button>
                    )}
                  </div>

                  {m.role === "assistant" && m.structured && m.intent !== "GENERAL" ? (
                    <div className="structured-answer-container">
                      {/* 1. Quick Answer Card */}
                      <div className={`quick-answer-card ${getSeverityClass(m.structured.severity)}`}>
                        <div className="quick-answer-header">
                          <span className="quick-answer-title">
                            {m.structured.severity === "SEVERE" || m.structured.severity === "WARNING" ? (
                              <AlertTriangle size={16} style={{ color: "#ef4444" }} />
                            ) : (
                              <Sun size={16} style={{ color: "#10b981" }} />
                            )}
                            QUICK ANSWER
                          </span>
                          <span className={`badge ${getSeverityClass(m.structured.severity)}`}>
                            {m.structured.severity}
                          </span>
                        </div>
                        <p className="quick-answer-summary">{m.structured.summary}</p>

                        {/* Metric chips */}
                        {m.structured.metrics && m.structured.metrics.length > 0 && (
                          <div className="metric-chips-row">
                            {m.structured.metrics.map((mc, idx) => (
                              <span key={idx} className="metric-chip">
                                <span>{mc.label}:</span>
                                <span className="chip-val">
                                  {mc.value} {mc.unit}
                                </span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* 2. Key Points */}
                      {m.structured.key_points && m.structured.key_points.length > 0 && (
                        <div className="structured-section">
                          <span className="section-label">KEY POINTS</span>
                          <ul className="key-points-list">
                            {m.structured.key_points.map((pt, idx) => (
                              <li key={idx}>{pt}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* 3. What You Should Do */}
                      {m.structured.actions && m.structured.actions.length > 0 && (
                        <div className="structured-section">
                          <span className="section-label">WHAT YOU SHOULD DO</span>
                          <div className="actions-checklist">
                            {m.structured.actions.map((act, idx) => {
                              const isWarning =
                                act.toLowerCase().includes("avoid") ||
                                act.toLowerCase().includes("warn") ||
                                act.toLowerCase().includes("alert") ||
                                act.toLowerCase().includes("danger") ||
                                act.toLowerCase().includes("caution") ||
                                act.startsWith("⚠");
                              return (
                                <div
                                  key={idx}
                                  className={`action-item ${isWarning ? "warning-action" : ""}`}
                                >
                                  {isWarning ? (
                                    <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2, color: "#f59e0b" }} />
                                  ) : (
                                    <CheckCircle2 size={15} style={{ flexShrink: 0, marginTop: 2, color: "#10b981" }} />
                                  )}
                                  <span>{act.replace(/^[✓⚠•\s]+/, "")}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* 4. Timeline Strip */}
                      {m.structured.timeline && m.structured.timeline.length > 0 && (
                        <div className="structured-section">
                          <span className="section-label">TIMELINE</span>
                          <div className="timeline-strip">
                            {m.structured.timeline.map((slot, idx) => {
                              const parts = slot.split(":");
                              const timeStr = parts.length > 1 ? parts[0] : `Period ${idx + 1}`;
                              const desc = parts.length > 1 ? parts.slice(1).join(":") : slot;
                              return (
                                <div key={idx} className="timeline-card">
                                  <div className="timeline-time">{timeStr}</div>
                                  <div className="timeline-cond">{desc.trim()}</div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* 5. Sources Bar */}
                      {m.structured.sources && m.structured.sources.length > 0 && (
                        <div className="sources-bar">
                          <span style={{ fontWeight: 700, color: "var(--muted)" }}>SOURCE:</span>
                          {m.structured.sources.map((s, idx) => (
                            <span key={idx} className="source-chip">
                              <Info size={11} />
                              {s.organization || s.type || "WeatherGPT Fact"}{" "}
                              {s.dataset ? `(${s.dataset})` : ""}{" "}
                              {s.timestamp ? `· ${s.timestamp.slice(0, 10)}` : ""}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* 6. Explain More Button */}
                      {(m.structured.technical_details || chatMode === "technical") && (
                        <div style={{ marginTop: 6 }}>
                          <button
                            type="button"
                            className="explain-more-btn"
                            onClick={() => toggleTechnical(i)}
                          >
                            {m.showTechnical ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            {m.showTechnical ? "Hide Technical Details" : "Explain More (Technical)"}
                          </button>

                          {m.showTechnical && (
                            <div className="technical-drawer" style={{ marginTop: 8 }}>
                              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--cyan)", marginBottom: 6 }}>
                                METEOROLOGICAL & MODEL RATIONALE
                              </div>
                              <ReactMarkdown>
                                {m.structured.technical_details || "No deeper technical metrics available."}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="general-chat-text" style={{ lineHeight: 1.65, fontSize: "0.95rem" }}>
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  )}

                  {m.weather?.status === "live" && m.intent !== "GENERAL" && m.structured && (
                    <div className="list-item" style={{ marginTop: 12, color: "var(--cyan)", fontSize: 12 }}>
                      {number(m.weather.current?.temperature_2m)} °C ·{" "}
                      {number(m.weather.current?.wind_speed_10m)} km/h · {m.weather.source}
                      <small style={{ display: "block", color: "var(--muted)" }}>
                        {m.weather.timestamp} · {m.mode}
                      </small>
                    </div>
                  )}
                </article>
              ))}

              {busy && (
                <article className="message" role="status">
                  <Sparkles size={16} className="spin" /> Thinking…
                </article>
              )}
              <div ref={bottom} />
            </div>
          )}

          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <textarea
              aria-label="Message WeatherGPT"
              placeholder={listening ? "Listening…" : "Ask anything about weather, farming, marine, travel..."}
              value={text}
              rows={2}
              maxLength={2000}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            {supported && (
              <button
                type="button"
                className="icon-btn"
                onClick={voice}
                aria-label={listening ? "Stop listening" : "Start voice input"}
              >
                {listening ? <Square size={15} /> : <Mic size={17} />}
              </button>
            )}
            <button
              className="button primary"
              disabled={busy || !text.trim()}
              aria-label="Send message"
            >
              <ArrowUp size={18} />
            </button>
          </form>
          <small style={{ textAlign: "center", marginTop: 10, color: "var(--muted)", fontSize: 11 }}>
            Weather can change rapidly. Check official IMD/NDMA CAP alerts before safety-critical decisions.
          </small>
        </section>
      </div>
    </>
  );
}
