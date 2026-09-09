import { useEffect, useState } from "react";
import { Key, ShieldCheck, Cpu, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { Heading } from "@/components/WeatherUI";
import { api, type Row } from "@/lib/api";
import { useApp } from "@/lib/context";

export default function Setup() {
  const { toast } = useApp();
  const [status, setStatus] = useState<Row | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<Row | null>(null);
  const [error, setError] = useState("");

  const [groqKey, setGroqKey] = useState("");
  const [groqModel, setGroqModel] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [aiProvider, setAiProvider] = useState("auto");
  const [imdToken, setImdToken] = useState("");
  const [imdHeader, setImdHeader] = useState("Authorization");
  const [imdScheme, setImdScheme] = useState("Bearer");

  const loadStatus = () => {
    setLoading(true);
    setError("");
    api("/api/setup/status")
      .then((data) => {
        setStatus(data);
        if (data.selection) setAiProvider(data.selection);
        if (data.groq_model) setGroqModel(data.groq_model);
        if (data.gemini_model) setGeminiModel(data.gemini_model);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, any> = {
        ai_provider: aiProvider,
      };
      if (groqKey.trim()) payload.groq_api_key = groqKey.trim();
      if (groqModel.trim()) payload.groq_model = groqModel.trim();
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();
      if (geminiModel.trim()) payload.gemini_model = geminiModel.trim();
      if (imdToken.trim()) payload.imd_token = imdToken.trim();
      if (imdHeader) payload.imd_auth_header = imdHeader;
      if (imdScheme !== undefined) payload.imd_auth_scheme = imdScheme;

      const res = await api("/api/setup", {
        method: "POST",
        headers: {
          "x-weathergpt-setup": "1",
        },
        body: JSON.stringify(payload),
      });

      toast(res.message || "Settings saved successfully to .env.local");
      setGroqKey("");
      setGeminiKey("");
      setImdToken("");
      loadStatus();
    } catch (err: any) {
      setError(err.message || "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api("/api/ai/check", {
        method: "POST",
        headers: { "x-weathergpt-setup": "1" },
      });
      setTestResult(res);
      toast("AI connection test complete");
    } catch (err: any) {
      setError(err.message || "Connection check failed");
    } finally {
      setTesting(false);
    }
  };

  if (loading) return <div className="loading" aria-label="Loading setup" />;

  return (
    <div style={{ maxWidth: 880, margin: "0 auto", paddingBottom: 60 }}>
      <Heading
        title="Secure local setup"
        subtitle="Configure API credentials server-side. Keys are stored exclusively in .env.local with strict filesystem permissions (0600) and are never exposed to the client or committed to git."
      >
        <button className="button secondary" onClick={loadStatus} disabled={loading}>
          <RefreshCw size={15} />
          Refresh
        </button>
      </Heading>

      {error && <div className="error-note">{error}</div>}

      <div className="metric-strip" style={{ marginBottom: 24 }}>
        <section className="card">
          <small>Groq API</small>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
            {status?.groq ? (
              <span className="badge" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)" }}>
                <CheckCircle2 size={14} /> Configured
              </span>
            ) : (
              <span className="badge" style={{ background: "rgba(148,163,184,0.15)", color: "#94a3b8" }}>
                Not Configured
              </span>
            )}
          </div>
          <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            {status?.groq_model || "Auto-detected LLaMA-3.3 / LLaMA-3.1"}
          </p>
        </section>

        <section className="card">
          <small>Gemini API</small>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
            {status?.gemini ? (
              <span className="badge" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)" }}>
                <CheckCircle2 size={14} /> Configured
              </span>
            ) : (
              <span className="badge" style={{ background: "rgba(148,163,184,0.15)", color: "#94a3b8" }}>
                Not Configured
              </span>
            )}
          </div>
          <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            {status?.gemini_model || "Auto-detected Gemini 2.5/2.0 Flash"}
          </p>
        </section>

        <section className="card">
          <small>IMD Official</small>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12 }}>
            {status?.imd ? (
              <span className="badge" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", border: "1px solid rgba(34,197,94,0.3)" }}>
                <CheckCircle2 size={14} /> Token Present
              </span>
            ) : (
              <span className="badge" style={{ background: "rgba(245,158,11,0.15)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.3)" }}>
                Public Catalog / Fallback
              </span>
            )}
          </div>
          <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
            Open-Meteo fallback active for India
          </p>
        </section>

        <section className="card">
          <small>Active Router Strategy</small>
          <h3 style={{ marginTop: 10, color: "var(--brand, #38bdf8)" }}>
            {(status?.selection || "auto").toUpperCase()}
          </h3>
          <p className="muted" style={{ marginTop: 4, fontSize: 12 }}>
            Groq → Gemini → Deterministic
          </p>
        </section>
      </div>

      <form onSubmit={handleSave} className="card" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, borderBottom: "1px solid var(--border)", paddingBottom: 14 }}>
          <ShieldCheck size={22} color="var(--brand, #38bdf8)" />
          <div>
            <h2 style={{ fontSize: 18, margin: 0 }}>API Credentials & Model Preferences</h2>
            <small className="muted">Leave key inputs blank to preserve currently stored credentials.</small>
          </div>
        </div>

        <div>
          <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
            AI Routing Strategy
          </label>
          <select
            value={aiProvider}
            onChange={(e) => setAiProvider(e.target.value)}
            className="input"
            style={{ width: "100%" }}
          >
            <option value="auto">Auto (Groq primary → Gemini fallback → Deterministic rules)</option>
            <option value="groq">Groq Only</option>
            <option value="gemini">Gemini Only</option>
            <option value="deterministic">Deterministic Engine Only (Zero external API dependencies)</option>
          </select>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
              Groq API Key
            </label>
            <input
              type="password"
              placeholder={status?.groq ? "•••••••••••••••• (Configured)" : "gsk_..."}
              value={groqKey}
              onChange={(e) => setGroqKey(e.target.value)}
              className="input"
              style={{ width: "100%" }}
              autoComplete="off"
            />
            <small className="muted">Used for ultra-low-latency LLaMA inference.</small>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
              Groq Model Override (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. llama-3.3-70b-versatile or leave blank for auto"
              value={groqModel}
              onChange={(e) => setGroqModel(e.target.value)}
              className="input"
              style={{ width: "100%" }}
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
              Google Gemini API Key
            </label>
            <input
              type="password"
              placeholder={status?.gemini ? "•••••••••••••••• (Configured)" : "AIzaSy..."}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              className="input"
              style={{ width: "100%" }}
              autoComplete="off"
            />
            <small className="muted">Official Google GenAI SDK integration.</small>
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
              Gemini Model Override (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. gemini-2.5-flash or leave blank for auto"
              value={geminiModel}
              onChange={(e) => setGeminiModel(e.target.value)}
              className="input"
              style={{ width: "100%" }}
            />
          </div>
        </div>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 16 }}>
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>India Meteorological Department (IMD) Credentials</h3>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 16 }}>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
                IMD API Token
              </label>
              <input
                type="password"
                placeholder={status?.imd ? "•••••••••••••••• (Configured)" : "Token if authorized"}
                value={imdToken}
                onChange={(e) => setImdToken(e.target.value)}
                className="input"
                style={{ width: "100%" }}
                autoComplete="off"
              />
              <small className="muted">If left blank, WeatherGPT uses public catalogs + Open-Meteo fallback.</small>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
                Auth Header
              </label>
              <select
                value={imdHeader}
                onChange={(e) => setImdHeader(e.target.value)}
                className="input"
                style={{ width: "100%" }}
              >
                <option value="Authorization">Authorization</option>
                <option value="X-API-Key">X-API-Key</option>
                <option value="api-key">api-key</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", marginBottom: 6, fontWeight: 500, fontSize: 13 }}>
                Scheme
              </label>
              <select
                value={imdScheme}
                onChange={(e) => setImdScheme(e.target.value)}
                className="input"
                style={{ width: "100%" }}
              >
                <option value="Bearer">Bearer</option>
                <option value="">None (Raw Token)</option>
              </select>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border)", paddingTop: 18 }}>
          <button
            type="button"
            className="button secondary"
            onClick={testConnection}
            disabled={testing}
          >
            <Cpu size={16} />
            {testing ? "Testing AI providers..." : "Test AI connectivity"}
          </button>

          <button type="submit" className="button" disabled={saving}>
            <Key size={16} />
            {saving ? "Saving to .env.local..." : "Save Configuration"}
          </button>
        </div>
      </form>

      {testResult && (
        <section className="card" style={{ marginTop: 24 }}>
          <h3>AI Connectivity Report</h3>
          <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            {Object.entries(testResult.providers || {}).map(([name, p]: any) => (
              <div key={name} className="list-item" style={{ flexDirection: "column", alignItems: "flex-start" }}>
                <strong style={{ textTransform: "capitalize" }}>{name}</strong>
                <span style={{ color: p.status === "Connected" ? "#22c55e" : p.status === "Error" ? "#ef4444" : "#94a3b8", fontSize: 13 }}>
                  {p.status}
                </span>
                {p.model && <small className="muted">Model: {p.model}</small>}
                {p.latency_ms && <small className="muted">Latency: {p.latency_ms}ms</small>}
                {p.error && <small style={{ color: "#ef4444" }}>Error: {p.error}</small>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
