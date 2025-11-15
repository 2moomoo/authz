"""API Gateway - Handles authentication, rate limiting, and routing."""
import sys
import time
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import httpx
from sqlalchemy.orm import Session

from shared.database import get_db, init_db
from shared import crud
from shared.config import settings
from .rate_limiter import RateLimiter
from .auth import verify_api_key, APIKeyInfo

app = FastAPI(title="LLM API Gateway", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
rate_limiter = RateLimiter()

# HTTP client for proxying requests
http_client = httpx.AsyncClient(timeout=300.0)


@app.on_event("startup")
async def startup_event():
    """Initialize database."""
    init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Close HTTP client."""
    await http_client.aclose()


# Middleware for request logging
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log requests and track performance."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000

    # Add timing header
    response.headers["X-Process-Time"] = str(round(duration_ms, 2))

    return response


# Health check
@app.get("/health")
async def health_check():
    """Gateway health check."""
    # Check backend services
    llm_backend_healthy = False
    admin_healthy = False

    # Check LLM backend (try /health first, fallback to /v1/models for vLLM)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try /health endpoint first
            try:
                llm_response = await client.get(f"{settings.llm_backend_url}/health")
                llm_backend_healthy = llm_response.status_code == 200
            except:
                # Fallback to /v1/models for vLLM compatibility
                llm_response = await client.get(f"{settings.llm_backend_url}/v1/models")
                llm_backend_healthy = llm_response.status_code == 200
    except:
        pass

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            admin_response = await client.get(f"http://{settings.admin_host}:{settings.admin_port}/health")
            admin_healthy = admin_response.status_code == 200
    except:
        pass

    return {
        "status": "healthy" if (llm_backend_healthy and admin_healthy) else "degraded",
        "services": {
            "gateway": "healthy",
            "llm_backend": "healthy" if llm_backend_healthy else "unhealthy",
            "admin": "healthy" if admin_healthy else "unhealthy",
        }
    }


# Proxy to LLM Backend with authentication and rate limiting
async def proxy_to_llm_backend(
    request: Request,
    path: str,
    api_key_info: APIKeyInfo,
    db: Session,
):
    """Proxy request to LLM backend with auth and rate limiting."""
    start_time = time.time()

    # Check rate limit
    rate_limiter.check_rate_limit(api_key_info)

    # Get rate limit status for headers
    minute_limit, minute_remaining, hour_limit, hour_remaining = (
        rate_limiter.get_rate_limit_status(api_key_info)
    )

    # Forward request to LLM backend
    url = f"{settings.llm_backend_url}/{path}"

    # Get request body
    body = await request.body()

    try:
        # Forward request
        response = await http_client.request(
            method=request.method,
            url=url,
            content=body,
            headers={
                "Content-Type": request.headers.get("Content-Type", "application/json"),
            },
        )

        # Log request to database
        duration_ms = (time.time() - start_time) * 1000

        # Extract token usage from response if available
        prompt_tokens = 0
        completion_tokens = 0
        model = None

        if response.status_code == 200:
            try:
                response_json = response.json()
                if "usage" in response_json:
                    prompt_tokens = response_json["usage"].get("prompt_tokens", 0)
                    completion_tokens = response_json["usage"].get("completion_tokens", 0)
                if "model" in response_json:
                    model = response_json["model"]
            except:
                pass

        # Log to database
        crud.create_request_log(
            db,
            user_id=api_key_info.user_id,
            api_key_id=api_key_info.key_id,
            endpoint=path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            error=None if response.status_code == 200 else response.text[:500],
        )

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit-Minute": str(minute_limit),
            "X-RateLimit-Remaining-Minute": str(minute_remaining),
            "X-RateLimit-Limit-Hour": str(hour_limit),
            "X-RateLimit-Remaining-Hour": str(hour_remaining),
        }

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=headers,
            media_type=response.headers.get("Content-Type"),
        )

    except httpx.TimeoutException:
        crud.create_request_log(
            db,
            user_id=api_key_info.user_id,
            api_key_id=api_key_info.key_id,
            endpoint=path,
            method=request.method,
            status_code=504,
            duration_ms=(time.time() - start_time) * 1000,
            error="Request timeout",
        )
        raise HTTPException(status_code=504, detail="Request timeout")

    except Exception as e:
        crud.create_request_log(
            db,
            user_id=api_key_info.user_id,
            api_key_id=api_key_info.key_id,
            endpoint=path,
            method=request.method,
            status_code=500,
            duration_ms=(time.time() - start_time) * 1000,
            error=str(e)[:500],
        )
        raise HTTPException(status_code=500, detail="Internal server error")


# LLM API Routes (with authentication)
@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def llm_api_proxy(
    path: str,
    request: Request,
    api_key_info: APIKeyInfo = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Proxy all /v1/* requests to LLM backend."""
    return await proxy_to_llm_backend(request, f"v1/{path}", api_key_info, db)


# Auth API Routes (self-service, no authentication required)
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_api_proxy(path: str, request: Request):
    """Proxy all /auth/* requests to Admin service (self-service endpoints)."""
    url = f"http://{settings.admin_host}:{settings.admin_port}/auth/{path}"

    # Get request body
    body = await request.body()

    try:
        # Forward request with all headers
        response = await http_client.request(
            method=request.method,
            url=url,
            content=body,
            headers=dict(request.headers),
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("Content-Type"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth service error: {str(e)}")


# Admin API Routes (proxy without LLM auth, admin service handles its own auth)
@app.api_route("/admin/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def admin_api_proxy(path: str, request: Request):
    """Proxy all /admin/* requests to Admin service."""
    url = f"http://{settings.admin_host}:{settings.admin_port}/{path}"

    # Get request body
    body = await request.body()

    try:
        # Forward request with all headers
        response = await http_client.request(
            method=request.method,
            url=url,
            content=body,
            headers=dict(request.headers),
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("Content-Type"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Admin service error: {str(e)}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to user self-service portal."""
    return {
        "service": "LLM API Gateway",
        "version": "1.0.0",
        "portals": {
            "user": f"http://localhost:{settings.gateway_port}/admin/user.html",
            "admin": f"http://localhost:{settings.gateway_port}/admin/index.html"
        },
        "endpoints": {
            "health": "/health",
            "llm_api": "/v1/*",
            "self_service_auth": "/auth/*",
            "admin_api": "/admin/api/*",
        },
    }


# Admin UI shortcut
@app.get("/admin")
async def admin_ui():
    """Redirect to admin UI."""
    return JSONResponse(
        content={"message": "Admin UI", "url": f"http://localhost:{settings.gateway_port}/admin/index.html"}
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.gateway_host, port=settings.gateway_port)
