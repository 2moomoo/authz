"""Internal LLM API Server - Main application."""
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import config, APIKeyInfo
from .auth import verify_api_key
from .rate_limiter import rate_limiter
from .logger import app_logger as logger, log_request
from .models import (
    CompletionRequest,
    CompletionResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    HealthResponse,
)
from .vllm_client import vllm_client


# Prometheus metrics
REQUEST_COUNT = Counter(
    "api_requests_total",
    "Total API requests",
    ["endpoint", "method", "status"],
)
REQUEST_DURATION = Histogram(
    "api_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint", "method"],
)
TOKEN_COUNT = Counter(
    "api_tokens_total",
    "Total tokens processed",
    ["type", "user"],  # type: prompt or completion
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Internal LLM API Server")
    logger.info(f"vLLM backend: {config.vllm.base_url}")
    logger.info(f"Default model: {config.vllm.default_model}")
    logger.info(f"Loaded {len(config.api_keys)} API keys")

    # Check vLLM connection
    is_healthy = await vllm_client.health_check()
    if is_healthy:
        logger.info("vLLM backend is healthy")
    else:
        logger.warning("vLLM backend health check failed - requests may fail")

    yield

    # Cleanup
    logger.info("Shutting down Internal LLM API Server")
    await vllm_client.close()


# Create FastAPI app
app = FastAPI(
    title="Internal LLM API Server",
    description="OpenAI-compatible API for internal LLM models",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
if config.server.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request timing and logging."""
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000  # Convert to ms

        response.headers["X-Process-Time"] = str(round(process_time, 2))

        # Record metrics
        REQUEST_COUNT.labels(
            endpoint=request.url.path,
            method=request.method,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            endpoint=request.url.path,
            method=request.method,
        ).observe(process_time / 1000)  # Record in seconds

        return response

    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        REQUEST_COUNT.labels(
            endpoint=request.url.path,
            method=request.method,
            status=500,
        ).inc()

        logger.error(f"Request failed: {str(e)}")
        raise


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    vllm_healthy = await vllm_client.health_check()

    return HealthResponse(
        status="healthy" if vllm_healthy else "degraded",
        version="1.0.0",
        model=config.vllm.default_model,
        vllm_status="connected" if vllm_healthy else "disconnected",
    )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not config.monitoring.prometheus_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics endpoint is disabled",
        )

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# List models endpoint
@app.get("/v1/models")
async def list_models(user_info: APIKeyInfo = Depends(verify_api_key)):
    """List available models."""
    try:
        # Check rate limit
        rate_limiter.check_rate_limit(user_info)

        models_response = await vllm_client.models()
        return models_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models list",
        )


# Completions endpoint
@app.post("/v1/completions", response_model=CompletionResponse)
async def create_completion(
    request_body: CompletionRequest,
    request: Request,
    user_info: APIKeyInfo = Depends(verify_api_key),
):
    """Create a text completion."""
    start_time = time.time()
    response_body = None
    error = None

    try:
        # Check rate limit
        rate_limiter.check_rate_limit(user_info)

        # Add rate limit headers to response
        minute_limit, minute_remaining, hour_limit, hour_remaining = (
            rate_limiter.get_rate_limit_status(user_info)
        )

        # Forward request to vLLM
        request_dict = request_body.model_dump(exclude_none=True)

        # Use default model if not specified or override for internal routing
        if not request_dict.get("model"):
            request_dict["model"] = config.vllm.default_model

        response_body = await vllm_client.completions(request_dict)

        # Track token usage
        if response_body.get("usage"):
            usage = response_body["usage"]
            TOKEN_COUNT.labels(type="prompt", user=user_info.user_id).inc(
                usage.get("prompt_tokens", 0)
            )
            TOKEN_COUNT.labels(type="completion", user=user_info.user_id).inc(
                usage.get("completion_tokens", 0)
            )

        # Log request
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/completions",
            method="POST",
            request_body=request_dict,
            response_body=response_body,
            status_code=200,
            duration_ms=duration_ms,
        )

        # Add custom headers
        headers = {
            "X-RateLimit-Limit-Minute": str(minute_limit),
            "X-RateLimit-Remaining-Minute": str(minute_remaining),
            "X-RateLimit-Limit-Hour": str(hour_limit),
            "X-RateLimit-Remaining-Hour": str(hour_remaining),
        }

        return JSONResponse(content=response_body, headers=headers)

    except HTTPException as e:
        error = e.detail
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/completions",
            method="POST",
            request_body=request_body.model_dump(exclude_none=True),
            status_code=e.status_code,
            duration_ms=duration_ms,
            error=error,
        )
        raise

    except Exception as e:
        error = str(e)
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/completions",
            method="POST",
            request_body=request_body.model_dump(exclude_none=True),
            status_code=500,
            duration_ms=duration_ms,
            error=error,
        )
        logger.error(f"Completion request failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing completion request",
        )


# Chat completions endpoint
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request_body: ChatCompletionRequest,
    request: Request,
    user_info: APIKeyInfo = Depends(verify_api_key),
):
    """Create a chat completion."""
    start_time = time.time()
    response_body = None
    error = None

    try:
        # Check rate limit
        rate_limiter.check_rate_limit(user_info)

        # Add rate limit headers to response
        minute_limit, minute_remaining, hour_limit, hour_remaining = (
            rate_limiter.get_rate_limit_status(user_info)
        )

        # Forward request to vLLM
        request_dict = request_body.model_dump(exclude_none=True)

        # Use default model if not specified or override for internal routing
        if not request_dict.get("model"):
            request_dict["model"] = config.vllm.default_model

        response_body = await vllm_client.chat_completions(request_dict)

        # Track token usage
        if response_body.get("usage"):
            usage = response_body["usage"]
            TOKEN_COUNT.labels(type="prompt", user=user_info.user_id).inc(
                usage.get("prompt_tokens", 0)
            )
            TOKEN_COUNT.labels(type="completion", user=user_info.user_id).inc(
                usage.get("completion_tokens", 0)
            )

        # Log request
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/chat/completions",
            method="POST",
            request_body=request_dict,
            response_body=response_body,
            status_code=200,
            duration_ms=duration_ms,
        )

        # Add custom headers
        headers = {
            "X-RateLimit-Limit-Minute": str(minute_limit),
            "X-RateLimit-Remaining-Minute": str(minute_remaining),
            "X-RateLimit-Limit-Hour": str(hour_limit),
            "X-RateLimit-Remaining-Hour": str(hour_remaining),
        }

        return JSONResponse(content=response_body, headers=headers)

    except HTTPException as e:
        error = e.detail
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/chat/completions",
            method="POST",
            request_body=request_body.model_dump(exclude_none=True),
            status_code=e.status_code,
            duration_ms=duration_ms,
            error=error,
        )
        raise

    except Exception as e:
        error = str(e)
        duration_ms = (time.time() - start_time) * 1000
        log_request(
            user_id=user_info.user_id,
            endpoint="/v1/chat/completions",
            method="POST",
            request_body=request_body.model_dump(exclude_none=True),
            status_code=500,
            duration_ms=duration_ms,
            error=error,
        )
        logger.error(f"Chat completion request failed: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing chat completion request",
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Internal LLM API Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "models": "/v1/models",
            "completions": "/v1/completions",
            "chat_completions": "/v1/chat/completions",
        },
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"message": "Internal server error", "type": "internal_error"}},
    )
