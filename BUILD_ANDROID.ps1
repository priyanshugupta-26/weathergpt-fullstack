Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         WeatherGPT Android Mobile Build Automation       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptPath

Write-Host ">> [1/3] Building Web Production Bundle..." -ForegroundColor Yellow
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Frontend compilation failed."
    exit $LASTEXITCODE
}

Write-Host ">> [2/3] Syncing Capacitor Assets..." -ForegroundColor Yellow
npx cap sync android
if ($LASTEXITCODE -ne 0) {
    Write-Error "Capacitor sync failed."
    exit $LASTEXITCODE
}

Write-Host ">> [3/3] Assembling Debug APK..." -ForegroundColor Yellow
Set-Location "$scriptPath/android"
./gradlew.bat assembleDebug
if ($LASTEXITCODE -ne 0) {
    Write-Error "Gradle build failed."
    exit $LASTEXITCODE
}

Set-Location $scriptPath
$apkPath = "$scriptPath/android/app/build/outputs/apk/debug/app-debug.apk"
if (Test-Path $apkPath) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] APK Built: $apkPath" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
}
