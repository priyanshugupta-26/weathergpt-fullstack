import { useEffect, useState } from "react";
import { MapPin, Plus, Sparkles, ShieldAlert } from "lucide-react";
import { useApp } from "@/lib/context";
import { api, type Row } from "@/lib/api";
import { Heading, CurrentCard, Chart, Empty } from "@/components/WeatherUI";
import { Auth } from "./Account";
import ModelConsole from "@/components/ModelConsole";
export default function Dashboard() {
  const { user, place, setPlace, weather, navigate, toast, alerts } = useApp();
  const [locations, setLocations] = useState<Row[]>([]),
    [messages, setMessages] = useState<Row[]>([]),
    [error, setError] = useState("");
  const load = () => {
    if (!user) return;
    Promise.all([api("/api/locations/saved"), api("/api/chat/history")])
      .then(([l, m]) => {
        setLocations(l.locations);
        setMessages(m.messages.filter((m: Row) => m.role === "user").reverse());
      })
      .catch((e) => setError(e.message));
  };
  useEffect(load, [user]);
  if (!user) return <Auth />;
  return (
    <>
      <Heading
        title={`Your day, ${user.name.split(" ")[0]}.`}
        subtitle="A personal view of the places and conditions that matter."
      >
        <button className="button primary" onClick={() => navigate("/chat")}>
          <Sparkles size={15} />
          Ask WeatherGPT
        </button>
      </Heading>
      {error && <div className="error-note">{error}</div>}
      <div className="hero-grid">
        <CurrentCard />
        <section className="card">
          <div className="card-head">
            <h2>Your weather trend</h2>
            <small>Next 48 hours</small>
          </div>
          <Chart
            data={
              weather?.hourly
                .filter(
                  (h) => !weather.timestamp || h.time >= weather.timestamp.slice(0, 13) + ":00",
                )
                .slice(0, 48) || []
            }
            tall
          />
        </section>
      </div>
      <div className="below-grid">
        <section className="card">
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
                  load();
                  toast("Location saved");
                } catch (e) {
                  toast((e as Error).message);
                }
              }}
            >
              <Plus size={15} />
              Save current
            </button>
          </div>
          {locations.length ? (
            locations.map((p) => (
              <button
                className="prompt"
                key={p.id}
                onClick={() =>
                  setPlace({ name: p.name, latitude: p.latitude, longitude: p.longitude })
                }
              >
                <MapPin size={16} />
                {p.name}
                <span className="muted">
                  {p.latitude.toFixed(2)}°, {p.longitude.toFixed(2)}°
                </span>
              </button>
            ))
          ) : (
            <Empty title="Keep your places close">Search for a location, then save it here.</Empty>
          )}
        </section>
        <section className="card">
          <h2>Recent questions</h2>
          {messages.slice(0, 5).map((m, i) => (
            <button
              className="prompt"
              key={i}
              onClick={() => navigate("/chat?q=" + encodeURIComponent(m.content))}
            >
              {m.content} ↗
            </button>
          ))}
          {!messages.length && (
            <p className="muted" style={{ marginTop: 20 }}>
              Your signed-in weather questions will appear here.
            </p>
          )}
        </section>
      </div>
      <div className="alert-banner">
        <ShieldAlert size={20} />
        <div>
          <h3>{alerts.length} local threshold alerts</h3>
          <p>Disaster risk is not fully assessed by weather-only screening.</p>
        </div>
        <button className="button" onClick={() => navigate("/alerts")}>
          Review alerts
        </button>
      </div>
      <ModelConsole />
    </>
  );
}
