"""Start simulator and UI/backend; backend owns its two stdio MCP subprocesses."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
processes = []


def stop(*_):
    for p in reversed(processes):
        p.terminate()
    for p in processes:
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.kill()


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "enterprise.simulator:app",
                    "--host",
                    "0.0.0.0" if os.getenv("CONTAINER") else "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT,
            )
        )
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:8000/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Simulator did not become healthy")
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "enterprise.backend:app",
                    "--host",
                    os.getenv("COPILOT_HOST", "127.0.0.1"),
                    "--port",
                    os.getenv("COPILOT_PORT", "8080"),
                ],
                cwd=ROOT,
            )
        )
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        if any(p.returncode not in (0, None) for p in processes):
            raise SystemExit(1)
    finally:
        stop()


if __name__ == "__main__":
    main()
