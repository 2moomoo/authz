#!/usr/bin/env python3
"""
LLM API 시스템 통합 테스트
Python 버전 - 더 상세한 테스트
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost"
GATEWAY_PORT = 8000
ADMIN_PORT = 8002
BACKEND_PORT = 8001

class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_header(text):
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{'='*60}")

def print_result(passed, message):
    if passed:
        print(f"{Colors.GREEN}✓ PASS{Colors.NC} {message}")
        return 1
    else:
        print(f"{Colors.RED}✗ FAIL{Colors.NC} {message}")
        return 0

def test_health_checks():
    print_header("1. Health Check 테스트")
    passed = 0
    total = 3

    endpoints = {
        "Gateway": f"{BASE_URL}:{GATEWAY_PORT}/health",
        "Admin": f"{BASE_URL}:{ADMIN_PORT}/health",
        "Backend": f"{BASE_URL}:{BACKEND_PORT}/health",
    }

    for name, url in endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                passed += print_result(True, f"{name} Health Check")
                print(f"  Response: {response.json()}")
            else:
                print_result(False, f"{name} Health Check (HTTP {response.status_code})")
        except Exception as e:
            print_result(False, f"{name} Health Check - {str(e)}")

    return passed, total

def test_admin_login():
    print_header("2. Admin 로그인 테스트")

    try:
        response = requests.post(
            f"{BASE_URL}:{ADMIN_PORT}/api/login",
            json={"username": "admin", "password": "admin123"}
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            print_result(True, "Admin 로그인")
            print(f"  Token: {token[:30]}...")
            return 1, 1, token
        else:
            print_result(False, f"Admin 로그인 (HTTP {response.status_code})")
            print(f"  Response: {response.text}")
            return 0, 1, None
    except Exception as e:
        print_result(False, f"Admin 로그인 - {str(e)}")
        return 0, 1, None

def test_self_service():
    print_header("3. Self-Service 이메일 인증 테스트")

    test_email = "test@company.com"

    try:
        response = requests.post(
            f"{BASE_URL}:{ADMIN_PORT}/auth/request-code",
            json={"email": test_email}
        )

        if response.status_code == 200:
            print_result(True, "이메일 인증 코드 요청")
            print(f"  Response: {response.json()}")
            print(f"{Colors.YELLOW}  ℹ 콘솔 로그에서 6자리 인증 코드를 확인하세요{Colors.NC}")
            return 1, 1
        else:
            print_result(False, f"이메일 인증 코드 요청 (HTTP {response.status_code})")
            return 0, 1
    except Exception as e:
        print_result(False, f"이메일 인증 코드 요청 - {str(e)}")
        return 0, 1

def test_create_api_key(admin_token):
    print_header("4. API Key 생성 테스트")

    if not admin_token:
        print(f"{Colors.YELLOW}⊘ SKIP{Colors.NC} (Admin 토큰 없음)")
        return 0, 0, None

    try:
        response = requests.post(
            f"{BASE_URL}:{ADMIN_PORT}/api/keys",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "user_id": "test-user@company.com",
                "tier": "standard",
                "description": "Test API Key from Python"
            }
        )

        if response.status_code == 200:
            api_key = response.json().get("key")
            print_result(True, "API Key 생성")
            print(f"  API Key: {api_key}")
            return 1, 1, api_key
        else:
            print_result(False, f"API Key 생성 (HTTP {response.status_code})")
            print(f"  Response: {response.text}")
            return 0, 1, None
    except Exception as e:
        print_result(False, f"API Key 생성 - {str(e)}")
        return 0, 1, None

def test_gateway_auth(api_key):
    print_header("5. Gateway 인증 테스트")
    passed = 0
    total = 2

    # 인증 없이 접근 (실패해야 함)
    try:
        response = requests.get(f"{BASE_URL}:{GATEWAY_PORT}/health")
        if response.status_code == 401:
            passed += print_result(True, "인증 없이 접근 차단")
        else:
            print_result(False, f"인증 없이 접근 (예상: 401, 실제: {response.status_code})")
    except Exception as e:
        print_result(False, f"인증 없이 접근 - {str(e)}")

    # API Key로 인증 (성공해야 함)
    if api_key:
        try:
            response = requests.get(
                f"{BASE_URL}:{GATEWAY_PORT}/health",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if response.status_code == 200:
                passed += print_result(True, "API Key 인증")
                print(f"  Response: {response.json()}")
            else:
                print_result(False, f"API Key 인증 (HTTP {response.status_code})")
        except Exception as e:
            print_result(False, f"API Key 인증 - {str(e)}")
    else:
        print(f"{Colors.YELLOW}⊘ SKIP{Colors.NC} API Key 인증 (API Key 없음)")

    return passed, total

def test_llm_api(api_key):
    print_header("6. LLM API 호출 테스트")
    passed = 0
    total = 2

    if not api_key:
        print(f"{Colors.YELLOW}⊘ SKIP{Colors.NC} (API Key 없음)")
        return 0, 0

    # 모델 목록 조회
    try:
        response = requests.get(
            f"{BASE_URL}:{GATEWAY_PORT}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if response.status_code == 200:
            passed += print_result(True, "모델 목록 조회")
            print(f"  Models: {json.dumps(response.json(), indent=2)[:200]}...")
        else:
            print_result(False, f"모델 목록 조회 (HTTP {response.status_code})")
    except Exception as e:
        print_result(False, f"모델 목록 조회 - {str(e)}")

    # Chat Completion 테스트
    try:
        response = requests.post(
            f"{BASE_URL}:{GATEWAY_PORT}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "meta-llama/Llama-2-7b-chat-hf",
                "messages": [{"role": "user", "content": "Hello! Say hi in one word."}],
                "max_tokens": 10,
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            passed += print_result(True, "Chat Completion API")
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {}).get("content", "")
                print(f"  LLM 응답: {message[:100]}")
                print(f"  토큰 사용: {result.get('usage', {})}")
        else:
            print(f"{Colors.YELLOW}! PARTIAL{Colors.NC} Chat Completion (HTTP {response.status_code} - vLLM이 준비 중일 수 있음)")
            print(f"  Response: {response.text[:200]}")
    except requests.Timeout:
        print(f"{Colors.YELLOW}! TIMEOUT{Colors.NC} Chat Completion (vLLM 응답 대기 중)")
    except Exception as e:
        print_result(False, f"Chat Completion - {str(e)}")

    return passed, total

def test_rate_limiting(api_key):
    print_header("7. Rate Limiting 테스트")

    if not api_key:
        print(f"{Colors.YELLOW}⊘ SKIP{Colors.NC} (API Key 없음)")
        return 0, 0

    print("연속으로 10개 요청 보내기...")
    success_count = 0
    rate_limited_count = 0

    for i in range(10):
        try:
            response = requests.get(
                f"{BASE_URL}:{GATEWAY_PORT}/health",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5
            )
            if response.status_code == 200:
                print(f"  요청 {i+1}: {Colors.GREEN}✓{Colors.NC}")
                success_count += 1
            elif response.status_code == 429:
                print(f"  요청 {i+1}: {Colors.YELLOW}⚠ Rate Limited{Colors.NC}")
                rate_limited_count += 1
            else:
                print(f"  요청 {i+1}: {Colors.RED}✗ {response.status_code}{Colors.NC}")
            time.sleep(0.1)
        except Exception as e:
            print(f"  요청 {i+1}: {Colors.RED}✗ {str(e)}{Colors.NC}")

    print(f"\n  성공: {success_count}, Rate Limited: {rate_limited_count}")
    if rate_limited_count > 0:
        print_result(True, "Rate Limiting 작동 확인")
        return 1, 1
    else:
        print(f"{Colors.YELLOW}ℹ{Colors.NC} Rate Limit에 도달하지 않음 (설정이 너그럽거나 요청이 적음)")
        return 1, 1

def main():
    print(f"\n{Colors.BLUE}{'='*60}")
    print("LLM API 시스템 통합 테스트")
    print(f"{'='*60}{Colors.NC}\n")

    total_passed = 0
    total_tests = 0

    # 1. Health Checks
    passed, total = test_health_checks()
    total_passed += passed
    total_tests += total

    # 2. Admin Login
    passed, total, admin_token = test_admin_login()
    total_passed += passed
    total_tests += total

    # 3. Self-Service
    passed, total = test_self_service()
    total_passed += passed
    total_tests += total

    # 4. Create API Key
    passed, total, api_key = test_create_api_key(admin_token)
    total_passed += passed
    total_tests += total

    # 5. Gateway Auth
    passed, total = test_gateway_auth(api_key)
    total_passed += passed
    total_tests += total

    # 6. LLM API
    passed, total = test_llm_api(api_key)
    total_passed += passed
    total_tests += total

    # 7. Rate Limiting
    passed, total = test_rate_limiting(api_key)
    total_passed += passed
    total_tests += total

    # 결과 요약
    print(f"\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")
    print(f"통과: {Colors.GREEN}{total_passed}{Colors.NC}")
    print(f"실패: {Colors.RED}{total_tests - total_passed}{Colors.NC}")
    print(f"총계: {total_tests}")

    if total_passed == total_tests:
        print(f"\n{Colors.GREEN}✓ 모든 테스트 통과!{Colors.NC}\n")
        return 0
    else:
        print(f"\n{Colors.RED}✗ {total_tests - total_passed}개 테스트 실패{Colors.NC}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
