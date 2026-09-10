# WeatherGPT Android & Mobile Architecture Documentation

## 1. System Architecture

WeatherGPT utilizes a unified **Single Backend Architecture** where both Web/PWA and native Android apps communicate directly with the production Render backend over secure HTTPS and WebSocket channels:

```
                            WEATHERGPT BACKEND
                 https://weathergpt-fullstack.onrender.com
                                    │
                        REST API / WebSocket
                                    │
               ┌────────────────────┴────────────────────┐
               ↓                                         ↓
        Desktop / PWA                             Android App
    (Modern Web / Service Worker)              (Capacitor 8.5)
               │                                         │
       Web Push (VAPID)                        Firebase Cloud Messaging
       RFC 8291 / RFC 8292                               │
               ↓                                         ↓
          Web Browser                             Android Device
```

---

## 2. Capacitor & Android Project Structure

The mobile wrapper is integrated directly with the existing responsive React 19 + Vite frontend.

- **Application ID**: `com.weathergpt.app`
- **Application Name**: `WeatherGPT`
- **Capacitor Configuration**: `capacitor.config.json`
- **Native Android Project**: `android/`
  - `android/app/src/main/AndroidManifest.xml`: Custom permissions (INTERNET, POST_NOTIFICATIONS, ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, RECORD_AUDIO, VIBRATE).
  - `android/app/src/main/res/mipmap-*`: Indigenous WeatherGPT wavefront branding launcher icons (48x48, 72x72, 96x96, 144x144, 192x192).
  - `android/app/build.gradle`: Versioning `versionCode 1`, `versionName "1.0.0"`.

---

## 3. Real Push Notification Pipeline (FCM + Web Push)

WeatherGPT implements **real, non-simulated push alerts**:

```
Official IMD / NDMA / CAP Alerts / WeatherGPT ML
                      │
                 Alert Fusion
                      │
                 Geo Matching (State / District / Radius)
                      │
               User Preferences
                      │
               Push Dispatcher
           ┌──────────┴──────────┐
           ↓                     ↓
     FCM (Android)        Web Push (VAPID)
           ↓                     ↓
     Android Device         PWA Browser
```

### Device Token Management
- **Table**: `push_devices`
  - `id`, `user_id`, `platform` (`android` or `web`), `device_token`, `device_name`, `enabled`, `created_at`, `updated_at`, `last_seen`.
- **Table**: `push_delivery_logs`
  - `id`, `alert_id`, `user_id`, `device_id`, `platform`, `status` (`QUEUED`, `SENT`, `FAILED`, `INVALID_TOKEN`, `NOT_CONFIGURED`), `sent_at`, `error_message`.

### Endpoints
- `POST /api/push/register-device`: Registers/refreshes FCM token or Web Push keys for authenticated user.
- `POST /api/push/unregister-device`: Disables device token on logout.
- `GET /api/push/devices`: Lists active registered devices for current user.
- `POST /api/push/test`: Diagnostic ping sending test alert via FCM and Web Push.
- `GET /api/push/status`: Real-time system health of Firebase and push subscribers.

---

## 4. Firebase Setup & Configuration

### For Android Native App:
1. Create a project in [Firebase Console](https://console.firebase.google.com/).
2. Add an Android App with package name: `com.weathergpt.app`.
3. Download `google-services.json`.
4. Place `google-services.json` at:
   ```
   android/app/google-services.json
   ```
   *(Do not commit private service accounts or secrets to public repositories).*

### For Backend FCM Dispatch:
1. In Firebase Console, go to **Project Settings** > **Service Accounts**.
2. Click **Generate New Private Key** to download the JSON credentials.
3. Configure the backend using one of the following methods:
   - **Method A (File path)**: Place the file at:
     ```
     backend/data/firebase-service-account.json
     ```
   - **Method B (Environment Variable)**:
     ```env
     FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", "project_id": "...", ...}'
     ```
   - **Method C (Google standard)**:
     ```env
     GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
     ```

If credentials are not yet supplied, the system operates in `NOT CONFIGURED` mode, safely logging all queued alerts to `push_delivery_logs` without failing application requests.

---

## 5. Mobile-First UX & Offline Experience

### Bottom Navigation
The phone interface features a high-accessibility 5-item bottom bar:
- **Home** (`/dashboard`): Immediate current weather card, active warnings, hourly strip, and quick actions.
- **Forecast** (`/forecast`): Daily & hourly multi-model weather projections.
- **WeatherGPT** (`/chat`): Full-featured conversational weather assistant with speech and source citations.
- **Alerts** (`/alerts`): Emergency disaster monitoring center sorted by severity and proximity.
- **More**: Bottom sheet drawer giving quick touch access to:
  - Live 3D Globe
  - Climate Analytics (10, 20, 30 Year Reanalysis)
  - Agriculture Advisory
  - Aviation Weather
  - Marine & Coastal Advisory
  - Smart City Air Quality & Heat Island Monitor
  - NWP / GFS 0.25° Model Layers
  - Rural Voice Portal
  - Data & Learning Lab
  - Model Lab (Champion/Challenger)
  - Notifications Center
  - SIH Matrix
  - Sources & Model Metrics
  - Profile & Location Settings
  - Low Data Mode Toggle
  - Secure Sign Out

### Stale-While-Revalidate (SWR) Caching
- Weather data for current and saved locations is locally cached in browser storage.
- On launch or network drop, cached weather is displayed immediately with timestamp indicator (`CACHED` or `STALE`).
- Background fetch refreshes data and updates state seamlessly.
- **Safety Critical**: Emergency disaster warnings are never misleadingly marked as live if expired or offline; they explicitly indicate `OFFLINE - Last received: <timestamp>`.

### Low Data Mode
- Accessible directly from the mobile "More" drawer.
- Disables heavy 3D globe geometry and high particle counts.
- Condenses charts, skips heavy radar images, and limits polling to conserve bandwidth on 2G/3G networks.

### Android Back Button
- Integrated with `@capacitor/app`.
- Closes open drawers or modals first.
- If in a sub-view (e.g. `/alerts`), returns to `/dashboard`.
- If on `/dashboard`, exits the app cleanly.

---

## 6. Build & Automation Scripts

### One-Command Debug Build:
```bash
# On macOS / Linux
./BUILD_ANDROID.sh

# On Windows Command Prompt
BUILD_ANDROID.bat

# On Windows PowerShell
./BUILD_ANDROID.ps1
```

### Manual Build Steps:
```bash
# 1. Build web bundle
npm --prefix frontend run build

# 2. Sync to Android project
npx cap sync android

# 3. Compile APK using Gradle (using JDK 21 LTS)
cd android
./gradlew assembleDebug
```

### Generated Debug APK:
```
android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 7. Future Signed Release Build (Play Store)

To produce an optimized, signed release `.aab` or `.apk` for Google Play Store:

1. **Generate Release Key**:
   ```bash
   keytool -genkey -v -keystore my-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias weathergpt-key
   ```
2. **Configure Signing**:
   In `android/app/build.gradle`:
   ```groovy
   signingConfigs {
       release {
           storeFile file('/path/to/my-release-key.jks')
           storePassword System.getenv("KEYSTORE_PASSWORD")
           keyAlias "weathergpt-key"
           keyPassword System.getenv("KEY_PASSWORD")
       }
   }
   buildTypes {
       release {
           signingConfig signingConfigs.release
           minifyEnabled true
           proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
       }
   }
   ```
3. **Build Android App Bundle (AAB)**:
   ```bash
   cd android
   ./gradlew bundleRelease
   ```
   The resulting bundle will be located at:
   ```
   android/app/build/outputs/bundle/release/app-release.aab
   ```
