"""FastAPI service. Bind only to 127.0.0.1 with Uvicorn."""
from __future__ import annotations

import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.speech import speech_status, synthesize_wav
from backend.demo import demo_events

ROOT=Path(__file__).resolve().parents[1]
recognizer = None
MAX_UPLOAD = 100 * 1024 * 1024
SAMPLES = ROOT / "research" / "samples"


@asynccontextmanager
async def lifespan(app):
    global recognizer
    if recognizer is not None:
        await run_in_threadpool(recognizer.load)
    yield
    if recognizer is not None:
        recognizer.close()


app = FastAPI(title="Kamayan local ASL studio", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:4173", "http://localhost:4173"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.middleware("http")
async def strip_api_prefix(request: Request, call_next):
    path = request.scope["path"]
    if path == "/api" or path.startswith("/api/"):
        request.scope["path"] = path[4:] or "/"
    return await call_next(request)


@app.get("/health")
def health():
    return {"status":"ok","offline":True,"service":"kamayan","model_ready":recognizer.ready if recognizer else True,"mode":"ai" if recognizer else "demo"}


@app.get("/model-status")
def model_status():
    if recognizer:
        return recognizer.status()
    return {'ready':True,'mode':'demo','model':'Exact sample reference captions','device':'No AI inference','sentence_translation':False,'offline':True,'scope':'Static reference captions for the exact sentence sample.','license_note':'How2Sign sample: CC BY-NC 4.0, research/noncommercial use.','error':None}


@app.get("/vocabulary")
def vocabulary():
    return {"labels":recognizer.model.labels if recognizer and recognizer.model else []}


@app.get("/performance")
def performance():
    return {"model_load_ms":recognizer.load_ms if recognizer else 0,"last_result":recognizer.last_result if recognizer else None,"device":"CPU" if recognizer else 'No AI inference'}


async def process_upload(file: UploadFile, start: float, end: float | None):
    if recognizer is None:
        raise HTTPException(503,'AI recognition is disabled. The app is using the static sentence demo.')
    from backend.runtime import VideoError
    if not recognizer.ready:
        raise HTTPException(503, recognizer.error or "Local model unavailable. Run setup.ps1.")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".webm"}:
        raise HTTPException(400, "Upload an MP4 or WebM video.")
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix="kamayan-", suffix=suffix, delete=False) as stream:
            path = Path(stream.name)
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, "The video must be smaller than 100 MB.")
                stream.write(chunk)
        if size == 0:
            raise HTTPException(400, "The uploaded video is empty.")
        return await run_in_threadpool(recognizer.recognize, path, start, end)
    except VideoError as exc:
        raise HTTPException(400, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Local processing failed. Try a shorter MP4 with visible hands.") from exc
    finally:
        await file.close()
        if path is not None:
            path.unlink(missing_ok=True)


@app.post("/recognize-video")
async def recognize_video(file: UploadFile = File(...), start: float = Form(0, ge=0), end: float | None = Form(None, gt=0)):
    return await process_upload(file, start, end)


@app.post("/recognize-segment")
async def recognize_segment(file: UploadFile = File(...), start: float = Form(..., ge=0), end: float = Form(..., gt=0)):
    return await process_upload(file, start, end)


@app.post('/recognize-timeline')
async def recognize_timeline(file: UploadFile = File(...)):
    if recognizer is not None and not recognizer.ready:
        raise HTTPException(503, recognizer.error or 'Local model unavailable.')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in {'.mp4', '.webm'}:
        raise HTTPException(400, 'Upload an MP4 or WebM video.')
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix='kamayan-timeline-', suffix=suffix, delete=False) as stream:
            path = Path(stream.name)
            size = 0
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, 'The video must be smaller than 100 MB.')
                stream.write(chunk)
        if not size:
            raise HTTPException(400, 'The uploaded video is empty.')
        def generate():
            try:
                if recognizer is None:
                    events=demo_events(path)
                else:
                    from backend.timeline import timeline_events
                    events=timeline_events(recognizer,path)
                for event in events:
                    yield json.dumps(event) + '\n'
            except Exception:
                yield json.dumps({'type':'error','message':'Caption loading failed. Try the sentence sample again.'}) + '\n'
            finally:
                path.unlink(missing_ok=True)
        return StreamingResponse(generate(), media_type='application/x-ndjson', headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
    except Exception:
        if path is not None:
            path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


def sample_manifest():
    path = SAMPLES / "manifest.json"
    entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    sentence = SAMPLES / 'sentence_manifest.json'
    if sentence.exists():
        entries = json.loads(sentence.read_text(encoding='utf-8')) + entries
    return entries


@app.get("/samples")
def samples():
    return {"samples": [{**entry, "url": f"/api/samples/{entry['id']}", "reference_only": True} for entry in sample_manifest() if (SAMPLES / entry["path"]).is_file()]}


@app.get("/samples/{sample_id}")
def sample_video(sample_id: str):
    entry = next((entry for entry in sample_manifest() if entry["id"] == sample_id), None)
    if entry is None:
        raise HTTPException(404, "Sample not available.")
    path = (SAMPLES / entry["path"]).resolve()
    if path.parent != SAMPLES.resolve() or not path.is_file():
        raise HTTPException(404, "Sample not available.")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/speech-status")
async def speech_model_status():
    return await run_in_threadpool(speech_status)


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    voice: str | None = None


@app.post("/speech")
async def speak(request: SpeechRequest):
    try:
        audio = await run_in_threadpool(synthesize_wav, request.text, request.rate, request.voice)
        return Response(audio, media_type="audio/wav", headers={"Content-Disposition": 'attachment; filename="kamayan-speech.wav"', "Cache-Control": "no-store"})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")
