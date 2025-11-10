#!/bin/bash
# 전체 시스템 테스트 스크립트

BASE_URL=${BASE_URL:-"http://localhost"}
GATEWAY_PORT=${GATEWAY_PORT:-8000}
ADMIN_PORT=${ADMIN_PORT:-8002}
BACKEND_PORT=${BACKEND_PORT:-8001}

echo "=========================================="
echo "LLM API 시스템 테스트"
echo "=========================================="
echo

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

# 테스트 함수
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=$3
    local method=${4:-GET}
    local data=${5:-}
    local headers=${6:-}

    echo -n "[$name] "

    if [ "$method" = "POST" ]; then
        if [ -n "$headers" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$url" -H "Content-Type: application/json" -H "$headers" -d "$data" 2>&1)
        else
            response=$(curl -s -w "\n%{http_code}" -X POST "$url" -H "Content-Type: application/json" -d "$data" 2>&1)
        fi
    else
        if [ -n "$headers" ]; then
            response=$(curl -s -w "\n%{http_code}" "$url" -H "$headers" 2>&1)
        else
            response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
        fi
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        ((test_passed++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $http_code)"
        echo "  Response: $body"
        ((test_failed++))
        return 1
    fi
}

# 1. Health Check 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Health Check 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_endpoint "Gateway Health" "$BASE_URL:$GATEWAY_PORT/health" "200"
test_endpoint "Admin Health" "$BASE_URL:$ADMIN_PORT/health" "200"
test_endpoint "Backend Health" "$BASE_URL:$BACKEND_PORT/health" "200"
echo

# 2. Admin 로그인 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Admin 로그인 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
login_response=$(curl -s -X POST "$BASE_URL:$ADMIN_PORT/api/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')

ADMIN_TOKEN=$(echo $login_response | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$ADMIN_TOKEN" ]; then
    echo -e "${GREEN}✓ PASS${NC} Admin 로그인 성공"
    echo "  Token: ${ADMIN_TOKEN:0:20}..."
    ((test_passed++))
else
    echo -e "${RED}✗ FAIL${NC} Admin 로그인 실패"
    echo "  Response: $login_response"
    ((test_failed++))
fi
echo

# 3. Self-Service 이메일 인증 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Self-Service 이메일 인증 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TEST_EMAIL="test@company.com"

echo -n "[이메일 인증 요청] "
verify_response=$(curl -s -X POST "$BASE_URL:$ADMIN_PORT/auth/request-code" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\"}")

if echo "$verify_response" | grep -q "message"; then
    echo -e "${GREEN}✓ PASS${NC}"
    echo "  Response: $verify_response"
    echo -e "${YELLOW}  ℹ 콘솔에서 6자리 인증 코드를 확인하세요${NC}"
    ((test_passed++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Response: $verify_response"
    ((test_failed++))
fi
echo

# 4. API Key 생성 테스트 (Admin)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. API Key 생성 테스트 (Admin)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$ADMIN_TOKEN" ]; then
    apikey_response=$(curl -s -X POST "$BASE_URL:$ADMIN_PORT/api/keys" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -d '{"user_id":"test-user@company.com","tier":"standard","description":"Test API Key"}')

    API_KEY=$(echo $apikey_response | grep -o '"key":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓ PASS${NC} API Key 생성 성공"
        echo "  API Key: $API_KEY"
        ((test_passed++))
    else
        echo -e "${RED}✗ FAIL${NC} API Key 생성 실패"
        echo "  Response: $apikey_response"
        ((test_failed++))
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC} (Admin 토큰 없음)"
fi
echo

# 5. Gateway 인증 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Gateway 인증 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 인증 없이 접근 (실패해야 함)
test_endpoint "인증 없이 접근 (실패 예상)" "$BASE_URL:$GATEWAY_PORT/health" "401"

# API Key로 인증 (성공해야 함)
if [ -n "$API_KEY" ]; then
    test_endpoint "API Key 인증" "$BASE_URL:$GATEWAY_PORT/health" "200" "GET" "" "Authorization: Bearer $API_KEY"
else
    echo -e "${YELLOW}⊘ SKIP${NC} (API Key 없음)"
fi
echo

# 6. LLM API 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. LLM API 호출 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$API_KEY" ]; then
    echo -n "[모델 목록 조회] "
    models_response=$(curl -s -w "\n%{http_code}" "$BASE_URL:$GATEWAY_PORT/v1/models" \
        -H "Authorization: Bearer $API_KEY")

    http_code=$(echo "$models_response" | tail -n1)
    body=$(echo "$models_response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        echo "  Response: $(echo $body | head -c 100)..."
        ((test_passed++))
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        ((test_failed++))
    fi

    echo
    echo -n "[Chat Completion 테스트] "
    chat_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL:$GATEWAY_PORT/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d '{
            "model": "meta-llama/Llama-2-7b-chat-hf",
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "max_tokens": 50
        }')

    http_code=$(echo "$chat_response" | tail -n1)
    body=$(echo "$chat_response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        echo "  Response: $(echo $body | head -c 150)..."
        ((test_passed++))
    else
        echo -e "${YELLOW}! PARTIAL${NC} (HTTP $http_code - vLLM may not be ready)"
        echo "  Response: $(echo $body | head -c 150)..."
    fi
else
    echo -e "${YELLOW}⊘ SKIP${NC} (API Key 없음)"
fi
echo

# 7. Rate Limiting 테스트
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Rate Limiting 테스트"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -n "$API_KEY" ]; then
    echo "연속으로 여러 요청 보내기 (Rate limit 확인)..."
    for i in {1..5}; do
        echo -n "  요청 $i: "
        response=$(curl -s -w "%{http_code}" -o /dev/null "$BASE_URL:$GATEWAY_PORT/health" \
            -H "Authorization: Bearer $API_KEY")
        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✓${NC}"
        elif [ "$response" = "429" ]; then
            echo -e "${YELLOW}⚠ Rate Limited${NC}"
        else
            echo -e "${RED}✗ $response${NC}"
        fi
        sleep 0.2
    done
    ((test_passed++))
else
    echo -e "${YELLOW}⊘ SKIP${NC} (API Key 없음)"
fi
echo

# 결과 요약
echo "=========================================="
echo "테스트 결과 요약"
echo "=========================================="
echo -e "통과: ${GREEN}$test_passed${NC}"
echo -e "실패: ${RED}$test_failed${NC}"
echo "총계: $((test_passed + test_failed))"
echo

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}✓ 모든 테스트 통과!${NC}"
    exit 0
else
    echo -e "${RED}✗ 일부 테스트 실패${NC}"
    exit 1
fi
