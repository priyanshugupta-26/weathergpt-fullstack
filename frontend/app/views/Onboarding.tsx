import { useState } from "react";
import {
  CloudSun,
  Globe,
  MapPin,
  LocateFixed,
  Bell,
  ArrowRight,
  ArrowLeft,
  Check,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { api, type Place } from "@/lib/api";
import { LANGUAGES, t, isRTL } from "@/lib/i18n";
import { Switch } from "@/components/ui/switch";

export default function Onboarding() {
  const { user, setUser, language, setLanguage, setPlace, notifications, setNotifications, toast, navigate } = useApp();
  const [step, setStep] = useState(1);
  const [locating, setLocating] = useState(false);
  const [detectedLoc, setDetectedLoc] = useState<Place | null>(null);
  const [manualState, setManualState] = useState(user?.state || "");
  const [manualDistrict, setManualDistrict] = useState(user?.district || user?.city || "");
  const [alertPrefs, setAlertPrefs] = useState<Record<string, boolean>>({
    HeavyRain: true,
    Thunderstorm: true,
    Lightning: true,
    Cyclone: true,
    Flood: true,
    Heatwave: true,
    ColdWave: false,
    StrongWind: true,
    Earthquake: true,
    Marine: false,
    ...notifications,
  });
  const [saving, setSaving] = useState(false);

  const rtl = isRTL(language);

  // Step 2: Browser geolocation handler
  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      toast("Geolocation is not supported by your browser. Please enter location manually.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const p: Place = {
          name: manualDistrict || "My Location",
          latitude: Number(pos.coords.latitude.toFixed(4)),
          longitude: Number(pos.coords.longitude.toFixed(4)),
          country: "India",
        };
        setDetectedLoc(p);
        setLocating(false);
        toast("Current coordinates detected successfully");
      },
      (err) => {
        setLocating(false);
        toast(
          err.code === 1
            ? "Location permission denied. Please enter state and district manually."
            : "Could not retrieve location. Please enter manually.",
        );
      },
      { timeout: 10000 },
    );
  };

  const finishOnboarding = async () => {
    setSaving(true);
    try {
      let finalPlace: Place = detectedLoc || {
        name: manualDistrict || manualState || "Patna",
        latitude: 25.5941,
        longitude: 85.1376,
        country: "India",
      };

      // If user entered manual location without coordinates, try resolving or fallback
      if (!detectedLoc && manualDistrict) {
        try {
          const res = await api<any[]>(`/api/locations/search?q=${encodeURIComponent(manualDistrict)}`);
          if (res && res.length > 0) {
            finalPlace = {
              name: res[0].name,
              latitude: res[0].latitude,
              longitude: res[0].longitude,
              country: res[0].country || "India",
            };
          }
        } catch {
          // Keep default if search fails
        }
      }

      setPlace(finalPlace);
      setNotifications(alertPrefs);

      // Save to server profile
      const updated = await api("/api/profile", {
        method: "PATCH",
        body: JSON.stringify({
          name: user?.name,
          language,
          preferred_language: language,
          state: manualState,
          district: manualDistrict,
          city: manualDistrict,
          default_location: finalPlace,
          notifications: alertPrefs,
        }),
      });

      setUser(updated);
      toast("Welcome to WeatherGPT!");
      navigate("/dashboard");
    } catch (e: any) {
      toast(e.message || "Failed to save preferences");
      navigate("/dashboard");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="onboarding-viewport"
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "24px 16px",
      }}
    >
      <div
        className="card"
        dir={rtl ? "rtl" : "ltr"}
        style={{
          width: "100%",
          maxWidth: 620,
          background: "rgba(16, 26, 43, 0.9)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 20,
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.6)",
          padding: "32px",
        }}
      >
        {/* Header with Step indicator */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "linear-gradient(135deg, rgba(102,224,212,0.2), rgba(116,166,255,0.2))",
                border: "1px solid var(--cyan)",
                color: "var(--cyan)",
              }}
            >
              <CloudSun size={20} />
            </span>
            <span style={{ fontSize: 18, fontWeight: 800 }}>WeatherGPT</span>
          </div>

          <div style={{ display: "flex", gap: 6 }}>
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                style={{
                  width: 32,
                  height: 6,
                  borderRadius: 3,
                  background: s <= step ? "var(--cyan)" : "rgba(255,255,255,0.15)",
                  transition: "background 0.3s ease",
                }}
              />
            ))}
          </div>
        </div>

        {/* STEP 1: PREFERRED LANGUAGE */}
        {step === 1 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--cyan)", marginBottom: 4 }}>
              <Globe size={18} />
              <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {t("onboarding.step1Title", language)}
              </span>
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
              Choose your language
            </h2>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 20px" }}>
              {t("onboarding.step1Desc", language)}
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                gap: 8,
                maxHeight: 300,
                overflowY: "auto",
                padding: 4,
                marginBottom: 24,
              }}
            >
              {LANGUAGES.map((l) => {
                const active = language === l.code;
                return (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => setLanguage(l.code)}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                      padding: "10px 12px",
                      borderRadius: 10,
                      border: active ? "1.5px solid var(--cyan)" : "1px solid var(--line)",
                      background: active ? "rgba(102, 224, 212, 0.15)" : "rgba(255, 255, 255, 0.03)",
                      color: active ? "var(--cyan)" : "var(--text)",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <span style={{ fontSize: 14, fontWeight: 700 }}>{l.nativeName}</span>
                    <span style={{ fontSize: 11, color: active ? "var(--cyan)" : "var(--muted)" }}>{l.name}</span>
                  </button>
                );
              })}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => setStep(2)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--muted)",
                  fontSize: 13,
                  cursor: "pointer",
                  padding: "6px 12px",
                }}
              >
                {t("onboarding.skip", language)}
              </button>
              <button
                type="button"
                className="button primary"
                onClick={() => setStep(2)}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px" }}
              >
                <span>Continue</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: PRIMARY LOCATION */}
        {step === 2 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--cyan)", marginBottom: 4 }}>
              <MapPin size={18} />
              <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {t("onboarding.step2Title", language)}
              </span>
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
              Set primary location
            </h2>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 20px" }}>
              {t("onboarding.step2Desc", language)}
            </p>

            {/* Geolocation Button */}
            <div style={{ marginBottom: 20 }}>
              <button
                type="button"
                onClick={handleDetectLocation}
                disabled={locating}
                style={{
                  width: "100%",
                  padding: "14px 18px",
                  borderRadius: 12,
                  background: detectedLoc ? "rgba(16, 185, 129, 0.15)" : "rgba(255, 255, 255, 0.06)",
                  border: detectedLoc ? "1.5px solid #10b981" : "1px solid var(--line)",
                  color: detectedLoc ? "#10b981" : "var(--text)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 10,
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: locating ? "wait" : "pointer",
                  transition: "all 0.2s ease",
                }}
              >
                {locating ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>{t("onboarding.detectingLocation", language)}</span>
                  </>
                ) : detectedLoc ? (
                  <>
                    <Check size={18} />
                    <span>Location detected ({detectedLoc.latitude}, {detectedLoc.longitude})</span>
                  </>
                ) : (
                  <>
                    <LocateFixed size={18} />
                    <span>{t("onboarding.useCurrentLocation", language)}</span>
                  </>
                )}
              </button>
            </div>

            <div style={{ textAlign: "center", color: "var(--muted)", fontSize: 12, margin: "16px 0", position: "relative" }}>
              <span style={{ background: "#101a2b", padding: "0 10px", position: "relative", zIndex: 1 }}>
                {t("onboarding.orManual", language)}
              </span>
              <div style={{ position: "absolute", top: "50%", left: 0, right: 0, height: 1, background: "var(--line)" }} />
            </div>

            {/* Manual state & district selection */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
              <label className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 13, fontWeight: 600 }}>
                {t("auth.state", language)}
                <input
                  type="text"
                  placeholder="e.g. Bihar, Tamil Nadu"
                  value={manualState}
                  onChange={(e) => setManualState(e.target.value)}
                  style={{
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
                  placeholder="e.g. Patna, Chennai"
                  value={manualDistrict}
                  onChange={(e) => setManualDistrict(e.target.value)}
                  style={{
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

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                className="button"
                onClick={() => setStep(1)}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>
              <button
                type="button"
                className="button primary"
                onClick={() => setStep(3)}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px" }}
              >
                <span>Continue</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: ALERT PREFERENCES */}
        {step === 3 && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--cyan)", marginBottom: 4 }}>
              <ShieldAlert size={18} />
              <span style={{ fontSize: 13, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                {t("onboarding.step3Title", language)}
              </span>
            </div>
            <h2 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
              Alert preferences
            </h2>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 16px" }}>
              {t("onboarding.step3Desc", language)}
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
                maxHeight: 280,
                overflowY: "auto",
                padding: 4,
                marginBottom: 24,
              }}
            >
              {[
                { id: "HeavyRain", label: t("onboarding.heavyRain", language) },
                { id: "Thunderstorm", label: t("onboarding.thunderstorm", language) },
                { id: "Lightning", label: t("onboarding.lightning", language) },
                { id: "Cyclone", label: t("onboarding.cyclone", language) },
                { id: "Flood", label: t("onboarding.flood", language) },
                { id: "Heatwave", label: t("onboarding.heatwave", language) },
                { id: "ColdWave", label: t("onboarding.coldWave", language) },
                { id: "StrongWind", label: t("onboarding.strongWind", language) },
                { id: "Earthquake", label: t("onboarding.earthquake", language) },
                { id: "Marine", label: t("onboarding.marine", language) },
              ].map(({ id, label }) => {
                const active = alertPrefs[id] ?? true;
                return (
                  <div
                    key={id}
                    onClick={() => setAlertPrefs((p) => ({ ...p, [id]: !active }))}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "10px 14px",
                      borderRadius: 10,
                      background: active ? "rgba(102, 224, 212, 0.08)" : "rgba(255, 255, 255, 0.03)",
                      border: active ? "1px solid rgba(102, 224, 212, 0.3)" : "1px solid var(--line)",
                      cursor: "pointer",
                      userSelect: "none",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: active ? "var(--text)" : "var(--muted)" }}>
                      {label}
                    </span>
                    <Switch
                      checked={active}
                      onCheckedChange={(checked) => setAlertPrefs((p) => ({ ...p, [id]: checked }))}
                    />
                  </div>
                );
              })}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                type="button"
                className="button"
                onClick={() => setStep(2)}
                disabled={saving}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                <ArrowLeft size={16} />
                <span>Back</span>
              </button>

              <button
                type="button"
                disabled={saving}
                onClick={finishOnboarding}
                style={{
                  padding: "12px 24px",
                  borderRadius: 12,
                  background: "linear-gradient(135deg, var(--cyan), #3b82f6)",
                  color: "#051c20",
                  fontWeight: 700,
                  fontSize: 15,
                  border: "none",
                  cursor: saving ? "wait" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  boxShadow: "0 4px 20px -2px rgba(102, 224, 212, 0.4)",
                }}
              >
                {saving ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    <span>{t("onboarding.saving", language)}</span>
                  </>
                ) : (
                  <>
                    <span>{t("onboarding.enterPortal", language)}</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
