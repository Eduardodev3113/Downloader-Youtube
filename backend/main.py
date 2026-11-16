import asyncio
import ipaddress
import json
import mimetypes
import socket
import sqlite3
import uuid
import zipfile
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.config import DATA_DIR, DB_PATH, INBOX_DIR, MAX_UPLOAD_BYTES, OUTPUT_DIR, WORKER_COUNT
from backend.services import data_service, doc_service, downloader_service, image_service, media_service
from backend.services.common import safe_stem

IMAGE_INPUTS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".ico", ".bmp", ".tif", ".tiff", ".svg"}
DOC_INPUTS = {".pdf", ".docx", ".doc", ".odt", ".rtf", ".md", ".txt", ".html"}
DATA_INPUTS = {".csv", ".xlsx", ".json", ".xml", ".yaml", ".yml"}
MEDIA_INPUTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".flac", ".m4a", ".opus", ".ogg", ".aac", ".aiff"}

queue: asyncio.Queue = asyncio.Queue(maxsize=500)
events: dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
cancelled: set[str] = set()
workers: list[asyncio.Task] = []
worker_condition = None
concurrency_limit = WORKER_COUNT
active_workers = 0


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL,
                status TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
                detail TEXT NOT NULL DEFAULT '', output TEXT, error TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, suffix TEXT NOT NULL,
                size INTEGER NOT NULL, media_kind TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        conn.execute(
            "UPDATE jobs SET status='failed', error='Servidor reiniciado durante o processamento.', "
            "detail='Servidor reiniciado durante o processamento.', updated_at=? "
            "WHERE status IN ('queued','running')", (utc_now(),)
        )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def publish(job_id: str, **payload):
    next_id = events[job_id][-1]["id"] + 1 if events[job_id] else 1
    events[job_id].append({"id": next_id, "job_id": job_id, **payload})


def update_job(job_id: str, **values):
    values["updated_at"] = utc_now()
    fields = ", ".join(f"{key}=?" for key in values)
    with db() as conn:
        conn.execute(f"UPDATE jobs SET {fields} WHERE id=?", [*values.values(), job_id])


def detect_kind(name: str, header: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if header.startswith(b"%PDF-") or suffix in DOC_INPUTS:
        return "document"
    if header.startswith(b"\x89PNG") or header.startswith(b"\xff\xd8\xff") or suffix in IMAGE_INPUTS:
        return "image"
    if suffix in DATA_INPUTS:
        return "data"
    if suffix in MEDIA_INPUTS or header[4:8] == b"ftyp" or header.startswith(b"ID3"):
        return "media"
    return "unknown"


def formats_for(kind: str) -> list[str]:
    return {
        "image": sorted(image_service.IMAGE_FORMATS),
        "document": sorted(doc_service.DOC_FORMATS),
        "data": sorted(data_service.FORMATS),
        "media": sorted(media_service.VIDEO | media_service.AUDIO),
        "unknown": [],
    }[kind]


def output_root() -> Path:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='output_folder'").fetchone()
    root = Path(json.loads(row["value"])).expanduser().resolve() if row and json.loads(row["value"]) else OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


class ProcessRequest(BaseModel):
    file_id: str
    target: str
    options: dict = Field(default_factory=dict)


class DownloadRequest(BaseModel):
    url: str
    options: dict = Field(default_factory=dict)


class SettingsRequest(BaseModel):
    output_folder: str = ""
    gpu: bool = False
    concurrency: int = Field(default=WORKER_COUNT, ge=1, le=8)
    cleanup_days: int = Field(default=7, ge=0, le=365)


async def execute_job(job_id: str, payload: dict):
    if job_id in cancelled:
        update_job(job_id, status="cancelled", error="Tarefa cancelada.", detail="Tarefa cancelada.")
        publish(job_id, status="cancelled", progress=0, error="Tarefa cancelada.")
        cancelled.discard(job_id)
        return
    update_job(job_id, status="running", detail="Iniciando processamento")
    publish(job_id, status="running", progress=0, detail="Iniciando processamento")
    output_dir = output_root() / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    def report(progress, detail="Processando"):
        if job_id in cancelled:
            raise RuntimeError("Tarefa cancelada.")
        value = max(0.0, min(1.0, float(progress)))
        update_job(job_id, progress=value, detail=detail)
        publish(job_id, status="running", progress=value, detail=detail)

    try:
        if payload["kind"] == "download":
            result = await asyncio.to_thread(
                downloader_service.download, payload["url"], output_dir,
                payload["options"], lambda data: report(
                    data.get("downloaded_bytes", 0) / max(data.get("total_bytes") or data.get("total_bytes_estimate") or 1, 1),
                    f"Baixando: {data.get('_percent_str', '').strip()}",
                ) if data.get("status") == "downloading" else None,
            )
        else:
            item = payload["file"]
            suffix = Path(item["name"]).suffix.lower()
            target = payload["target"].lower().lstrip(".")
            stem = safe_stem(item["name"])
            output = output_dir / f"{stem}.{target}"
            kind = item["kind"]
            if kind == "merge_pdf":
                import fitz
                merged = fitz.open()
                for input_path in payload["inputs"]:
                    source_doc = fitz.open(input_path)
                    merged.insert_pdf(source_doc)
                    source_doc.close()
                merged.save(output)
                merged.close()
            else:
                source = INBOX_DIR / f"{item['id']}{suffix}"
                if not source.is_file():
                    raise RuntimeError("Arquivo de entrada não encontrado; envie-o novamente.")
                if kind == "image":
                    await asyncio.to_thread(image_service.convert, source, target, output, payload["options"])
                elif kind == "document":
                    await asyncio.to_thread(doc_service.convert, source, target, output, payload["options"])
                elif kind == "data":
                    await asyncio.to_thread(data_service.convert, source, target, output)
                elif kind == "media":
                    if payload["options"].get("extract_frames"):
                        output = output_dir
                    await asyncio.to_thread(media_service.convert, source, target, output, payload["options"])
                else:
                    raise ValueError("Não foi possível identificar um formato de arquivo compatível.")
            if output.exists():
                result = output
            else:
                generated = sorted(path for path in output_dir.iterdir() if path.is_file())
                if not generated:
                    raise RuntimeError("O serviço não produziu arquivos.")
                result = generated[0]
        if job_id in cancelled:
            raise RuntimeError("Tarefa cancelada.")
        output_path = str(result)
        update_job(job_id, status="completed", progress=1, detail="Concluído", output=output_path)
        publish(job_id, status="completed", progress=1, detail="Concluído", output=output_path)
    except Exception as exc:
        was_cancelled = job_id in cancelled
        status = "cancelled" if was_cancelled else "failed"
        message = "Tarefa cancelada." if was_cancelled else str(exc)
        update_job(job_id, status=status, error=message, detail=message)
        publish(job_id, status=status, error=message, detail=message)
    finally:
        cancelled.discard(job_id)


async def worker():
    global active_workers
    while True:
        job_id, payload = await queue.get()
        acquired = False
        try:
            async with worker_condition:
                while active_workers >= concurrency_limit:
                    await worker_condition.wait()
                active_workers += 1
                acquired = True
            await execute_job(job_id, payload)
        finally:
            if acquired:
                async with worker_condition:
                    active_workers -= 1
                    worker_condition.notify_all()
            queue.task_done()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global worker_condition, concurrency_limit
    initialize_db()
    worker_condition = asyncio.Condition()
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='concurrency'").fetchone()
    if row:
        concurrency_limit = max(1, min(8, int(json.loads(row["value"]))))
    for _ in range(8):
        workers.append(asyncio.create_task(worker()))
    yield
    for task in workers:
        task.cancel()
    await asyncio.gather(*workers, return_exceptions=True)


app = FastAPI(title="Universal Media & File Converter Studio", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"ok": True, "workers": WORKER_COUNT}


@app.post("/api/files")
async def upload_files(files: list[UploadFile] = File(...)):
    response = []
    for upload in files:
        name = Path(upload.filename or "upload.bin").name
        suffix = Path(name).suffix.lower()
        file_id = str(uuid.uuid4())
        destination = INBOX_DIR / f"{file_id}{suffix}"
        size = 0
        with destination.open("wb") as target:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    destination.unlink(missing_ok=True)
                    raise HTTPException(413, f"{name}: limite de upload excedido.")
                target.write(chunk)
        with destination.open("rb") as saved:
            header = saved.read(32)
        kind = detect_kind(name, header)
        if kind == "unknown":
            destination.unlink(missing_ok=True)
            continue
        created = utc_now()
        with db() as conn:
            conn.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
                         (file_id, name, suffix, size, kind, created))
        response.append({"id": file_id, "name": name, "size": size, "kind": kind,
                         "mime": mimetypes.guess_type(name)[0] or "application/octet-stream",
                         "formats": formats_for(kind)})
    if not response:
        raise HTTPException(415, "Nenhum arquivo em formato compatível foi encontrado.")
    return {"files": response}


def new_job(title: str, kind: str, payload: dict) -> dict:
    if queue.full():
        raise HTTPException(429, "A fila está cheia; tente novamente em instantes.")
    job_id = str(uuid.uuid4())
    now = utc_now()
    with db() as conn:
        conn.execute(
            "INSERT INTO jobs (id,title,kind,status,progress,detail,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (job_id, title, kind, "queued", 0, "Na fila", now, now),
        )
    publish(job_id, status="queued", progress=0, detail="Na fila")
    queue.put_nowait((job_id, payload))
    return {"id": job_id, "title": title, "kind": kind, "status": "queued", "progress": 0}


@app.post("/api/jobs/process")
async def process_file(request: ProcessRequest):
    try:
        uuid.UUID(request.file_id)
    except ValueError as exc:
        raise HTTPException(400, "Identificador de arquivo inválido.") from exc
    with db() as conn:
        row = conn.execute("SELECT * FROM files WHERE id=?", (request.file_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Arquivo não encontrado.")
    if request.target.lower().lstrip(".") not in formats_for(row["media_kind"]):
        raise HTTPException(400, "Formato de saída não compatível com este arquivo.")
    item = dict(row)
    return new_job(f"{row['name']} → {request.target.upper()}", "convert",
                   {"kind": "convert", "file": item, "target": request.target, "options": request.options})


@app.post("/api/jobs/download")
async def download_media(request: DownloadRequest):
    downloader_service.validate_url(request.url)
    title = urlparse(request.url).hostname or "Download"
    return new_job(title, "download", {"kind": "download", "url": request.url, "options": request.options})


class MergeRequest(BaseModel):
    file_ids: list[str] = Field(min_length=2, max_length=50)


@app.post("/api/jobs/pdf/merge")
async def merge_pdfs(request: MergeRequest):
    sources = []
    with db() as conn:
        for file_id in request.file_ids:
            try:
                uuid.UUID(file_id)
            except ValueError as exc:
                raise HTTPException(400, "Identificador de arquivo inválido.") from exc
            row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
            if not row or row["suffix"] != ".pdf":
                raise HTTPException(400, "Todos os arquivos devem ser PDFs enviados nesta sessão.")
            sources.append(str(INBOX_DIR / f"{row['id']}.pdf"))
    name = f"Juntar {len(sources)} PDFs"
    payload = {"kind": "convert", "file": {"id": "merge", "name": "merged.pdf", "kind": "merge_pdf"},
               "target": "pdf", "options": {}, "inputs": sources}
    return new_job(name, "convert", payload)


@app.get("/api/jobs")
async def list_jobs():
    with db() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall()
    return {"jobs": [dict(row) for row in rows]}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str):
    with db() as conn:
        exists = conn.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not exists:
        raise HTTPException(404, "Tarefa não encontrada.")

    async def stream():
        sent = 0
        if not events[job_id]:
            with db() as conn:
                initial = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if initial:
                snapshot = dict(initial)
                yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                if snapshot["status"] in ("completed", "failed", "cancelled"):
                    return
        while True:
            backlog = list(events[job_id])
            for event in backlog:
                if event["id"] <= sent:
                    continue
                yield f"id: {event['id']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                sent = event["id"]
                if event.get("status") in ("completed", "failed", "cancelled"):
                    return
            with db() as conn:
                row = conn.execute("SELECT status,progress,detail,error,output FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row and row["status"] in ("completed", "failed", "cancelled") and sent == 0:
                yield f"data: {json.dumps(dict(row), ensure_ascii=False)}\n\n"
                return
            yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    with db() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Tarefa não encontrada.")
    if row["status"] == "queued":
        cancelled.add(job_id)
    elif row["status"] == "running":
        cancelled.add(job_id)
    return {"ok": True}


@app.get("/api/jobs/{job_id}/output")
async def get_output(job_id: str):
    with db() as conn:
        row = conn.execute("SELECT output,status FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not row or row["status"] != "completed" or not row["output"]:
        raise HTTPException(404, "Arquivo final ainda não está disponível.")
    output = Path(row["output"]).resolve()
    root = output_root()
    if root not in output.parents or not output.is_file():
        raise HTTPException(404, "Arquivo final não encontrado.")
    return FileResponse(output, filename=output.name)


@app.get("/api/outputs.zip")
async def download_all_outputs():
    root = output_root()
    zip_path = DATA_DIR / f"studio-{uuid.uuid4()}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() != ".zip":
                archive.write(path, path.relative_to(root))
    return FileResponse(zip_path, filename="studio-outputs.zip")


@app.get("/api/history")
async def history():
    with db() as conn:
        rows = conn.execute("SELECT * FROM jobs WHERE status='completed' ORDER BY updated_at DESC LIMIT 100").fetchall()
    return {"items": [dict(row) for row in rows]}


@app.get("/api/settings")
async def get_settings():
    with db() as conn:
        rows = conn.execute("SELECT key,value FROM settings").fetchall()
    result = {"output_folder": "", "gpu": False, "concurrency": WORKER_COUNT, "cleanup_days": 7}
    for row in rows:
        result[row["key"]] = json.loads(row["value"])
    return result


@app.put("/api/settings")
async def save_settings(request: SettingsRequest):
    global concurrency_limit
    folder = request.output_folder.strip()
    if folder:
        path = Path(folder).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        folder = str(path)
    values = request.model_dump()
    values["output_folder"] = folder
    with db() as conn:
        conn.executemany("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)",
                         [(key, json.dumps(value)) for key, value in values.items()])
    concurrency_limit = request.concurrency
    async with worker_condition:
        worker_condition.notify_all()
    return values
