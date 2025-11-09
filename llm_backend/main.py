"""LLM Backend Service - Simple vLLM proxy without authentication.

Authentication and rate limiting are handled by the Gateway.
This service only proxies requests to vLLM.
"""
import sys
from pathlib import Path

# Add parent directory to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import settings
from .vllm_client import vllm_client
from .models import (
    CompletionRequest,
    ChatCompletionRequest,
    HealthResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print(f"Starting LLM Backend Service")
    print(f"vLLM backend: {settings.vllm_base_url}")
    print(f"Default model: {settings.vllm_default_model}")

    # Check vLLM connection
    is_healthy = await vllm_client.health_check()
    if is_healthy:
        print("vLLM backend is healthy")
    else:
        print("WARNING: vLLM backend health check failed")

    yield

    # Cleanup
    print("Shutting down LLM Backend Service")
    await vllm_client.close()


# Create FastAPI app
app = FastAPI(
    title="LLM Backend Service",
    description="vLLM proxy service (authentication handled by gateway)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    vllm_healthy = await vllm_client.health_check()

    return HealthResponse(
        status="healthy" if vllm_healthy else "degraded",
        version="1.0.0",
        model=settings.vllm_default_model,
        vllm_status="connected" if vllm_healthy else "disconnected",
    )


@app.get("/v1/models")
async def list_models():
    """List available models."""
    try:
        models_response = await vllm_client.models()
        return models_response
    except Exception as e:
        print(f"Failed to list models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models list",
        )


@app.post("/v1/completions")
async def create_completion(request_body: CompletionRequest):
    """Create a text completion."""
    try:
        # Forward request to vLLM
        request_dict = request_body.model_dump(exclude_none=True)

        # Use default model if not specified
        if not request_dict.get("model"):
            request_dict["model"] = settings.vllm_default_model

        response_body = await vllm_client.completions(request_dict)

        return JSONResponse(content=response_body)

    except Exception as e:
        print(f"Completion request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing completion request",
        )


@app.post("/v1/chat/completions")
async def create_chat_completion(request_body: ChatCompletionRequest):
    """Create a chat completion."""
    try:
        # Forward request to vLLM
        request_dict = request_body.model_dump(exclude_none=True)

        # Use default model if not specified
        if not request_dict.get("model"):
            request_dict["model"] = settings.vllm_default_model

        response_body = await vllm_client.chat_completions(request_dict)

        return JSONResponse(content=response_body)

    except Exception as e:
        print(f"Chat completion request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing chat completion request",
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LLM Backend Service",
        "version": "1.0.0",
        "note": "This service is internal only. Use the Gateway for authenticated access.",
        "endpoints": {
            "health": "/health",
            "models": "/v1/models",
            "completions": "/v1/completions",
            "chat_completions": "/v1/chat/completions",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.llm_backend_host,
        port=settings.llm_backend_port,
    )
