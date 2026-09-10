import { useEffect, useState } from "react";
import {
  Bell,
  CheckCircle,
  Trash2,
  ShieldAlert,
  Send,
  Radio,
  CheckCheck,
  RefreshCw,
  AlertTriangle,
  Info,
} from "lucide-react";
import { useApp } from "@/lib/context";
import { Heading, Empty } from "@/components/WeatherUI";
import { api } from "@/lib/api";

interface NotificationItem {
  id: number;
  title: string;
  body: string;
  category: string;
  severity: string;
  location: string;
  is_read: boolean;
  created_at: string;
  action_url?: string;
}

export default function Notifications() {
  const { user, toast, navigate } = useApp();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState<"ALL" | "UNREAD" | "WARNING" | "WEATHER" | "DISASTER">("ALL");
  const [loading, setLoading] = useState(true);
  const [pushStatus, setPushStatus] = useState<"default" | "granted" | "denied">("default");
  const [subscribing, setSubscribing] = useState(false);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const unreadParam = filter === "UNREAD" ? "?unread_only=true" : "";
      const catParam =
        filter === "WARNING"
          ? "?category=warning"
          : filter === "WEATHER"
            ? "?category=weather"
            : filter === "DISASTER"
              ? "?category=disaster"
              : "";
      const query = unreadParam || catParam;
      const res = await api<{ notifications: NotificationItem[]; unread_count: number }>(
        `/api/notifications${query}`,
      );
      setItems(res.notifications || []);
      setUnreadCount(res.unread_count || 0);
    } catch (e) {
      toast(`Failed to load notifications: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
    if ("Notification" in window) {
      setPushStatus(Notification.permission);
    }
  }, [filter]);

  const markRead = async (id: number) => {
    try {
      await api(`/api/notifications/${id}/read`, { method: "POST" });
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      toast((e as Error).message);
    }
  };

  const markAllRead = async () => {
    try {
      await api("/api/notifications/read-all", { method: "POST" });
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast("All notifications marked as read.");
    } catch (e) {
      toast((e as Error).message);
    }
  };

  const deleteItem = async (id: number) => {
    try {
      await api(`/api/notifications/${id}`, { method: "DELETE" });
      setItems((prev) => prev.filter((n) => n.id !== id));
      toast("Notification removed.");
    } catch (e) {
      toast((e as Error).message);
    }
  };

  const dispatchTestNotification = async () => {
    try {
      const res = await api<{ status: string; delivered: boolean }>("/api/notifications/test-dispatch", {
        method: "POST",
      });
      toast(`Test alert sent! Web Push delivery: ${res.delivered ? "SUCCESS" : "Stored in-app"}`);
      loadNotifications();
    } catch (e) {
      toast(`Dispatch failed: ${(e as Error).message}`);
    }
  };

  const subscribeWebPush = async () => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      toast("Web Push is not supported by your current browser.");
      return;
    }

    setSubscribing(true);
    try {
      const permission = await Notification.requestPermission();
      setPushStatus(permission);
      if (permission !== "granted") {
        toast("Push notification permission was denied.");
        setSubscribing(false);
        return;
      }

      const { publicKey } = await api<{ publicKey: string }>("/api/notifications/vapid-public-key");
      const reg = await navigator.serviceWorker.ready;

      // Convert VAPID key
      const padding = "=".repeat((4 - (publicKey.length % 4)) % 4);
      const base64 = (publicKey + padding).replace(/-/g, "+").replace(/_/g, "/");
      const rawData = window.atob(base64);
      const outputArray = new Uint8Array(rawData.length);
      for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
      }

      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: outputArray,
      });

      const subJSON = subscription.toJSON();
      await api("/api/notifications/subscribe", {
        method: "POST",
        body: JSON.stringify({
          endpoint: subJSON.endpoint,
          p256dh: subJSON.keys?.p256dh,
          auth: subJSON.keys?.auth,
          device_name: navigator.userAgent.slice(0, 100),
        }),
      });

      toast("Device registered for Geo-Targeted Emergency Push Alerts!");
    } catch (e) {
      toast(`Subscription error: ${(e as Error).message}`);
    } finally {
      setSubscribing(false);
    }
  };

  return (
    <>
      <Heading
        title="Notification Center"
        subtitle="Geo-targeted emergency alerts, meteorological watches, and official NDMA/IMD bulletins delivered directly to your device."
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button className="button secondary" onClick={loadNotifications} disabled={loading}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            Refresh
          </button>
          {unreadCount > 0 && (
            <button className="button secondary" onClick={markAllRead}>
              <CheckCheck size={14} />
              Mark all read
            </button>
          )}
          <button className="button" onClick={dispatchTestNotification}>
            <Send size={14} />
            Test Push Dispatch
          </button>
        </div>
      </Heading>

      {/* Push Subscription Card */}
      <section
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 20,
          background: "rgba(16, 185, 129, 0.05)",
          borderColor: "rgba(16, 185, 129, 0.3)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Radio size={22} style={{ color: "#10b981" }} />
          <div>
            <div style={{ fontWeight: 700, fontSize: 14 }}>
              Push Notification Pipeline (Android FCM & Web Push)
            </div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>
              {pushStatus === "granted"
                ? "Active · Device subscribed to official India CAP alerts"
                : pushStatus === "denied"
                  ? "Permission blocked in settings"
                  : "Enable background push alerts for severe lightning, cyclone, flood & IMD warnings"}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <button
            className={`button ${pushStatus === "granted" ? "secondary" : "primary"}`}
            onClick={subscribeWebPush}
            disabled={subscribing || pushStatus === "denied"}
          >
            {subscribing
              ? "Registering…"
              : pushStatus === "granted"
                ? "Re-sync Device Subscription"
                : "Enable Push Alerts"}
          </button>
          <button
            className="button secondary"
            style={{ fontSize: 12, borderColor: "var(--cyan)", color: "var(--cyan)" }}
            onClick={async () => {
              try {
                const res = await api<{ status: string; detail?: string }>("/api/push/test", { method: "POST" });
                if (res.status === "sent") {
                  toast("Test push sent successfully to registered device!");
                } else if (res.status === "not_configured") {
                  toast(`FIREBASE CONFIG REQUIRED: ${res.detail || "Credentials missing"}`);
                } else {
                  toast(`Push status: ${res.status} (${res.detail || ""})`);
                }
              } catch (e) {
                toast(`Push test failed: ${(e as Error).message}`);
              }
            }}
          >
            Send Test Push
          </button>
        </div>
      </section>

      {/* Filter Tabs */}
      <div className="alert-filters" style={{ marginBottom: 16 }}>
        {[
          ["ALL", "All Notifications"],
          ["UNREAD", `Unread (${unreadCount})`],
          ["WARNING", "Warnings"],
          ["WEATHER", "Weather"],
          ["DISASTER", "Disasters"],
        ].map(([val, label]) => (
          <button
            key={val}
            className={filter === val ? "active" : ""}
            onClick={() => setFilter(val as any)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {loading ? (
          <div className="loading" aria-label="Loading notifications" />
        ) : items.length > 0 ? (
          items.map((item) => (
            <section
              key={item.id}
              className="card"
              style={{
                padding: 16,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                opacity: item.is_read ? 0.75 : 1,
                borderLeft: `4px solid ${
                  item.severity === "WARNING" || item.severity === "SEVERE"
                    ? "#ef4444"
                    : "var(--cyan)"
                }`,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {!item.is_read && (
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: "#38bdf8",
                        display: "inline-block",
                      }}
                    />
                  )}
                  <h3 style={{ margin: 0, fontSize: 15 }}>{item.title}</h3>
                  <span className="badge neutral" style={{ fontSize: 10, textTransform: "uppercase" }}>
                    {item.category}
                  </span>
                </div>

                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <small style={{ color: "var(--muted)", fontSize: 11 }}>
                    {new Date(item.created_at).toLocaleString()}
                  </small>
                  {!item.is_read && (
                    <button
                      className="icon-btn"
                      title="Mark as read"
                      onClick={() => markRead(item.id)}
                    >
                      <CheckCircle size={15} />
                    </button>
                  )}
                  <button
                    className="icon-btn"
                    title="Delete notification"
                    onClick={() => deleteItem(item.id)}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.5, color: "var(--text)" }}>
                {item.body}
              </p>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                <small style={{ color: "var(--muted)" }}>Target Location: {item.location}</small>
                {item.action_url && (
                  <button
                    className="button secondary"
                    style={{ fontSize: 11, padding: "2px 8px" }}
                    onClick={() => navigate(item.action_url!)}
                  >
                    View Details
                  </button>
                )}
              </div>
            </section>
          ))
        ) : (
          <Empty title="No Notifications Found">
            <Bell size={36} style={{ margin: "14px auto", color: "var(--muted)" }} />
            You are all caught up. New emergency warnings and weather bulletins will appear here.
          </Empty>
        )}
      </div>
    </>
  );
}
