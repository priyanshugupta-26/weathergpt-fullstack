import { useState, useEffect } from "react";
import { Bell, Save, LogOut, UserPlus, LogIn, MapPin, Trash2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { useApp } from "@/lib/context";
import { api, type Row } from "@/lib/api";
import { Heading, Choice } from "@/components/WeatherUI";
import { LANGUAGES, t } from "@/lib/i18n";
export function Auth() {
  const { setUser, toast, navigate } = useApp();
  const [register, setRegister] = useState(false),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <section className="card auth-card">
      <h1>{register ? "Make it your forecast." : "Welcome back."}</h1>
      <p className="muted" style={{ fontSize: 14, marginTop: 12 }}>
        Save locations and keep your weather conversations together.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setError("");
          setBusy(true);
          try {
            if (register)
              await api("/api/auth/register", {
                method: "POST",
                body: JSON.stringify({ email, password, name }),
              });
            const u = await api("/api/auth/login", {
              method: "POST",
              body: JSON.stringify({ email, password }),
            });
            setUser(u);
            toast(register ? "Account created" : "Signed in");
            navigate("/dashboard");
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {register && (
          <label className="form-field">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={100}
              autoComplete="name"
            />
          </label>
        )}
        <label className="form-field">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            maxLength={254}
            autoComplete="email"
          />
        </label>
        <label className="form-field">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={10}
            maxLength={128}
            required
            autoComplete={register ? "new-password" : "current-password"}
          />
          <small>At least 10 characters</small>
        </label>
        {error && (
          <p className="error-note" role="alert">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy} style={{ width: "100%" }}>
          {register ? <UserPlus size={15} /> : <LogIn size={15} />}{" "}
          {busy ? "Please wait…" : register ? "Create account" : "Sign in"}
        </button>
      </form>
      <button
        className="prompt"
        onClick={() => {
          setRegister(!register);
          setError("");
        }}
      >
        {register ? "Already have an account? Sign in" : "New to WeatherGPT? Create an account"}
      </button>
    </section>
  );
}
export default function Account() {
  const {
    user,
    setUser,
    route,
    language,
    setLanguage,
    theme,
    setTheme,
    place,
    toast,
    notifications,
    setNotifications,
    navigate,
  } = useApp();
  const [name, setName] = useState(user?.name || ""),
    [permission, setPermission] = useState(
      "Notification" in window ? Notification.permission : "unsupported",
    ),
    [saving, setSaving] = useState(false),
    [saved, setSaved] = useState<Row[]>([]);
  useEffect(() => setName(user?.name || ""), [user]);
  useEffect(() => {
    if (user)
      api("/api/locations/saved")
        .then((d) => setSaved(d.locations))
        .catch((e) => toast(e.message));
  }, [user]);
  if (!user && route !== "/settings") return <Auth />;
  const save = async () => {
    if (!user) {
      toast("Preferences saved on this device. Sign in to sync them to your account.");
      return;
    }
    setSaving(true);
    try {
      const u = await api("/api/profile", {
        method: "PATCH",
        body: JSON.stringify({
          name,
          language,
          theme,
          units: "metric",
          default_location: place,
          notifications,
        }),
      });
      setUser(u);
      toast("Profile and preferences saved");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <>
      <Heading
        title={route === "/settings" ? "Make WeatherGPT yours." : "Your weather profile."}
        subtitle="Choose how you see, hear, and receive weather information."
      >
        <button className="button primary" onClick={save} disabled={saving}>
          <Save size={15} />
          {saving ? "Saving…" : "Save preferences"}
        </button>
      </Heading>
      <div className="settings-grid">
        <section className="card">
          <h2>Profile & preferences</h2>
          {user ? (
            <>
              <label className="form-field">
                Display name
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={100}
                  required
                />
              </label>
              <div className="detail-list">
                <span>Email</span>
                <span>{user.email}</span>
              </div>
            </>
          ) : (
            <p className="muted" style={{ fontSize: 14, marginTop: 18 }}>
              Preferences stay on this device.{" "}
              <button className="cyan" onClick={() => navigate("/profile")}>
                Sign in to sync.
              </button>
            </p>
          )}
          <div className="settings-row">
            <span>Response language</span>
            <Choice
              label="Preferred language"
              value={language}
              onChange={setLanguage}
              items={LANGUAGES.map((l) => ({
                value: l.code,
                label: `${l.nativeName} (${l.name})`,
              }))}
            />
          </div>
          <div className="settings-row">
            <span>Appearance</span>
            <Choice
              label="Theme"
              value={theme}
              onChange={setTheme}
              items={["dark", "light", "system"]}
            />
          </div>
          <div className="settings-row">
            <span>Units</span>
            <span className="badge neutral">METRIC · °C / KM/H</span>
          </div>
          <div className="detail-list">
            <span>Default location on save</span>
            <span>{place.name}</span>
          </div>
          {user && (
            <button
              className="button"
              style={{ marginTop: 20 }}
              onClick={async () => {
                try {
                  await api("/api/auth/logout", { method: "POST" });
                  setUser(null);
                  toast("Signed out");
                  navigate("/login");
                } catch (e) {
                  toast((e as Error).message);
                  setUser(null);
                  navigate("/login");
                }
              }}
            >
              <LogOut size={15} />
              Sign out
            </button>
          )}
        </section>
        <section className="card">
          <h2>Browser notifications</h2>
          <p className="muted" style={{ fontSize: 14, marginTop: 15 }}>
            Receive selected alerts while WeatherGPT is open. Background push delivery is not
            configured.
          </p>
          <div className="settings-row">
            <span>Browser permission</span>
            <span className="badge neutral">{permission.toUpperCase()}</span>
          </div>
          <button
            className="button"
            disabled={permission === "unsupported" || permission === "denied"}
            onClick={async () => {
              try {
                const p = await Notification.requestPermission();
                setPermission(p);
                toast(
                  p === "granted"
                    ? "Notifications enabled"
                    : "Alerts will remain visible in the application.",
                );
              } catch {
                toast("This browser could not enable notifications.");
              }
            }}
          >
            <Bell size={15} />
            Enable browser notifications
          </button>
          {[
            ["Weather", "Severe weather / heavy rain"],
            ["Cyclone", "Cyclone"],
            ["Wind", "High wind"],
            ["Heat", "Heatwave"],
            ["Earthquake", "Earthquake"],
            ["Flood", "Flood"],
            ["Marine", "Marine warning"],
          ].map(([key, label]) => (
            <div className="settings-row" key={key}>
              <label htmlFor={`notify-${key}`}>{label}</label>
              <Switch
                id={`notify-${key}`}
                checked={Boolean(notifications[key])}
                onCheckedChange={(v) => setNotifications({ ...notifications, [key]: v })}
              />
            </div>
          ))}
          <small>
            Only connected data sources can generate notifications. Official cyclone and flood feeds
            are unavailable.
          </small>
        </section>
      </div>
      {user && (
        <section className="card" style={{ marginTop: 20 }}>
          <div className="card-head">
            <h2>Saved locations</h2>
            <button
              className="button"
              onClick={async () => {
                try {
                  await api("/api/locations/saved", {
                    method: "POST",
                    body: JSON.stringify(place),
                  });
                  setSaved((await api("/api/locations/saved")).locations);
                  toast("Location saved");
                } catch (e) {
                  toast((e as Error).message);
                }
              }}
            >
              <MapPin size={15} />
              Save {place.name}
            </button>
          </div>
          {saved.length ? (
            saved.map((p) => (
              <div className="detail-list" key={p.id}>
                <span>
                  {p.name}{" "}
                  <small>
                    {p.latitude.toFixed(2)}, {p.longitude.toFixed(2)}
                  </small>
                </span>
                <button
                  aria-label={`Remove ${p.name}`}
                  onClick={async () => {
                    try {
                      await api(`/api/locations/saved/${p.id}`, { method: "DELETE" });
                      setSaved((s) => s.filter((l) => l.id !== p.id));
                    } catch (e) {
                      toast((e as Error).message);
                    }
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          ) : (
            <p className="muted">No locations saved yet.</p>
          )}
        </section>
      )}
    </>
  );
}
