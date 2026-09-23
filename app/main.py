"""FastAPI server: upload an MP4, get an SRT back."""

import shutil
import tempfile
import threading
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from . import transcribe as tx
from .srt import LANDSCAPE, PORTRAIT, group_words, to_srt

HOST, PORT = "127.0.0.1", 8000
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Video to SRT")


@dataclass
class Job:
    id: str
    filename: str
    video: Path
    max_words: int | None
    layout: str  # auto | vertical | horizontal
    status: str = "queued"  # queued | downloading-model | extracting | transcribing | done | error
    error: str | None = None
    srt: str | None = None
    caption_count: int = 0
    started: float = field(default_factory=time.time)
    finished: float | None = None


jobs: dict[str, Job] = {}
gpu_lock = threading.Lock()  # one transcription at a time


def _run(job: Job) -> None:
    workdir = job.video.parent
    try:
        with gpu_lock:
            job.status = "extracting"
            wav = workdir / "audio.wav"
            tx.extract_audio(job.video, wav)
            vertical = job.layout == "vertical" or (job.layout == "auto" and tx.is_portrait(job.video))
            job.status = "transcribing" if tx.model_is_cached() else "downloading-model"
            words = tx.transcribe(wav)
        captions = group_words(words, job.max_words, PORTRAIT if vertical else LANDSCAPE)
        job.srt = to_srt(captions)
        job.caption_count = len(captions)
        job.status = "done"
    except Exception as e:
        job.status = "error"
        job.error = str(e)
    finally:
        job.finished = time.time()
        shutil.rmtree(workdir, ignore_errors=True)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/jobs")
def create_job(
    file: UploadFile = File(...),
    max_words: int | None = Form(None),
    layout: str = Form("auto"),
) -> dict:
    name = file.filename or "video.mp4"
    if not name.lower().endswith(".mp4"):
        raise HTTPException(400, "Only .mp4 files are supported.")
    if max_words is not None and not 1 <= max_words <= 30:
        raise HTTPException(400, "Max words per caption must be between 1 and 30.")
    if layout not in ("auto", "vertical", "horizontal"):
        raise HTTPException(400, "Layout must be auto, vertical or horizontal.")

    workdir = Path(tempfile.mkdtemp(prefix="video-to-srt-"))
    video = workdir / "input.mp4"
    with video.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    job = Job(id=uuid.uuid4().hex, filename=name, video=video, max_words=max_words, layout=layout)
    jobs[job.id] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": job.id}


def _get(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = _get(job_id)
    end = job.finished or time.time()
    return {
        "status": job.status,
        "error": job.error,
        "elapsed": round(end - job.started, 1),
        "captions": job.caption_count,
        "preview": job.srt[:1200] if job.srt else None,
    }


@app.get("/api/jobs/{job_id}/srt")
def job_srt(job_id: str) -> Response:
    job = _get(job_id)
    if job.status != "done" or job.srt is None:
        raise HTTPException(409, "Subtitles are not ready yet.")
    out_name = Path(job.filename).stem + ".srt"
    return Response(
        job.srt,
        media_type="application/x-subrip; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(out_name)}"},
    )


def run() -> None:
    import uvicorn

    url = f"http://{HOST}:{PORT}"
    print(f"Video to SRT running at {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
