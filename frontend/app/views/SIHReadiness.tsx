import { useEffect, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Search,
} from "lucide-react";
import { Heading } from "@/components/WeatherUI";
import { api } from "@/lib/api";
import { useApp } from "@/lib/context";

interface RequirementItem {
  id: string;
  name: string;
  category: string;
  status: "IMPLEMENTED" | "PARTIAL" | "EXTERNAL ACCESS REQUIRED" | "NOT CONFIGURED";
  evidence: string;
  route?: string;
  details: string;
}

export default function SIHReadiness() {
  const { navigate } = useApp();
  const [items, setItems] = useState<RequirementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const loadReadiness = async () => {
    setLoading(true);
    try {
      const res = await api<{ requirements: RequirementItem[] }>("/api/system/sih-readiness");
      setItems(res.requirements || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReadiness();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "IMPLEMENTED":
        return (
          <span className="badge" style={{ background: "rgba(16, 185, 129, 0.2)", color: "#10b981", fontWeight: 700 }}>
            ✓ IMPLEMENTED
          </span>
        );
      case "PARTIAL":
        return (
          <span className="badge" style={{ background: "rgba(56, 189, 248, 0.2)", color: "#38bdf8", fontWeight: 700 }}>
            ⚡ PARTIAL
          </span>
        );
      case "EXTERNAL ACCESS REQUIRED":
        return (
          <span className="badge warn" style={{ fontWeight: 700 }}>
            ⚠ ACCESS REQUIRED
          </span>
        );
      case "NOT CONFIGURED":
        return (
          <span className="badge neutral" style={{ fontWeight: 700 }}>
            ○ NOT CONFIGURED
          </span>
        );
      default:
        return <span className="badge neutral">{status}</span>;
    }
  };

  const filtered = items.filter((item) => {
    const matchesFilter = filter === "ALL" || item.status === filter;
    const matchesSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.details.toLowerCase().includes(search.toLowerCase()) ||
      item.category.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const implementedCount = items.filter((i) => i.status === "IMPLEMENTED").length;
  const partialCount = items.filter((i) => i.status === "PARTIAL").length;
  const externalCount = items.filter((i) => i.status === "EXTERNAL ACCESS REQUIRED").length;

  return (
    <>
      <Heading
        title="SIH 26068 Requirement Coverage"
        subtitle="Ministry of Earth Sciences (MoES) / IMD problem statement compliance matrix. Truthfully verified against live codebase execution."
      >
        <button className="button" onClick={loadReadiness} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          Re-audit Matrix
        </button>
      </Heading>

      {/* Summary Chips */}
      <div className="metric-strip" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <section className="card" style={{ borderLeft: "4px solid #10b981" }}>
          <div className="eyebrow" style={{ color: "#10b981" }}>FULLY IMPLEMENTED</div>
          <h1 style={{ marginTop: 8, fontSize: 32 }}>{implementedCount} / {items.length}</h1>
          <small>Production-ready SIH deliverables</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid #38bdf8" }}>
          <div className="eyebrow" style={{ color: "#38bdf8" }}>HYBRID / ADAPTED</div>
          <h1 style={{ marginTop: 8, fontSize: 32 }}>{partialCount}</h1>
          <small>Operational with browser/open fallbacks</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid #f59e0b" }}>
          <div className="eyebrow" style={{ color: "#f59e0b" }}>CREDENTIAL REQUIRED</div>
          <h1 style={{ marginTop: 8, fontSize: 32 }}>{externalCount}</h1>
          <small>Requires MoES/Govt API token</small>
        </section>

        <section className="card" style={{ borderLeft: "4px solid var(--cyan)" }}>
          <div className="eyebrow" style={{ color: "var(--cyan)" }}>AUTHENTICATION GATE</div>
          <h2 style={{ marginTop: 12, fontSize: 18 }}>Strict Login-First</h2>
          <small>Protected unauthenticated routes</small>
        </section>
      </div>

      {/* Filters and Search */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, margin: "16px 0" }}>
        <div className="alert-filters">
          {[
            ["ALL", "All Requirements"],
            ["IMPLEMENTED", "Implemented"],
            ["PARTIAL", "Partial"],
            ["EXTERNAL ACCESS REQUIRED", "Access Required"],
          ].map(([val, label]) => (
            <button
              key={val}
              className={filter === val ? "active" : ""}
              onClick={() => setFilter(val)}
            >
              {label}
            </button>
          ))}
        </div>

        <input
          type="text"
          className="input"
          placeholder="Search requirement or module…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 300 }}
        />
      </div>

      {/* Requirements Table */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {filtered.map((req) => (
          <div
            key={req.id}
            className="card"
            style={{
              padding: 16,
              borderLeft: `4px solid ${
                req.status === "IMPLEMENTED"
                  ? "#10b981"
                  : req.status === "PARTIAL"
                    ? "#38bdf8"
                    : req.status === "EXTERNAL ACCESS REQUIRED"
                      ? "#f59e0b"
                      : "var(--line)"
              }`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <h3 style={{ margin: 0, fontSize: 16 }}>{req.name}</h3>
                <span className="badge neutral" style={{ fontSize: 10, textTransform: "uppercase" }}>
                  {req.category}
                </span>
              </div>
              {getStatusBadge(req.status)}
            </div>

            <p style={{ fontSize: 13, color: "var(--text)", margin: "8px 0 10px", lineHeight: 1.5 }}>
              {req.details}
            </p>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, fontSize: 12, color: "var(--muted)" }}>
              <span>
                <strong>Evidence:</strong> <code>{req.evidence}</code>
              </span>
              {req.route && (
                <button
                  className="button secondary"
                  style={{ fontSize: 11, padding: "2px 8px" }}
                  onClick={() => navigate(req.route!)}
                >
                  Test in UI <ExternalLink size={12} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
