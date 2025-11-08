"""Configuration management for the internal LLM API server."""
import os
from typing import Dict, Any, List
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    log_level: str = "info"
    cors_enabled: bool = True
    cors_origins: List[str] = ["*"]


class VLLMConfig(BaseModel):
    base_url: str = "http://localhost:8100/v1"
    default_model: str = "meta-llama/Llama-2-7b-chat-hf"
    timeout: int = 300
    max_retries: int = 3


class APIKeyInfo(BaseModel):
    user_id: str
    tier: str = "standard"


class RateLimitConfig(BaseModel):
    requests_per_minute: int = 30
    requests_per_hour: int = 300


class LoggingConfig(BaseModel):
    log_dir: str = "./logs"
    rotation: str = "500 MB"
    retention: str = "30 days"
    log_bodies: bool = True
    max_body_log_size: int = 10000


class MonitoringConfig(BaseModel):
    prometheus_enabled: bool = True
    metrics_port: int = 9090


class SecurityConfig(BaseModel):
    require_https: bool = False
    api_key_header: str = "Authorization"
    use_bearer_format: bool = True


class Config(BaseSettings):
    """Application configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    vllm: VLLMConfig = Field(default_factory=VLLMConfig)
    api_keys: Dict[str, APIKeyInfo] = Field(default_factory=dict)
    rate_limits: Dict[str, RateLimitConfig] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # Parse nested configurations
        if config_data:
            if "api_keys" in config_data:
                api_keys_dict = {}
                for key, value in config_data["api_keys"].items():
                    api_keys_dict[key] = APIKeyInfo(**value)
                config_data["api_keys"] = api_keys_dict

            if "rate_limits" in config_data:
                rate_limits_dict = {}
                for tier, limits in config_data["rate_limits"].items():
                    rate_limits_dict[tier] = RateLimitConfig(**limits)
                config_data["rate_limits"] = rate_limits_dict

            return Config(**config_data)

    return Config()


# Global config instance
config = load_config()
