import { useEffect, useState } from "react";
import { RefreshCw, Activity } from "lucide-react";
import { useApp } from "@/lib/context";
import { api, type Row } from "@/lib/api";
import { Heading, Empty } from "@/components/WeatherUI";
import { Auth } from "./Account";
export default function Admin() {
  const { user } = useApp();
  const [data, setData] = useState<Row | null>(null),
    [error, setError] = useState("");
  const load = () => {
    setError("");
    api("/api/admin")
      .then(setData)
      .catch((e) => setError(e.message));
  };
  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user]);
  if (!user) return <Auth />;
  if (user.role !== "admin")
    return (
      <Empty title="Administrator access required">
        This account does not have access to operational data.
      </Empty>
    );
  return (
    <>
      <Heading
        title="System observatory."
        subtitle="Provider connectivity, models, ingestion, and application health."
      >
        <button className="button" onClick={load}>
          <RefreshCw size={15} />
          Refresh status
        </button>
      </Heading>
      {error && <div className="error-note">{error}</div>}
      {!data ? (
        <div className="loading" />
      ) : (
        <>
          <div className="metric-strip">
            {[
              ["Health", data.health],
              ["Registered users", data.users],
              ["Requests", data.requests],
              ["Database", data.database],
            ].map(([k, v]) => (
              <section className="card" key={k}>
                <small>{k}</small>
                <h2 style={{ marginTop: 15 }}>{v}</h2>
              </section>
            ))}
          </div>
          <div className="settings-grid" style={{ marginTop: 20 }}>
            <section className="card">
              <h2>Provider health</h2>
              {Object.entries(data.providers).map(([name, status]: any) => (
                <div className="detail-list" key={name}>
                  <span>{name}</span>
                  <span>
                    {status.status}
                    <small style={{ display: "block" }}>{status.checked_at}</small>
                  </span>
                </div>
              ))}
              {!Object.keys(data.providers).length && (
                <p className="muted">No provider requests yet.</p>
              )}
            </section>
            <section className="card">
              <h2>Model status</h2>
              {data.models.map((m: Row) => (
                <div className="detail-list" key={m.name}>
                  <span>{m.name}</span>
                  <span>
                    {m.status} · {m.mode}
                  </span>
                </div>
              ))}
              <h3 style={{ marginTop: 24 }}>Ingestion</h3>
              {Object.entries(data.ingestion).map(([k, v]) => (
                <div className="detail-list" key={k}>
                  <span>{k.replaceAll("_", " ")}</span>
                  <span>{String(v)}</span>
                </div>
              ))}
            </section>
            <section className="card">
              <h2>Active screening alerts</h2>
              {data.active_alerts.length ? (
                data.active_alerts.map((a: Row) => (
                  <div className="list-item" key={a.id}>
                    {a.description} · {a.location}
                  </div>
                ))
              ) : (
                <p className="muted" style={{ marginTop: 15 }}>
                  No active screening alerts.
                </p>
              )}
            </section>
            <section className="card">
              <h2>Recent errors</h2>
              {data.recent_errors.length ? (
                data.recent_errors.map((e: Row, i: number) => (
                  <div className="list-item" key={i}>
                    {e.component} · {e.type}
                    <small>{e.time}</small>
                  </div>
                ))
              ) : (
                <p className="muted" style={{ marginTop: 15 }}>
                  No application errors recorded this session.
                </p>
              )}
            </section>
          </div>
        </>
      )}
    </>
  );
}
