from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from kisan_backend.core.config import settings
from kisan_backend.core.exceptions import AppBaseException
from kisan_backend.api.v1.endpoints import auth, user, location
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
app.add_middleware(DeviceMetadataMiddleware)

# --- Routes ---

app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(location.router, prefix=settings.API_V1_STR)

from kisan_backend.core.messages import ResponseMessages

# --- Exception Handlers ---

@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    # Debug print for app exceptions
    print(f"[DEBUG] AppBaseException: status={exc.status_code}, message={exc.message}")
    return ErrorResponse(
        status_code=exc.status_code,
        message=exc.message
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Debug print for validation errors
    print(f"[DEBUG] Validation Error: {exc.errors()}")
    return ErrorResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=ResponseMessages.VALIDATION_ERROR
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    import traceback
    # Error logging for unhandled exceptions
    print(f"[ERROR] Unhandled exception: {exc}")
    traceback.print_exc()
    return ErrorResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=ResponseMessages.INTERNAL_SERVER_ERROR
    )

@app.get("/")
async def root():
    return SuccessResponse(message="Welcome to Kisan Backend API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
