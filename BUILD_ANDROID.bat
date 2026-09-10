@echo off
echo ==========================================================
echo          WeatherGPT Android Mobile Build Automation       
echo ==========================================================

cd /d "%~dp0"

echo [1/3] Building Web Production Bundle...
call npm --prefix frontend run build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Frontend build failed.
    exit /b %ERRORLEVEL%
)

echo [2/3] Syncing Capacitor Android Project...
call npx cap sync android
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Capacitor sync failed.
    exit /b %ERRORLEVEL%
)

echo [3/3] Compiling Android APK with Gradle...
cd android
call gradlew.bat assembleDebug
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gradle build failed.
    exit /b %ERRORLEVEL%
)

cd ..
echo ==========================================================
echo [SUCCESS] Android APK Generated:
echo android\app\build\outputs\apk\debug\app-debug.apk
echo ==========================================================
pause
