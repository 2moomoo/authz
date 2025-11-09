"""Shared configuration across services."""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Shared settings."""

    # Database
    database_url: str = "sqlite:///./llm_api.db"

    # Services
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000

    admin_host: str = "0.0.0.0"
    admin_port: int = 8002

    llm_backend_host: str = "localhost"
    llm_backend_port: int = 8001
    llm_backend_url: str = "http://localhost:8001"

    # vLLM
    vllm_base_url: str = "http://localhost:8100/v1"
    vllm_default_model: str = "meta-llama/Llama-2-7b-chat-hf"

    # Security
    admin_secret_key: str = "change-this-secret-key-in-production"
    admin_algorithm: str = "HS256"
    admin_token_expire_minutes: int = 60

    # Rate Limits (default tiers)
    rate_limit_free_per_minute: int = 10
    rate_limit_free_per_hour: int = 100

    rate_limit_standard_per_minute: int = 30
    rate_limit_standard_per_hour: int = 300

    rate_limit_premium_per_minute: int = 100
    rate_limit_premium_per_hour: int = 1000

    # CORS
    cors_origins: List[str] = ["*"]

    # Email Verification
    allowed_email_domains: List[str] = ["company.com", "company.co.kr"]  # Whitelist
    verification_code_expire_minutes: int = 5
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@company.com"
    use_mock_email: bool = True  # Set to False in production with real SMTP

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
