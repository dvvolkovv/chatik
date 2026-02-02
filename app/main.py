"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import auth, chat, profile, llm, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    await close_db()
    print("❌ Database connection closed")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Chat Platform API with multi-model support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Include routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    chat.router,
    prefix=f"{settings.API_V1_PREFIX}/chats",
    tags=["Chats"]
)

app.include_router(
    profile.router,
    prefix=f"{settings.API_V1_PREFIX}/profile",
    tags=["Profile"]
)

app.include_router(
    llm.router,
    prefix=f"{settings.API_V1_PREFIX}/llm",
    tags=["LLM"]
)

app.include_router(
    files.router,
    prefix=f"{settings.API_V1_PREFIX}/files",
    tags=["Files"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Chat Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
