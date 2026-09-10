# WeatherGPT Mobile Experience (Capacitor Android & iOS Wrapper)

This directory contains the native mobile wrapper configuration for WeatherGPT.

## Architecture
- **Unified Backend**: Directly consumes the single FastAPI backend (`http://127.0.0.1:8000` or deployed URL)
- **Unified Logic**: Runs the exact same authenticated portal, 23 Scheduled Indian Languages, WeatherGPT Orchestrator, Live Globe, Disaster Intelligence, NWP, and RAG engines
- **Mobile UX**: Automatically presents the mobile bottom navigation bar (`Home`, `Forecast`, `WeatherGPT`, `Alerts`, `Voice`)
- **Emergency Push**: Integrates Capacitor Push Notifications / Firebase Cloud Messaging (FCM) when `google-services.json` is provided, with graceful fallback to PWA Web Push

## Build Status
- **Source Configuration**: COMPLETE (`capacitor.config.json`, `AndroidManifest.xml`, `MainActivity.java`, `strings.xml`)
- **Android SDK Status**: **ANDROID SDK REQUIRED** (The host machine currently does not have `ANDROID_HOME` or `adb` installed in PATH).
- **PWA Status**: **FULLY OPERATIONAL** (Installable PWA with Service Worker `sw.js` stale-while-revalidate caching and VAPID Web Push).

## Build Instructions (When Android SDK is Installed)
```bash
# 1. Build frontend bundle
npm run build:web

# 2. Sync web assets into Capacitor Android project
npm run cap:sync

# 3. Build debug APK
npm run build:apk
# Output APK: mobile/android/app/build/outputs/apk/debug/app-debug.apk
```
