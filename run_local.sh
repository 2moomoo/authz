#!/bin/bash
# 로컬 개발 환경에서 서비스 직접 실행
# vLLM은 별도로 localhost:8100에서 실행 중이라고 가정

set -e

echo "=========================================="
echo "LLM API 로컬 실행 (개발용)"
echo "=========================================="
echo

# 0. Python 가상환경 확인
if [ ! -d "venv" ]; then
    echo "[0] Python 가상환경 생성"
    python3 -m venv venv
    echo "✓ 가상환경 생성 완료"
    echo
fi

echo "[1] 가상환경 활성화"
source venv/bin/activate
echo "✓ 가상환경 활성화됨"
echo

# 1. 의존성 설치 확인
echo "[2] 의존성 확인"
if ! python -c "import fastapi" 2>/dev/null; then
    echo "  의존성 설치 중..."
    pip install -q -r shared/requirements.txt
    pip install -q -r admin/requirements.txt
    pip install -q -r gateway/requirements.txt
    echo "✓ 의존성 설치 완료"
else
    echo "✓ 의존성 이미 설치됨"
fi
echo

# 2. 환경 변수 설정
export DATABASE_URL=${DATABASE_URL:-"sqlite:///./llm_api.db"}
export ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY:-"dev-secret-key-change-in-production"}
export USE_MOCK_EMAIL=${USE_MOCK_EMAIL:-"true"}
export LLM_BACKEND_URL=${LLM_BACKEND_URL:-"http://localhost:8100"}
export ADMIN_HOST=${ADMIN_HOST:-"localhost"}
export ADMIN_PORT=${ADMIN_PORT:-"8002"}

# 3. 기존 프로세스 종료
echo "[3] 기존 프로세스 정리"
pkill -f "uvicorn admin.main:app" 2>/dev/null || true
pkill -f "uvicorn gateway.main:app" 2>/dev/null || true
sleep 1
echo "✓ 기존 프로세스 종료됨"
echo

# 4. 로그 디렉토리 생성
mkdir -p logs

# 5. Admin 서비스 시작
echo "[4] Admin 서비스 시작"
python -m uvicorn admin.main:app \
    --host 0.0.0.0 \
    --port 8002 \
    --log-level info \
    > logs/admin.log 2>&1 &
ADMIN_PID=$!
echo "✓ Admin 서비스 시작됨 (PID: $ADMIN_PID, 포트 8002)"
echo

# 6. Gateway 서비스 시작
echo "[5] Gateway 서비스 시작"
sleep 2  # Admin이 먼저 시작되도록 대기
python -m uvicorn gateway.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info \
    > logs/gateway.log 2>&1 &
GATEWAY_PID=$!
echo "✓ Gateway 서비스 시작됨 (PID: $GATEWAY_PID, 포트 8000)"
echo

# 7. 서비스 확인
echo "[6] 서비스 확인 중..."
sleep 3

check_service() {
    local name=$1
    local url=$2
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo "✓ $name 정상 작동"
        return 0
    else
        echo "✗ $name 응답 없음 (로그 확인 필요)"
        return 1
    fi
}

check_service "Admin" "http://localhost:8002/health"
check_service "Gateway" "http://localhost:8000/health"
echo

echo "=========================================="
echo "✓ 서비스 시작 완료"
echo "=========================================="
echo
echo "구조:"
echo "  사용자 → Gateway(:8000) → vLLM(:8100)"
echo "             ↓"
echo "          Admin(:8002)"
echo
echo "접속 URL:"
echo "  Gateway:  http://localhost:8000"
echo "  Admin:    http://localhost:8002/admin/index.html"
echo "  Self-Service: http://localhost:8002/user/"
echo
echo "vLLM 확인:"
echo "  curl http://localhost:8100/v1/models"
echo
echo "로그 확인:"
echo "  tail -f logs/gateway.log"
echo "  tail -f logs/admin.log"
echo
echo "테스트 실행:"
echo "  python test_system.py"
echo
echo "서비스 종료:"
echo "  pkill -f 'uvicorn admin.main:app'"
echo "  pkill -f 'uvicorn gateway.main:app'"
echo "  또는"
echo "  kill $ADMIN_PID $GATEWAY_PID"
echo
echo "PID 저장 위치:"
echo "  Admin: $ADMIN_PID"
echo "  Gateway: $GATEWAY_PID"
echo

# PID 파일 저장
echo $ADMIN_PID > logs/admin.pid
echo $GATEWAY_PID > logs/gateway.pid
echo "PID 파일 저장됨: logs/admin.pid, logs/gateway.pid"
