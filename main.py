import uuid
from typing import Any
from fastapi import FastAPI, Request, status, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from kisan_backend.core.config import settings
from kisan_backend.core.exceptions import AppBaseException, ErrorCode, ErrorType
from kisan_backend.api.v1.endpoints import auth
from kisan_backend.middleware.logging import LoggingMiddleware, logger
from kisan_backend.db.session import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
app.add_middleware(LoggingMiddleware)

# Routes
app.include_router(auth.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    # In a real production app, use migrations (Alembic)
    # await init_db() 
    pass

# Exception Handlers
@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "type": exc.type
            },
            "meta": {"request_id": getattr(request.state, "request_id", None)}
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": ErrorCode.VAL_001,
                "message": str(exc.errors()),
                "type": ErrorType.VALIDATION_ERROR
            },
            "meta": {"request_id": getattr(request.state, "request_id", None)}
        },
    )

@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": ErrorCode.SYS_001,
                "message": "Internal server error",
                "type": ErrorType.SYSTEM_ERROR
            },
            "meta": {"request_id": getattr(request.state, "request_id", None)}
        },
    )

@app.get("/")
async def root():
    return {"message": "Welcome to Kisan Backend API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
