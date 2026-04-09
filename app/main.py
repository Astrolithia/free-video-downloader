import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.parse import router as parse_router
from app.api.download import router as download_router
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

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(static_dir / "index.html"))
