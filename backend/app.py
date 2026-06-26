"""
PanoSync FastAPI application.
"""

import asyncio
import hashlib
import json
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import storage
from .session import new_session_id, save_session, load_session, update_session
from .registration import compute_transform, initial_transform
from .pyramid import generate_dzi

try:
    from .version import __version__
except Exception:
    __version__ = "unknown"

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"

# Retention for the startup cleanup of stale sessions/tiles/uploads (hours).
CLEANUP_MAX_AGE_HOURS = 24

# Create the cloud-sync-safe data dirs before anything mounts or serves them.
storage.ensure_dirs()


def _calibration_key(name_a: str, name_b: str) -> str:
    """Stable key derived from the two original filenames."""
    return hashlib.md5(f"{name_a}|||{name_b}".encode()).hexdigest()[:16]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # The server starts fresh on every launch → ideal point to reclaim disk and
    # keep the data dir bounded (guards against the historic tile flood).
    storage.ensure_dirs()

    # One-time: remove the old in-program data/ folder (the lingering cloud
    # "tile flood" source). Calibrations are rescued first; the deletion happens
    # at the source so the user's own sync client propagates it to the cloud.
    migration = storage.migrate_legacy_data(BASE_DIR)
    if migration["removed"]:
        print(
            f"[PanoSync] Migration: alter Daten-Ordner im Programmverzeichnis entfernt "
            f"({migration['calibrations_migrated']} Kalibrierung(en) gesichert). "
            f"Lag der Ordner in einem Cloud-Sync-Ordner, wird das Löschen jetzt nach oben synchronisiert."
        )

    report = storage.cleanup_stale(max_age_hours=CLEANUP_MAX_AGE_HOURS)
    print(f"[PanoSync] data dir: {storage.data_root()} | startup cleanup removed {report}")
    synced = storage.is_cloud_synced(BASE_DIR)
    if synced:
        print(
            f"[PanoSync] WARNUNG: Der Programmordner liegt in einem Cloud-Sync-Ordner "
            f"('{synced}'). Die erzeugten Daten sind sicher (sie liegen unter "
            f"{storage.data_root()} und werden NICHT gesynct) — lege das Programm "
            f"selbst aber besser AUSSERHALB von OneDrive/iCloud/Dropbox ab."
        )
    print(f"[PanoSync] Version {__version__}")
    yield


app = FastAPI(title="PanoSync", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/tiles", StaticFiles(directory=str(storage.tiles_dir())), name="tiles")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ── In-memory processing status ──────────────────────────────────────────────
processing_status: dict[str, dict] = {}


# ── Pages ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def page_upload(request: Request):
    return templates.TemplateResponse(request=request, name="upload.html", context={"request": request})


@app.get("/hilfe", response_class=HTMLResponse)
async def page_hilfe(request: Request):
    import markdown as md
    candidates = [
        BASE_DIR / "README-Anleitung.md",
        Path.cwd() / "README-Anleitung.md",
        Path(__file__).resolve().parent.parent / "README-Anleitung.md",
    ]
    readme_path = next((p for p in candidates if p.exists()), None)
    if readme_path:
        content_html = md.markdown(readme_path.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
    else:
        content_html = f"<p style='color:#c66117'>README nicht gefunden. Gesuchte Pfade:</p><ul>{''.join(f'<li><code>{p}</code></li>' for p in candidates)}</ul>"
    return templates.TemplateResponse(request=request, name="hilfe.html", context={"request": request, "content": content_html})


@app.get("/calibrate/{session_id}", response_class=HTMLResponse)
async def page_calibrate(request: Request, session_id: str):
    session = load_session(session_id)
    if not session:
        return HTMLResponse("Session not found", status_code=404)
    return templates.TemplateResponse(request=request, name="calibrate.html", context={"request": request, "session_id": session_id})


# ── API ───────────────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_images(
    pano_a: UploadFile = File(...),
    pano_b: UploadFile = File(...),
):
    session_id = new_session_id()
    session_dir = storage.uploads_dir() / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    path_a = session_dir / "panoA.png"
    path_b = session_dir / "panoB.png"

    with open(path_a, "wb") as f:
        shutil.copyfileobj(pano_a.file, f)
    with open(path_b, "wb") as f:
        shutil.copyfileobj(pano_b.file, f)

    # Check for previously saved calibration for these filenames
    name_a = pano_a.filename or "panoA"
    name_b = pano_b.filename or "panoB"
    calib_key = _calibration_key(name_a, name_b)
    calib_dir = storage.calibrations_dir()
    calib_dir.mkdir(parents=True, exist_ok=True)
    calib_file = calib_dir / f"{calib_key}.json"

    restored_pairs = []
    restored_transform = None
    calibration_restored = False
    if calib_file.exists():
        try:
            saved = json.loads(calib_file.read_text())
            restored_pairs = saved.get("pairs", [])
            restored_transform = saved.get("transform", None)
            calibration_restored = bool(restored_pairs)
        except Exception:
            pass  # corrupt file — ignore

    # Save initial session state
    save_session(session_id, {
        "status": "uploaded",
        "pano_a": str(path_a),
        "pano_b": str(path_b),
        "orig_name_a": name_a,
        "orig_name_b": name_b,
        "calib_key": calib_key,
        "pairs": restored_pairs,
        "transform": restored_transform,
        "calibration_restored": calibration_restored,
    })

    processing_status[session_id] = {"step": "uploaded", "progress": 0, "error": None}

    # Start background processing
    asyncio.create_task(_process_session(session_id, str(path_a), str(path_b)))

    return {"session_id": session_id}


async def _process_session(session_id: str, path_a: str, path_b: str):
    """Generate DZI pyramids and compute initial transform."""
    try:
        tiles_a_dir = storage.tiles_dir() / session_id / "panoA"
        tiles_b_dir = storage.tiles_dir() / session_id / "panoB"
        tiles_a_dir.mkdir(parents=True, exist_ok=True)
        tiles_b_dir.mkdir(parents=True, exist_ok=True)

        processing_status[session_id] = {"step": "tiling_a", "progress": 10, "error": None}
        loop = asyncio.get_event_loop()

        result_a = await loop.run_in_executor(None, generate_dzi, path_a, str(tiles_a_dir))
        processing_status[session_id] = {"step": "tiling_b", "progress": 55, "error": None}

        result_b = await loop.run_in_executor(None, generate_dzi, path_b, str(tiles_b_dir))
        processing_status[session_id] = {"step": "computing_transform", "progress": 90, "error": None}

        initial_t = initial_transform(
            result_a["width"], result_a["height"],
            result_b["width"], result_b["height"],
        )

        # Preserve restored calibration if present; only use initial_t as fallback
        current = load_session(session_id) or {}
        if current.get("calibration_restored") and current.get("transform"):
            transform = current["transform"]
        else:
            transform = initial_t

        # Generate 5 evenly-distributed reference point suggestions
        wa, ha = result_a["width"], result_a["height"]
        suggestions = []
        positions = [
            (0.15, 0.5), (0.35, 0.25), (0.5, 0.75), (0.65, 0.25), (0.85, 0.5)
        ]
        for fx, fy in positions:
            ax = wa * fx
            ay = ha * fy
            bx = transform["a"] * ax + transform["b"] * ay + transform["tx"]
            by = transform["c"] * ax + transform["d"] * ay + transform["ty"]
            suggestions.append({"ax": ax, "ay": ay, "bx": bx, "by": by})

        update_session(session_id, {
            "status": "ready",
            "width_a": result_a["width"],
            "height_a": result_a["height"],
            "width_b": result_b["width"],
            "height_b": result_b["height"],
            "transform": transform,
            "suggestions": suggestions,
        })

        processing_status[session_id] = {"step": "ready", "progress": 100, "error": None}

    except Exception as e:
        import traceback
        traceback.print_exc()
        processing_status[session_id] = {"step": "error", "progress": 0, "error": str(e)}
        update_session(session_id, {"status": "error", "error": str(e)})


@app.get("/api/status/{session_id}")
async def get_status(session_id: str):
    status = processing_status.get(session_id, {"step": "unknown", "progress": 0, "error": None})
    return status


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


class CalibrationRequest(BaseModel):
    pairs: List[dict]


@app.post("/api/calibrate/{session_id}")
async def calibrate(session_id: str, body: CalibrationRequest):
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if len(body.pairs) < 3:
        raise HTTPException(status_code=400, detail="Need at least 3 point pairs for affine transform")

    img_size_a = (session.get("width_a"), session.get("height_a"))
    img_size_b = (session.get("width_b"), session.get("height_b"))
    transform = compute_transform(body.pairs, img_size_a=img_size_a, img_size_b=img_size_b)
    update_session(session_id, {"transform": transform, "pairs": body.pairs})
    return {"transform": transform}


@app.post("/api/calibration/persist/{session_id}")
async def persist_calibration(session_id: str):
    """Save the current calibration keyed by original filenames so it can be restored on re-upload."""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    calib_key = session.get("calib_key")
    if not calib_key:
        raise HTTPException(status_code=400, detail="No calibration key — session predates this feature")
    pairs = session.get("pairs", [])
    transform = session.get("transform")
    calib_dir = storage.calibrations_dir()
    calib_dir.mkdir(parents=True, exist_ok=True)
    calib_file = calib_dir / f"{calib_key}.json"
    calib_file.write_text(json.dumps({
        "orig_name_a": session.get("orig_name_a", ""),
        "orig_name_b": session.get("orig_name_b", ""),
        "pairs": pairs,
        "transform": transform,
    }, indent=2))
    return {"ok": True, "pairs_saved": len(pairs)}


def inject_version(request: Request):
    return {"version": __version__}


templates.context_processors.append(inject_version)
