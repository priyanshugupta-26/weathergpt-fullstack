import { Capacitor } from "@capacitor/core";
import { PushNotifications, Token, ActionPerformed, PushNotificationSchema } from "@capacitor/push-notifications";
import { api } from "./api";

export type PushCallback = (notification: PushNotificationSchema) => void;

class PushNotificationManager {
  private registeredToken: string | null = null;
  private onForegroundListeners: PushCallback[] = [];

  public isNative(): boolean {
    return Capacitor.isNativePlatform();
  }

  public async initPush(onForegroundAlert?: PushCallback) {
    if (onForegroundAlert) {
      this.onForegroundListeners.push(onForegroundAlert);
    }

    if (this.isNative()) {
      await this.initNativeFCM();
    } else {
      // Running in browser / PWA
      await this.initWebPush();
    }
  }

  // ========================================================
  // Native Android FCM Integration (Sections 10, 17, 18)
  // ========================================================
  private async initNativeFCM() {
    try {
      let permStatus = await PushNotifications.checkPermissions();

      if (permStatus.receive === "prompt") {
        permStatus = await PushNotifications.requestPermissions();
      }

      if (permStatus.receive !== "granted") {
        console.warn("Push notification permission not granted by user:", permStatus.receive);
        return;
      }

      // Register device with FCM
      await PushNotifications.register();

      // Listen for FCM Token
      await PushNotifications.addListener("registration", async (token: Token) => {
        this.registeredToken = token.value;
        try {
          await api("/api/push/register-device", {
            method: "POST",
            body: JSON.stringify({
              platform: "android",
              device_token: token.value,
              device_name: "Android Mobile Device",
            }),
          });
          console.info("FCM Token successfully synced to WeatherGPT backend");
        } catch (err) {
          console.error("Failed to sync FCM token to backend:", err);
        }
      });

      // Registration error
      await PushNotifications.addListener("registrationError", (error: any) => {
        console.error("FCM registration error: ", error);
      });

      // Foreground notification received (Section 18)
      await PushNotifications.addListener(
        "pushNotificationReceived",
        (notification: PushNotificationSchema) => {
          console.info("Foreground notification received:", notification);
          this.onForegroundListeners.forEach((fn) => fn(notification));
          window.dispatchEvent(
            new CustomEvent("wg:foreground_push", { detail: notification })
          );
        }
      );

      // Notification action performed / tapped (Section 17 - Deep Linking)
      await PushNotifications.addListener(
        "pushNotificationActionPerformed",
        (action: ActionPerformed) => {
          console.info("Push notification tapped:", action);
          const data = action.notification.data || {};
          const alertId = data.alert_id || data.id;
          const targetUrl = data.url || (alertId ? `/alerts/${alertId}` : "/alerts");

          // Dispatch deep link navigation event
          window.dispatchEvent(
            new CustomEvent("wg:navigate", {
              detail: { url: targetUrl, alert_id: alertId, tab: "alerts" },
            })
          );
        }
      );
    } catch (err) {
      console.warn("Capacitor Push Notifications initialization error:", err);
    }
  }

  // ========================================================
  // Web Push for Browsers & PWA (Section 8, 9)
  // ========================================================
  private async initWebPush() {
    if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) {
      return;
    }
    // Auto-check if permission is already granted
    if (Notification.permission === "granted") {
      try {
        const { publicKey } = await api<{ publicKey: string }>("/api/notifications/vapid-public-key");
        if (!publicKey) return;

        const reg = await navigator.serviceWorker.ready;
        let sub = await reg.pushManager.getSubscription();
        if (!sub) {
          const padding = "=".repeat((4 - (publicKey.length % 4)) % 4);
          const base64 = (publicKey + padding).replace(/-/g, "+").replace(/_/g, "/");
          const rawData = window.atob(base64);
          const outputArray = new Uint8Array(rawData.length);
          for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
          }
          sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: outputArray,
          });
        }
        if (sub) {
          const subJSON = sub.toJSON();
          this.registeredToken = subJSON.endpoint || null;
          await api("/api/push/register-device", {
            method: "POST",
            body: JSON.stringify({
              platform: "web",
              device_token: subJSON.endpoint,
              device_name: navigator.userAgent.slice(0, 100),
              p256dh: subJSON.keys?.p256dh,
              auth: subJSON.keys?.auth,
            }),
          });
        }
      } catch (e) {
        console.debug("Web push registration check:", e);
      }
    }
  }

  // ========================================================
  // Unregister / Logout (Section 57)
  // ========================================================
  public async unregister() {
    if (this.registeredToken) {
      try {
        await api("/api/push/unregister-device", {
          method: "POST",
          body: JSON.stringify({ device_token: this.registeredToken }),
        });
      } catch {}
      this.registeredToken = null;
    }
  }

  public getRegisteredToken(): string | null {
    return this.registeredToken;
  }
}

export const pushManager = new PushNotificationManager();
