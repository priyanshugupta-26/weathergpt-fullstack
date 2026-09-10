import { useState } from "react";
import { CloudSun, Eye, EyeOff, LogIn, AlertCircle, Globe, HelpCircle } from "lucide-react";
import { useApp } from "@/lib/context";
import { api } from "@/lib/api";
import { LANGUAGES, t, isRTL } from "@/lib/i18n";

export default function Login() {
  const { setUser, language, setLanguage, toast, navigate } = useApp();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showForgotModal, setShowForgotModal] = useState(false);

  const rtl = isRTL(language);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const isPhone = /^[0-9+ -]{7,15}$/.test(identifier.trim());
      const payload: any = { password };
      if (isPhone) {
        payload.mobile = identifier.trim();
      } else {
        payload.email = identifier.trim();
      }

      const u = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setUser(u);
      if (u.preferred_language) {
        setLanguage(u.preferred_language);
      }
      toast(t("auth.submitLogin", language) || "Signed in successfully");
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Invalid email or password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-viewport" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "24px 16px" }}>
      {/* Decorative Orbs */}
      <div style={{ position: "fixed", top: "15%", right: "20%", width: 340, height: 340, borderRadius: "50%", background: "radial-gradient(circle, rgba(102,224,212,0.12) 0%, rgba(0,0,0,0) 70%)", pointerEvents: "none", zIndex: 0 }} />
      <div style={{ position: "fixed", bottom: "15%", left: "20%", width: 360, height: 360, borderRadius: "50%", background: "radial-gradient(circle, rgba(116,166,255,0.12) 0%, rgba(0,0,0,0) 70%)", pointerEvents: "none", zIndex: 0 }} />

      <div
        className="auth-card card"
        dir={rtl ? "rtl" : "ltr"}
        style={{
          width: "100%",
          maxWidth: 460,
          position: "relative",
          zIndex: 1,
          backdropFilter: "blur(16px)",
          background: "rgba(16, 26, 43, 0.88)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 20,
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.6)",
          padding: "32px 32px 36px",
        }}
      >
        {/* Brand & Language Selector Bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 38,
                height: 38,
                borderRadius: 12,
                background: "linear-gradient(135deg, rgba(102,224,212,0.2), rgba(116,166,255,0.2))",
                border: "1px solid var(--cyan)",
                color: "var(--cyan)",
              }}
            >
              <CloudSun size={22} />
            </span>
            <div>
              <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--text)" }}>
                WeatherGPT
              </span>
              <span style={{ fontSize: 10, fontWeight: 700, marginLeft: 6, padding: "2px 6px", borderRadius: 4, background: "rgba(102,224,212,0.15)", color: "var(--cyan)", border: "1px solid rgba(102,224,212,0.3)" }}>
                BETA
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.06)", border: "1px solid var(--line)", borderRadius: 10, padding: "4px 10px" }}>
            <Globe size={15} style={{ color: "var(--cyan)" }} />
            <select
              aria-label="Login Language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text)",
                fontSize: 13,
                fontWeight: 600,
                outline: "none",
                cursor: "pointer",
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: "#101a2b", color: "#edf3fc" }}>
                  {l.nativeName} ({l.name})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Auth Mode Switcher */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 6,
            background: "rgba(255,255,255,0.06)",
            padding: 4,
            borderRadius: 12,
            marginBottom: 22,
            border: "1px solid var(--line)",
          }}
        >
          <button
            type="button"
            style={{
              padding: "9px 12px",
              borderRadius: 8,
              border: "none",
              background: "var(--cyan)",
              color: "#080c14",
              fontWeight: 700,
              fontSize: 13,
              cursor: "default",
              boxShadow: "0 2px 8px rgba(102,224,212,0.3)",
            }}
          >
            {t("auth.submitLogin", language) || "Sign In"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/register")}
            style={{
              padding: "9px 12px",
              borderRadius: 8,
              border: "none",
              background: "transparent",
              color: "var(--muted)",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {t("auth.createAccount", language) || "Create Account"}
          </button>
        </div>

        <div style={{ textAlign: rtl ? "right" : "left", marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 6px", color: "var(--text)" }}>
            {t("auth.loginTitle", language)}
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
            {t("auth.loginSubtitle", language)}
          </p>
        </div>

        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 14px",
              borderRadius: 10,
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#fca5a5",
              fontSize: 13,
              marginBottom: 18,
            }}
            role="alert"
          >
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Email or Mobile Number */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            {t("auth.emailOrMobile", language)}
            <input
              type="text"
              required
              placeholder={t("auth.emailOrMobilePlaceholder", language)}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              autoComplete="username"
              style={{
                width: "100%",
                padding: "11px 14px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--line)",
                color: "var(--text)",
                fontSize: 14,
                outline: "none",
              }}
            />
          </label>

          {/* Password */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{t("auth.password", language)}</span>
              <button
                type="button"
                onClick={() => setShowForgotModal(true)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--cyan)",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: "pointer",
                  padding: 0,
                }}
              >
                {t("auth.forgotPassword", language)}
              </button>
            </div>
            <div style={{ position: "relative" }}>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                style={{
                  width: "100%",
                  padding: rtl ? "11px 14px 11px 38px" : "11px 38px 11px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid var(--line)",
                  color: "var(--text)",
                  fontSize: 14,
                  outline: "none",
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                style={{
                  position: "absolute",
                  [rtl ? "left" : "right"]: 10,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  color: "var(--muted)",
                  padding: 0,
                  cursor: "pointer",
                }}
                aria-label="Toggle password visibility"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={busy}
            style={{
              marginTop: 6,
              padding: "13px 20px",
              borderRadius: 12,
              background: "linear-gradient(135deg, var(--cyan), #3b82f6)",
              color: "#051c20",
              fontWeight: 700,
              fontSize: 15,
              border: "none",
              cursor: busy ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              boxShadow: "0 4px 20px -2px rgba(102, 224, 212, 0.4)",
              transition: "opacity 0.2s, transform 0.1s",
            }}
          >
            <LogIn size={18} />
            {busy ? t("auth.loggingIn", language) : t("auth.submitLogin", language)}
          </button>
        </form>

        {/* Footer Link */}
        <div style={{ marginTop: 24, textAlign: "center", borderTop: "1px solid var(--line)", paddingTop: 18 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
            {t("auth.dontHaveAccount", language)}?{" "}
            <button
              type="button"
              onClick={() => navigate("/register")}
              style={{
                background: "none",
                border: "none",
                color: "var(--cyan)",
                fontWeight: 700,
                cursor: "pointer",
                padding: "0 4px",
                textDecoration: "underline",
              }}
            >
              {t("auth.submitRegister", language)}
            </button>
          </p>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 16,
          }}
          onClick={() => setShowForgotModal(false)}
        >
          <div
            className="card"
            style={{ maxWidth: 400, width: "100%", padding: 24, borderRadius: 16 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <HelpCircle size={22} style={{ color: "var(--cyan)" }} />
              <h3 style={{ margin: 0, fontSize: 18 }}>{t("auth.forgotPassword", language)}</h3>
            </div>
            <p style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.5, margin: "0 0 18px" }}>
              In local/development mode, please contact your system administrator or re-register with an updated password. Passwords are securely hashed with Argon2 and cannot be retrieved in plaintext.
            </p>
            <button
              className="button primary"
              style={{ width: "100%" }}
              onClick={() => setShowForgotModal(false)}
            >
              Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
