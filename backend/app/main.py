from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, collections, dashboard, diagrams, graph, jobs, lint, pages, query, review, saved_views, settings as runtime_settings, sources
from app.config import settings
from app.core.bootstrap import init_database
from app.core.health import readiness_payload, validate_startup_config
from app.core.ingest import ensure_upload_dir
from app.core.observability import RequestIdMiddleware, configure_structured_logging
from app.db.database import SessionLocal

configure_structured_logging()
app = FastAPI(
    title="LLM Wiki API",
    description="Backend API for the LLM Wiki / AI Knowledge Base platform",
    version="0.1.0",
)
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=ensure_upload_dir()), name="uploads")


@app.on_event("startup")
def on_startup():
    config_status = validate_startup_config()
    if not config_status["ok"]:
        raise RuntimeError("; ".join(config_status["errors"]))
    db = SessionLocal()
    try:
        init_database(db, seed_demo_data=settings.AUTO_SEED_DEMO_DATA)
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/ready")
def readiness_check():
    return readiness_payload()


app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(diagrams.router, prefix="/api/diagrams", tags=["Diagrams"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(pages.router, prefix="/api/pages", tags=["Pages"])
app.include_router(review.router, prefix="/api/review-items", tags=["Review"])
app.include_router(saved_views.router, prefix="/api/saved-views", tags=["Saved Views"])
app.include_router(query.router, prefix="/api", tags=["Query"])
app.include_router(graph.router, prefix="/api", tags=["Graph"])
app.include_router(lint.router, prefix="/api", tags=["Lint"])
app.include_router(runtime_settings.router, prefix="/api", tags=["Settings"])
