#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Testing imports for all services...")
print("=" * 60)

errors = []

# Test shared imports
print("\n[1/4] Testing shared module...")
try:
    from shared.config import settings
    print(f"  ✓ shared.config - vLLM URL: {settings.vllm_base_url}")
except Exception as e:
    errors.append(f"shared.config: {e}")
    print(f"  ✗ shared.config: {e}")

try:
    from shared.database import Base, engine, SessionLocal
    print(f"  ✓ shared.database")
except Exception as e:
    errors.append(f"shared.database: {e}")
    print(f"  ✗ shared.database: {e}")

try:
    from shared.models import APIKey, VerificationCode, AdminUser, RequestLog
    print(f"  ✓ shared.models")
except Exception as e:
    errors.append(f"shared.models: {e}")
    print(f"  ✗ shared.models: {e}")

try:
    from shared import crud
    print(f"  ✓ shared.crud")
except Exception as e:
    errors.append(f"shared.crud: {e}")
    print(f"  ✗ shared.crud: {e}")

# Test gateway imports
print("\n[2/4] Testing gateway module...")
try:
    from gateway.auth import verify_api_key, APIKeyInfo
    print(f"  ✓ gateway.auth")
except Exception as e:
    errors.append(f"gateway.auth: {e}")
    print(f"  ✗ gateway.auth: {e}")

try:
    from gateway.rate_limiter import RateLimiter
    print(f"  ✓ gateway.rate_limiter")
except Exception as e:
    errors.append(f"gateway.rate_limiter: {e}")
    print(f"  ✗ gateway.rate_limiter: {e}")

try:
    from gateway import main as gateway_main
    print(f"  ✓ gateway.main - App: {gateway_main.app}")
except Exception as e:
    errors.append(f"gateway.main: {e}")
    print(f"  ✗ gateway.main: {e}")

# Test admin imports
print("\n[3/4] Testing admin module...")
try:
    from admin import main as admin_main
    print(f"  ✓ admin.main - App: {admin_main.app}")
except Exception as e:
    errors.append(f"admin.main: {e}")
    print(f"  ✗ admin.main: {e}")

# Test llm_backend imports
print("\n[4/4] Testing llm_backend module...")
try:
    from llm_backend.models import CompletionRequest, ChatCompletionRequest
    print(f"  ✓ llm_backend.models")
except Exception as e:
    errors.append(f"llm_backend.models: {e}")
    print(f"  ✗ llm_backend.models: {e}")

try:
    from llm_backend.vllm_client import vllm_client
    print(f"  ✓ llm_backend.vllm_client - URL: {vllm_client.base_url}")
except Exception as e:
    errors.append(f"llm_backend.vllm_client: {e}")
    print(f"  ✗ llm_backend.vllm_client: {e}")

try:
    from llm_backend import main as llm_main
    print(f"  ✓ llm_backend.main - App: {llm_main.app}")
except Exception as e:
    errors.append(f"llm_backend.main: {e}")
    print(f"  ✗ llm_backend.main: {e}")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"❌ FAILED: {len(errors)} error(s) found")
    print("=" * 60)
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✅ SUCCESS: All imports working correctly")
    print("=" * 60)
    sys.exit(0)
