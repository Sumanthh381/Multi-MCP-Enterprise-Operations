import os
from pathlib import Path

ROOT = Path(os.getenv("ENTERPRISE_ROOT", str(Path(__file__).resolve().parents[2])))
API_URL = os.getenv("ALARM_API_BASE_URL", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("ALARM_API_TOKEN", "demo-token")
TIMEOUT = float(os.getenv("API_TIMEOUT_SECONDS", "5"))
DOCUMENTS = Path(os.getenv("DOCUMENT_PATH", str(ROOT / "rag/documents")))
INDEX = Path(os.getenv("RAG_INDEX_PATH", str(ROOT / ".runtime/rag-index.json")))
DATABASE = Path(os.getenv("DATA_PATH", str(ROOT / ".runtime/operations.sqlite3")))
