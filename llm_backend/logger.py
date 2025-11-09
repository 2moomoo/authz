"""Logging utilities for request/response tracking."""
import os
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from .config import config


def setup_logging():
    """Configure logging with rotation and retention."""
    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=config.server.log_level.upper(),
        colorize=True,
    )

    # Create log directory if it doesn't exist
    os.makedirs(config.logging.log_dir, exist_ok=True)

    # File handler for general logs
    logger.add(
        os.path.join(config.logging.log_dir, "app_{time:YYYY-MM-DD}.log"),
        rotation=config.logging.rotation,
        retention=config.logging.retention,
        level=config.server.log_level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )

    # File handler for request logs
    logger.add(
        os.path.join(config.logging.log_dir, "requests_{time:YYYY-MM-DD}.log"),
        rotation=config.logging.rotation,
        retention=config.logging.retention,
        level="INFO",
        format="{message}",
        filter=lambda record: "request_log" in record["extra"],
        encoding="utf-8",
    )

    return logger


def log_request(
    user_id: str,
    endpoint: str,
    method: str,
    request_body: Optional[Dict[str, Any]] = None,
    response_body: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    duration_ms: float = 0,
    error: Optional[str] = None,
):
    """Log API request/response for monitoring."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
    }

    if error:
        log_entry["error"] = error

    if config.logging.log_bodies:
        if request_body:
            # Truncate large bodies
            body_str = json.dumps(request_body)
            if len(body_str) > config.logging.max_body_log_size:
                body_str = body_str[:config.logging.max_body_log_size] + "...[truncated]"
            log_entry["request"] = body_str

        if response_body:
            body_str = json.dumps(response_body)
            if len(body_str) > config.logging.max_body_log_size:
                body_str = body_str[:config.logging.max_body_log_size] + "...[truncated]"
            log_entry["response"] = body_str

    logger.bind(request_log=True).info(json.dumps(log_entry))


# Initialize logging
app_logger = setup_logging()
