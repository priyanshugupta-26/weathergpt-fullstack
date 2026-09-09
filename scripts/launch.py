"""Cross-platform one-command bootstrap. Run from any working directory."""

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
PID_FILE = DATA / "server.pid"
URL = "http://127.0.0.1:8000"


def run(args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def fingerprint(paths):
    h = hashlib.sha256()
    for path in sorted(paths):
        h.update(str(path.relative_to(ROOT)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def launch():
    try:
        with urllib.request.urlopen(URL + "/api/health", timeout=2) as response:
            if json.load(response).get("version") == "1.0.0":
                print("WeatherGPT is already running: " + URL)
                if "--no-browser" not in sys.argv:
                    webbrowser.open(URL)
                return
    except Exception:
        pass
    python = (
        ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not python.exists():
        print("Creating Python environment…")
        venv.create(ROOT / ".venv", with_pip=True)
    requirements = fingerprint([ROOT / "requirements.txt"])
    marker = DATA / "python-dependencies.sha256"
    if not marker.exists() or marker.read_text() != requirements:
        run([python, "-m", "pip", "install", "-r", "requirements.txt"])
        marker.write_text(requirements)
    npm = "npm.cmd" if os.name == "nt" else "npm"
    frontend = ROOT / "frontend"
    dependencies = fingerprint(
        [frontend / "package.json", frontend / "package-lock.json"]
    )
    marker = DATA / "node-dependencies.sha256"
    if (
        not (frontend / "node_modules").exists()
        or not marker.exists()
        or marker.read_text() != dependencies
    ):
        run([npm, "ci"], frontend)
        marker.write_text(dependencies)
    sources = [
        p
        for directory in ["app", "components", "lib", "hooks", "public"]
        for p in (frontend / directory).rglob("*")
        if p.is_file()
    ]
    sources += [
        frontend / "index.html",
        frontend / "vite.config.ts",
        frontend / "package.json",
        frontend / "package-lock.json",
    ]
    build_hash = fingerprint(sources)
    marker = DATA / "frontend-build.sha256"
    if (
        not (frontend / "dist/client/index.html").exists()
        or not marker.exists()
        or marker.read_text() != build_hash
    ):
        run([npm, "run", "build"], frontend)
        marker.write_text(build_hash)
    if not (ROOT / ".env").exists():
        (ROOT / ".env").write_text((ROOT / ".env.example").read_text())
        if os.name != "nt":
            os.chmod(ROOT / ".env", 0o600)
    # Optional local admin bootstrap is explicit and never used in Docker/production.
    if "--seed-admin" in sys.argv:
        password = secrets.token_urlsafe(24)
        with (ROOT / ".env").open("a") as stream:
            stream.write(
                f"\nADMIN_EMAIL=admin@weathergpt.local\nADMIN_PASSWORD={password}\n"
            )
        credentials = DATA / "local-admin.txt"
        credentials.write_text(
            f"Local development administrator\nEmail: admin@weathergpt.local\nPassword: {password}\n"
        )
        if os.name != "nt":
            os.chmod(credentials, 0o600)
        print("Local admin credentials: " + str(credentials))
    process = subprocess.Popen(
        [
            str(python),
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
    )
    PID_FILE.write_text(str(process.pid))
    try:
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError("Server exited during startup")
            try:
                with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.25)
        else:
            raise RuntimeError("Server did not become healthy")
        print(
            "\nWeatherGPT is ready: "
            + URL
            + "\nKeep this window open. Press Ctrl+C to stop.\n",
            flush=True,
        )
        if "--no-browser" not in sys.argv:
            webbrowser.open(URL)
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping WeatherGPT…")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        if PID_FILE.exists() and PID_FILE.read_text() == str(process.pid):
            PID_FILE.unlink()


if __name__ == "__main__":
    try:
        launch()
    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as error:
        print(f"Launch failed: {error}", file=sys.stderr)
        sys.exit(1)
