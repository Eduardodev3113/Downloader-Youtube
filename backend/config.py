import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("STUDIO_DATA_DIR", BASE_DIR / "data")).resolve()
INBOX_DIR = DATA_DIR / "inbox"
OUTPUT_DIR = DATA_DIR / "outputs"
DB_PATH = DATA_DIR / "studio.sqlite3"
MAX_UPLOAD_BYTES = int(os.getenv("STUDIO_MAX_UPLOAD_BYTES", str(2 * 1024**3)))
WORKER_COUNT = max(1, int(os.getenv("STUDIO_WORKERS", "2")))

for directory in (DATA_DIR, INBOX_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)
