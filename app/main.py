from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous, deterministic AI Software Engineering Agent backend.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Healthcheck endpoint for container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


from pathlib import Path
from fastapi.responses import HTMLResponse, RedirectResponse

@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Interactive visual dashboard for monitoring and running the AI Software Engineering Agent."""
    template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")
    return "<h1>Dashboard template not found.</h1>"


@app.get("/", tags=["Root"])
async def root():
    """Root info endpoint redirecting to dashboard."""
    return RedirectResponse(url="/dashboard")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
