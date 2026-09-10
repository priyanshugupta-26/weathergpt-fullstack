#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "         WeatherGPT Android Mobile Build Automation       "
echo "=========================================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Detect Android SDK
if [ -z "$ANDROID_HOME" ]; then
  if [ -d "$HOME/Library/Android/sdk" ]; then
    export ANDROID_HOME="$HOME/Library/Android/sdk"
  elif [ -d "$LOCALAPPDATA/Android/Sdk" ]; then
    export ANDROID_HOME="$LOCALAPPDATA/Android/Sdk"
  fi
fi

# 2. Detect Java JDK (Prefer JDK 21 LTS if available)
if [ -z "$JAVA_HOME" ]; then
  if [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
    export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  fi
fi

echo ">> ANDROID_HOME: ${ANDROID_HOME:-'Not set'}"
echo ">> JAVA_HOME:    ${JAVA_HOME:-'Using default system Java'}"

# 3. Build Web App (Vite + React 19)
echo ">> Step 1/3: Building frontend bundle..."
npm --prefix frontend run build

# 4. Sync Capacitor
echo ">> Step 2/3: Syncing web bundle to Capacitor Android..."
npx cap sync android

# 5. Assemble Debug APK
echo ">> Step 3/3: Assembling native Android Debug APK..."
cd android
./gradlew assembleDebug

APK_PATH="$ROOT_DIR/android/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK_PATH" ]; then
  echo ""
  echo "=========================================================="
  echo "✔ BUILD SUCCESSFUL!"
  echo "✔ APK Location: $APK_PATH"
  echo "✔ Size: $(du -h "$APK_PATH" | cut -f1)"
  echo "=========================================================="
else
  echo "Build completed, check android/app/build/outputs/apk/ for binaries."
fi
