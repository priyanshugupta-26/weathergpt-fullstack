import { useState } from "react";
import { CloudSun, Eye, EyeOff, UserPlus, AlertCircle, Globe } from "lucide-react";
import { useApp } from "@/lib/context";
import { api } from "@/lib/api";
import { LANGUAGES, t, isRTL } from "@/lib/i18n";

export default function Register() {
  const { setUser, language, setLanguage, toast, navigate } = useApp();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [stateName, setStateName] = useState("");
  const [district, setDistrict] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [isDuplicateEmail, setIsDuplicateEmail] = useState(false);

  const rtl = isRTL(language);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsDuplicateEmail(false);

    if (password.length < 8) {
      setError(t("auth.passwordHint", language) || "Password must be at least 8 characters");
      return;
    }

    if (password !== confirmPassword) {
      setError(t("auth.passwordsDoNotMatch", language) || "Passwords do not match");
      return;
    }

    if (!agreed) {
      setError(t("auth.agreeTermsError", language) || "Please agree to the Terms & Privacy Policy");
      return;
    }

    setBusy(true);
    try {
      const u = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: email.trim(),
          password,
          confirm_password: confirmPassword,
          full_name: fullName.trim(),
          name: fullName.trim(),
          mobile: mobile.trim() || undefined,
          state: stateName.trim() || undefined,
          district: district.trim() || undefined,
          city: district.trim() || undefined,
          preferred_language: language,
        }),
      });

      setUser(u);
      toast(t("onboarding.title", language) || "Account created successfully");
      navigate("/onboarding");
    } catch (err: any) {
      const msg = err.message || "Failed to create account";
      setError(msg);
      if (msg.toLowerCase().includes("already exists") || msg.toLowerCase().includes("duplicate")) {
        setIsDuplicateEmail(true);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-viewport" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "24px 16px" }}>
      {/* Background Decorative Gradient Orbs */}
      <div style={{ position: "fixed", top: "10%", left: "15%", width: 320, height: 320, borderRadius: "50%", background: "radial-gradient(circle, rgba(102,224,212,0.12) 0%, rgba(0,0,0,0) 70%)", pointerEvents: "none", zIndex: 0 }} />
      <div style={{ position: "fixed", bottom: "10%", right: "15%", width: 380, height: 380, borderRadius: "50%", background: "radial-gradient(circle, rgba(116,166,255,0.12) 0%, rgba(0,0,0,0) 70%)", pointerEvents: "none", zIndex: 0 }} />

      <div
        className="auth-card card"
        dir={rtl ? "rtl" : "ltr"}
        style={{
          width: "100%",
          maxWidth: 520,
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
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
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

          {/* Registration Top Language Switcher */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: "rgba(255,255,255,0.06)", border: "1px solid var(--line)", borderRadius: 10, padding: "4px 10px" }}>
            <Globe size={15} style={{ color: "var(--cyan)" }} />
            <select
              aria-label="Registration Language"
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
            onClick={() => navigate("/login")}
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
              userSelect: "none",
            }}
          >
            {t("auth.submitLogin", language) || "Sign In"}
          </button>
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
              userSelect: "none",
            }}
          >
            Create Account
          </button>
        </div>

        <div style={{ textAlign: rtl ? "right" : "left", marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: "0 0 6px", color: "var(--text)" }}>
            {t("auth.createAccount", language)}
          </h1>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: 0, lineHeight: 1.5 }}>
            {t("auth.registerSubtitle", language)}
          </p>
        </div>

        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
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
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <div style={{ flex: 1 }}>
              <div>{error}</div>
              {isDuplicateEmail && (
                <button
                  type="button"
                  onClick={() => navigate("/login")}
                  style={{
                    marginTop: 6,
                    padding: "4px 10px",
                    background: "#ef4444",
                    color: "#fff",
                    border: "none",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {t("auth.submitLogin", language)} →
                </button>
              )}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Full Name */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            {t("auth.fullName", language)} *
            <input
              type="text"
              required
              maxLength={100}
              placeholder={t("auth.fullNamePlaceholder", language)}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--line)",
                color: "var(--text)",
                fontSize: 14,
                outline: "none",
              }}
            />
          </label>

          {/* Email Address */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            {t("auth.email", language)} *
            <input
              type="email"
              required
              maxLength={254}
              placeholder={t("auth.emailPlaceholder", language)}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--line)",
                color: "var(--text)",
                fontSize: 14,
                outline: "none",
              }}
            />
          </label>

          {/* Mobile Number */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{t("auth.mobile", language)}</span>
              <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 400 }}>India (+91)</span>
            </div>
            <input
              type="tel"
              maxLength={20}
              placeholder={t("auth.mobilePlaceholder", language)}
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--line)",
                color: "var(--text)",
                fontSize: 14,
                outline: "none",
              }}
            />
          </label>

          {/* Password & Confirm Password (2-col) */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
              {t("auth.password", language)} *
              <div style={{ position: "relative" }}>
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={8}
                  maxLength={128}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  style={{
                    width: "100%",
                    padding: rtl ? "10px 14px 10px 38px" : "10px 38px 10px 14px",
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

            <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
              {t("auth.confirmPassword", language)} *
              <div style={{ position: "relative" }}>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  minLength={8}
                  maxLength={128}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  autoComplete="new-password"
                  style={{
                    width: "100%",
                    padding: rtl ? "10px 14px 10px 38px" : "10px 38px 10px 14px",
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
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
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
                  aria-label="Toggle confirm password visibility"
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </label>
          </div>

          {/* State & District / City */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
              {t("auth.state", language)}
              <input
                type="text"
                placeholder={t("auth.statePlaceholder", language)}
                value={stateName}
                onChange={(e) => setStateName(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid var(--line)",
                  color: "var(--text)",
                  fontSize: 14,
                  outline: "none",
                }}
              />
            </label>

            <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
              {t("auth.district", language)}
              <input
                type="text"
                placeholder={t("auth.districtPlaceholder", language)}
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid var(--line)",
                  color: "var(--text)",
                  fontSize: 14,
                  outline: "none",
                }}
              />
            </label>
          </div>

          {/* Preferred Language Selection */}
          <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
            {t("auth.preferredLanguage", language)}
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: 10,
                background: "rgba(255,255,255,0.04)",
                border: "1px solid var(--line)",
                color: "var(--text)",
                fontSize: 14,
                outline: "none",
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: "#101a2b", color: "#edf3fc" }}>
                  {l.nativeName} ({l.name})
                </option>
              ))}
            </select>
          </label>

          {/* Terms & Privacy checkbox */}
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", marginTop: 4, fontSize: 13, color: "var(--muted)" }}>
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ width: 16, height: 16, accentColor: "var(--cyan)", cursor: "pointer" }}
            />
            <span>{t("auth.termsAgree", language)}</span>
          </label>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={busy}
            style={{
              marginTop: 10,
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
            <UserPlus size={18} />
            {busy ? t("auth.creatingAccount", language) : t("auth.submitRegister", language)}
          </button>
        </form>

        {/* Footer Link */}
        <div style={{ marginTop: 24, textAlign: "center", borderTop: "1px solid var(--line)", paddingTop: 18 }}>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
            {t("auth.alreadyRegistered", language)}?{" "}
            <button
              type="button"
              onClick={() => navigate("/login")}
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
              {t("auth.submitLogin", language)}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
