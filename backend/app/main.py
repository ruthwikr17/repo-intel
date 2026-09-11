from app.database import create_tables
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routes.health import router as health_router

from app.routes.repos import router as repos_router
from app.routes.admin import router as admin_router
from app.routes.pdfs import router as pdfs_router
from app.routes.analytics import router as analytics_router

settings = get_settings()

app = FastAPI(
    title="Repo Intel API",
    description="Repository Analysis and Contribution Matching Platform",
    version="1.0.0",
    debug=settings.debug,
)

import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://repo-intel-gray.vercel.app",
        # Add any other Vercel preview URLs if needed
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Unhandled error: {type(exc).__name__}: {str(exc)}"}
    )

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(repos_router, prefix="/api", tags=["repos"])
app.include_router(admin_router, prefix="/api", tags=["admin"])
app.include_router(pdfs_router, prefix="/api", tags=["pdfs"])
app.include_router(analytics_router, prefix="/api", tags=["analytics"])


@app.on_event("startup")
async def startup():
    await create_tables()
    print(f"Repo Intel API starting in {settings.app_env} mode")


@app.on_event("shutdown")
async def shutdown():
    print("Repo Intel API shutting down")
