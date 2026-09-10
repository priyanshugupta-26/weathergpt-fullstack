import { useEffect, useRef, useState } from "react";
import { Sparkles, Plus, ArrowUp, Mic, Square, MapPin, MessageSquare, Volume2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useApp } from "@/lib/context";
import { api, readLocal, writeLocal, number, type Row } from "@/lib/api";
import { Heading } from "@/components/WeatherUI";
import { getSpeechLocale, isRTL, getLanguageInfo, t } from "@/lib/i18n";
type Message = { role: string; content: string; weather?: Row; mode?: string };
export default function Chat() {
  const { place, language, toast } = useApp();
  const [conversations, setConversations] = useState<Record<string, Message[]>>(() =>
      readLocal("wg.chats", {}),
    ),
    [conversation, setConversation] = useState(() => readLocal("wg.activeChat", "default")),
    [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [listening, setListening] = useState(false),
    [supported, setSupported] = useState(false);
  const recognition = useRef<any>(null),
    bottom = useRef<HTMLDivElement>(null);
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
  const send = async (message = text) => {
    if (!message.trim() || busy) return;
    const id = conversation;
    setText("");
    setConversations((c) => ({
      ...c,
      [id]: [...(c[id] || []), { role: "user", content: message }],
    }));
    setBusy(true);
    try {
      const result = await api("/api/chat", {
        method: "POST",
        body: JSON.stringify({ ...place, message, language, conversation: id }),
      });
      setConversations((c) => ({
        ...c,
        [id]: [
          ...(c[id] || []),
          {
            role: "assistant",
            content: result.message,
            weather: result.weather,
            mode: result.mode,
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
            content: `Unable to answer: ${(e as Error).message} Please try again.`,
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
    const matched = voices.find((v) => v.lang.replace("_", "-").toLowerCase().startsWith(locale.split("-")[0].toLowerCase()));
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
  return (
    <>
      <Heading
        title="Weather, in your words."
        subtitle={`Grounded meteorological assistant for India. Active: ${getLanguageInfo(language).nativeName} (${getLanguageInfo(language).name}). No AI key required.`}
      />
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
            Signed-in messages are also saved privately to your account.
          </small>
        </aside>
        <section className="card chat-main">
          <div className="card-head">
            <div className="button-row">
              <span className="assistant-icon">
                <Sparkles size={19} />
              </span>
              <h2>WeatherGPT</h2>
              <span className="badge neutral">DATA-GROUNDED</span>
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
                {language === "hi" ? "आज मौसम के बारे में क्या जानना चाहेंगे?" : "What’s on your horizon?"}
              </h1>
              <p>
                Ask about the forecast, plan around the rain, or make sense of changing conditions.
              </p>
              <div className="suggestions">
                {[
                  "Will it rain here tomorrow?",
                  "What is the wind speed near Mumbai?",
                  "Explain today’s weather in Hindi.",
                  "Should farmers irrigate crops today?",
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
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                    <small>{m.role === "user" ? "YOU" : "WEATHERGPT"}</small>
                    {m.role === "assistant" && (
                      <button
                        type="button"
                        onClick={() => speak(m.content)}
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
                        <Volume2 size={14} />
                      </button>
                    )}
                  </div>
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                  {m.weather?.status === "live" && (
                    <div className="list-item" style={{ marginTop: 12, color: "var(--cyan)" }}>
                      {number(m.weather.current.temperature_2m)} °C ·{" "}
                      {number(m.weather.current.wind_speed_10m)} km/h · {m.weather.source}
                      <small style={{ display: "block" }}>
                        {m.weather.timestamp} · {m.mode}
                      </small>
                    </div>
                  )}
                </article>
              ))}
              {busy && (
                <article className="message" role="status">
                  <Sparkles size={16} /> Checking weather data…
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
              placeholder={listening ? "Listening…" : "Ask anything about the weather…"}
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
          <small style={{ textAlign: "center", marginTop: 10 }}>
            Weather can change. Check official warnings before safety-critical decisions.
          </small>
        </section>
      </div>
    </>
  );
}
