import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as chat_router
from app.schemas.contract import ErrorResponse

# Configure structured application logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("project_partner")

app = FastAPI(
    title="Project Partner Backend API",
    description="Collaborative Partner AI Backend built with Google ADK, Gemini, FastAPI, and Firestore.",
    version="1.0.0",
)

# Enable CORS for frontend integration (Next.js, React, Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# GLOBAL EXCEPTION HANDLERS (Standardized Error Envelope)
# -----------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles malformed or missing request body parameters."""
    sanitized_errors = jsonable_encoder(exc.errors())
    error_payload = ErrorResponse(
        error="validation_error",
        message="Request payload validation failed. Check request fields.",
        detail=sanitized_errors,
        status_code=422,
    )
    return JSONResponse(
        status_code=422,
        content=error_payload.model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles explicit HTTP exceptions thrown by routes and services."""
    error_payload = ErrorResponse(
        error="http_error",
        message=str(exc.detail),
        detail=None,
        status_code=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all exception handler.
    Logs the raw exception and stack trace securely on the server,
    while returning a sanitized error envelope to the client.
    """
    logger.error(f"Unhandled server exception on {request.url}: {str(exc)}", exc_info=True)
    error_payload = ErrorResponse(
        error="internal_server_error",
        message="An unexpected server error occurred. Please retry your request.",
        detail=None,
        status_code=500,
    )
    return JSONResponse(
        status_code=500,
        content=error_payload.model_dump(mode="json"),
    )


# Mount router
app.include_router(chat_router)


@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "service": "Project Partner Backend"}
