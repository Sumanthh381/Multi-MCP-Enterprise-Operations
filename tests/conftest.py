import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def services(tmp_path_factory):
    """Own isolated service ports and persistence for this test run."""
    temp = tmp_path_factory.mktemp("services")
    env = {
        **os.environ,
        "ALARM_API_BASE_URL": "http://127.0.0.1:18000",
        "DATA_PATH": str(temp / "data.sqlite3"),
        "RAG_INDEX_PATH": str(temp / "index.json"),
    }
    processes = []
    handles = []
    try:
        for module, port in (("enterprise.simulator", 18000), ("enterprise.backend", 18080)):
            handle = open(temp / f"{port}.log", "w")
            handles.append(handle)
            p = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", module + ":app", "--port", str(port)],
                env=env,
                cwd=ROOT,
                stdout=handle,
                stderr=handle,
            )
            processes.append(p)
            for _ in range(150):
                if p.poll() is not None:
                    raise RuntimeError((temp / f"{port}.log").read_text())
                try:
                    r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
                    if r.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Service failed readiness")
        yield {"api": "http://127.0.0.1:18000", "backend": "http://127.0.0.1:18080", "env": env}
    finally:
        for p in reversed(processes):
            p.terminate()
        for p in processes:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        for h in handles:
            h.close()
