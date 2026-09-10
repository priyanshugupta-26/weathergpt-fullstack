import { useEffect, useState, useRef } from "react";
import {
  Mic,
  Square,
  Volume2,
  AlertTriangle,
  Sparkles,
  CloudSun,
  ShieldCheck,
  Globe,
  Radio,
  RefreshCw,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { api, number } from "@/lib/api";
import { getLanguageInfo, getSpeechLocale } from "@/lib/i18n";
import type { StructuredAnswerData } from "./Chat";

export default function RuralVoice() {
  const { place, weather, alerts, language, setLanguage, toast } = useApp();
  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [responseSummary, setResponseSummary] = useState("");
  const [responseActions, setResponseActions] = useState<string[]>([]);
  const [voiceProvider, setVoiceProvider] = useState("BROWSER VOICE (FALLBACK)");
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    api("/api/bhashini/status")
      .then((res: any) => {
        setVoiceProvider(res.provider || "BROWSER VOICE (FALLBACK)");
      })
      .catch(() => setVoiceProvider("BROWSER VOICE (FALLBACK)"));
  }, []);

  const speakText = (text: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*_#|`-]/g, "").trim());
    utterance.lang = getSpeechLocale(language);
    utterance.rate = 0.9; // Slightly slower for clarity
    window.speechSynthesis.speak(utterance);
  };

  const askWeatherGPT = async (queryText: string) => {
    const q = queryText.trim();
    if (!q || busy) return;

    setBusy(true);
    try {
      const res = await api<any>("/api/chat", {
        method: "POST",
        body: JSON.stringify({
          ...place,
          message: q,
          language,
          mode: "simple",
          conversation: `rural_voice_${place.name}`,
        }),
      });

      const structured: StructuredAnswerData | undefined = res.structured;
      const summary = structured?.summary || res.message || "Advice generated.";
      const actions = structured?.actions || [];

      setResponseSummary(summary);
      setResponseActions(actions);
      speakText(summary);
    } catch (e) {
      toast(`Could not answer: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const toggleListening = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }

    const Speech = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Speech) {
      toast("Voice input is not supported on this device. You can type below.");
      return;
    }

    const r = new Speech();
    recognitionRef.current = r;
    r.lang = getSpeechLocale(language);
    r.interimResults = false;

    r.onstart = () => {
      setListening(true);
      setTranscript("");
    };

    r.onend = () => {
      setListening(false);
    };

    r.onresult = (event: any) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
      askWeatherGPT(text);
    };

    r.onerror = (e: any) => {
      setListening(false);
      toast(`Voice recognition: ${e.error}`);
    };

    try {
      r.start();
    } catch (e) {
      toast("Could not start microphone.");
    }
  };

  const activeSevereAlert = alerts.find((a) =>
    ["SEVERE", "WARNING", "EXTREME", "RED", "ORANGE"].includes(a.severity?.toUpperCase()),
  );

  return (
    <div
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "20px 16px 80px",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      {/* Header with Provider Info */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1 style={{ fontSize: 26, margin: 0, fontWeight: 800 }}>
            Rural & Voice Weather
          </h1>
          <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 2 }}>
            Simple high-contrast interface · Active Language: {getLanguageInfo(language).nativeName}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Radio size={14} style={{ color: voiceProvider.includes("BHASHINI") ? "#10b981" : "#f59e0b" }} />
          <span className="badge neutral" style={{ fontSize: 11, textTransform: "uppercase" }}>
            {voiceProvider}
          </span>
        </div>
      </div>

      {/* 1. Emergency Warning First */}
      {activeSevereAlert ? (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: 12,
            background: "rgba(239, 68, 68, 0.18)",
            border: "2px solid #ef4444",
            color: "#fee2e2",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <AlertTriangle size={24} style={{ color: "#ef4444" }} />
            <strong style={{ fontSize: 17, textTransform: "uppercase" }}>
              ACTIVE SEVERE WARNING: {activeSevereAlert.description || activeSevereAlert.event}
            </strong>
          </div>
          <p style={{ fontSize: 14, margin: "4px 0", lineHeight: 1.5 }}>
            {activeSevereAlert.recommendation || activeSevereAlert.instruction || "Stay indoors and follow safety instructions."}
          </p>
          <button
            className="button secondary"
            style={{ marginTop: 8, fontSize: 12, padding: "4px 10px" }}
            onClick={() => speakText(`Warning: ${activeSevereAlert.description || activeSevereAlert.event}`)}
          >
            <Volume2 size={14} /> Listen to Warning
          </button>
        </div>
      ) : (
        <div
          style={{
            padding: "12px 18px",
            borderRadius: 10,
            background: "rgba(16, 185, 129, 0.08)",
            border: "1px solid rgba(16, 185, 129, 0.25)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "#d1fae5",
          }}
        >
          <ShieldCheck size={20} style={{ color: "#10b981" }} />
          <span style={{ fontSize: 14, fontWeight: 600 }}>
            No extreme emergency alerts for {place.name} today. Conditions are normal.
          </span>
        </div>
      )}

      {/* 2. Today's Basic Conditions */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
          padding: 16,
          borderRadius: 12,
          background: "rgba(255, 255, 255, 0.03)",
          border: "1px solid var(--line)",
          textAlign: "center",
        }}
      >
        <div>
          <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Temperature
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 4, color: "var(--cyan)" }}>
            {number(weather?.current?.temperature_2m)} °C
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Rain Expected
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 4, color: "#38bdf8" }}>
            {number(weather?.daily?.[0]?.precipitation_sum, 1)} mm
          </div>
        </div>

        <div>
          <div style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", fontWeight: 700 }}>
            Wind Speed
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 4 }}>
            {number(weather?.current?.wind_speed_10m)} km/h
          </div>
        </div>
      </div>

      {/* 3. Massive Voice Ask Button */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "30px 20px",
          borderRadius: 16,
          background: listening
            ? "radial-gradient(circle, rgba(239, 68, 68, 0.25) 0%, rgba(20, 20, 20, 0.9) 70%)"
            : "radial-gradient(circle, rgba(56, 189, 248, 0.15) 0%, rgba(13, 20, 30, 0.8) 70%)",
          border: `2px solid ${listening ? "#ef4444" : "var(--cyan)"}`,
          boxShadow: listening ? "0 0 35px rgba(239, 68, 68, 0.4)" : "0 0 25px rgba(56, 189, 248, 0.2)",
          transition: "all 0.3s",
        }}
      >
        <button
          type="button"
          onClick={toggleListening}
          style={{
            width: 110,
            height: 110,
            borderRadius: "50%",
            background: listening ? "#ef4444" : "var(--cyan)",
            color: "#080c14",
            border: "none",
            cursor: "pointer",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 6,
            boxShadow: "0 6px 20px rgba(0, 0, 0, 0.4)",
          }}
          aria-label={listening ? "Stop listening" : "Tap to speak question"}
        >
          {listening ? <Square size={36} /> : <Mic size={42} />}
        </button>

        <div style={{ marginTop: 16, textAlign: "center" }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text)" }}>
            {listening ? "LISTENING... SPEAK NOW" : "TAP MIC & ASK IN YOUR LANGUAGE"}
          </div>
          <div style={{ fontSize: 13, color: "var(--muted)", marginTop: 4 }}>
            Ask: "कल बारिश होगी क्या?", "फसल में खाद कब डालूं?", "मौसम कैसा रहेगा?"
          </div>
        </div>

        {transcript && (
          <div
            style={{
              marginTop: 16,
              padding: "8px 16px",
              borderRadius: 20,
              background: "rgba(255, 255, 255, 0.08)",
              fontSize: 14,
              color: "var(--text)",
            }}
          >
            "{transcript}"
          </div>
        )}
      </div>

      {/* 4. Response Display */}
      {busy ? (
        <div style={{ textAlign: "center", padding: 20, color: "var(--cyan)", fontSize: 15 }}>
          <Sparkles size={20} className="spin" style={{ margin: "0 auto 8px" }} />
          Checking weather data and farmer advisory…
        </div>
      ) : responseSummary ? (
        <div
          style={{
            padding: 20,
            borderRadius: 14,
            background: "rgba(255, 255, 255, 0.04)",
            border: "1px solid var(--cyan)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--cyan)", letterSpacing: "0.05em" }}>
              WEATHERGPT ADVICE
            </span>
            <button
              className="button secondary"
              style={{ padding: "4px 10px", fontSize: 12 }}
              onClick={() => speakText(responseSummary)}
            >
              <Volume2 size={14} /> Listen Again
            </button>
          </div>

          <p style={{ fontSize: 18, fontWeight: 600, lineHeight: 1.5, color: "var(--text)", margin: "0 0 14px" }}>
            {responseSummary}
          </p>

          {responseActions.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {responseActions.map((act, i) => (
                <div
                  key={i}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "rgba(16, 185, 129, 0.1)",
                    border: "1px solid rgba(16, 185, 129, 0.2)",
                    fontSize: 14,
                    color: "#e2fbe8",
                  }}
                >
                  ✓ {act.replace(/^[✓•\s]+/, "")}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Text input alternative */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          askWeatherGPT(transcript);
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          type="text"
          className="input"
          style={{ flex: 1, padding: "12px 16px", fontSize: 15 }}
          placeholder="Or type simple question here..."
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
        />
        <button type="submit" className="button primary" disabled={busy || !transcript.trim()}>
          Ask
        </button>
      </form>
    </div>
  );
}
