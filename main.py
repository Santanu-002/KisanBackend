from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from kisan_backend.core.config import settings
from kisan_backend.core.exceptions import AppBaseException
from kisan_backend.api.v1.endpoints import auth, user, location, kyc, admin, admin_auth
from kisan_backend.middleware.logging import LoggingMiddleware
from kisan_backend.middleware.device_metadata import DeviceMetadataMiddleware
from kisan_backend.db.session import init_db
from kisan_backend.core.responses import ErrorResponse, SuccessResponse



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    try:
        # Initialize database tables on startup
        await init_db()
        print("[STARTUP] Database initialized successfully.")
    except Exception as e:
        print(f"[STARTUP] Failed to initialize database: {e}")
        
    yield
    # Cleanup on shutdown
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan
)

# --- Middleware ---

app.add_middleware(DeviceMetadataMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(location.router, prefix=settings.API_V1_STR)
app.include_router(kyc.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(admin_auth.router, prefix=settings.API_V1_STR)

from kisan_backend.core.messages import ResponseMessages

# --- Exception Handlers ---

@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    return ErrorResponse(
        status_code=exc.status_code,
        message=exc.message
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return ErrorResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=ResponseMessages.VALIDATION_ERROR
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    # Log the internal error details to the server logs (standard logging preferred in real prod)
    return ErrorResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=ResponseMessages.INTERNAL_SERVER_ERROR
    )

@app.get("/")
async def root():
    return SuccessResponse(message="Welcome to Kisan Backend API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=None, reload=True)
