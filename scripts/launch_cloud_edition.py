"""Start local/Runpod compute plus the Studio UI from a double-click launcher."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "app" / "env" / "Scripts" / "python.exe"
SETTINGS = ROOT / "studio" / "data" / "runpod_settings.json"


def free_port(preferred: int = 8787) -> int:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


def wait_http(url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def provider() -> str:
    try:
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return "runpod" if data.get("provider") == "runpod" else "local"
    except Exception:
        return "local"


def stop(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    if not PYTHON.is_file():
        print("Run install-windows-cuda.bat first.")
        return 1
    local = provider() == "local"
    comfy = None
    studio = None
    port = free_port()
    env = os.environ.copy()
    env.update({"STUDIO_HOST": "127.0.0.1", "STUDIO_PORT": str(port), "PYTHONIOENCODING": "utf-8"})
    try:
        if local:
            print("Starting local CUDA backend...")
            comfy = subprocess.Popen(
                [str(PYTHON), str(ROOT / "comfy_boot.py"), "--listen", "127.0.0.1", "--disable-auto-launch"],
                cwd=ROOT,
                env=env,
            )
            if not wait_http("http://127.0.0.1:8188/system_stats", 180):
                raise RuntimeError("Local ComfyUI did not become ready")
        else:
            print("Runpod backend selected; local CUDA backend will not be started.")
        print("Starting Minimax H3 Studio - Cloud Edition...")
        studio = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(port), "--timeout-graceful-shutdown", "8"],
            cwd=ROOT / "studio",
            env=env,
        )
        url = f"http://127.0.0.1:{port}"
        if not wait_http(url + "/api/health", 60):
            raise RuntimeError("Studio did not become ready")
        webbrowser.open(url)
        print(f"Cloud Edition is running at {url}")
        print("Close this window or press Ctrl+C to stop the local application.")
        return studio.wait()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        stop(studio)
        stop(comfy)


if __name__ == "__main__":
    raise SystemExit(main())
