import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.parse import router as parse_router
from app.api.download import router as download_router
from app.api.ai import router as ai_router
from app.services.video_service import DOWNLOADS_DIR, cleanup_stale_files

DOWNLOADS_DIR.mkdir(exist_ok=True)


async def _periodic_cleanup(interval: int = 600):
    """Delete downloaded files older than 10 minutes, every *interval* seconds."""
    while True:
        await asyncio.sleep(interval)
        cleanup_stale_files(max_age_seconds=600)


@asynccontextmanager
async def lifespan(application: FastAPI):
    task = asyncio.create_task(_periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(title="FreeVideoDownloader", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(ai_router, prefix="/api")

_dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _dist_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    """Serve Vue SPA build output; fall back to index.html for client-side routing."""
    if not _dist_dir.is_dir():
        return JSONResponse(
            {"detail": "Frontend not built. Run: cd frontend && npm run build"},
            status_code=503,
        )
    candidate = _dist_dir / full_path
    if candidate.is_file():
        return FileResponse(str(candidate))
    return FileResponse(str(_dist_dir / "index.html"))
