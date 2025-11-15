#!/bin/bash
# Admin + Gateway만 실행 (심플 버전)
# vLLM은 별도로 localhost:8100에서 실행 중이라고 가정

echo "=========================================="
echo "LLM API 서비스 실행 (심플 버전)"
echo "Admin + Gateway만"
echo "=========================================="
echo

# 0. 기존 컨테이너 정리
echo "[0] 기존 컨테이너 정리"
podman stop admin-service gateway-service 2>/dev/null
podman rm admin-service gateway-service 2>/dev/null
echo

# 1. 서비스 빌드
echo "[1] 서비스 빌드"
echo "  - Admin 빌드 중..."
podman build -t authz-admin:latest -f admin/Dockerfile . -q
echo "  - Gateway 빌드 중..."
podman build -t authz-gateway:latest -f gateway/Dockerfile . -q
echo "✓ 빌드 완료"
echo

# 2. Admin 서비스
echo "[2] Admin 서비스 시작"
podman run -d \
  --name admin-service \
  -p 8002:8002 \
  -v db-data:/app \
  -e DATABASE_URL=sqlite:///./llm_api.db \
  -e ADMIN_SECRET_KEY=change-this-secret-key-in-production \
  -e USE_MOCK_EMAIL=true \
  authz-admin:latest

if [ $? -eq 0 ]; then
  echo "✓ Admin 서비스 시작됨 (포트 8002)"
else
  echo "✗ Admin 서비스 시작 실패"
  exit 1
fi
echo

# 3. Gateway 서비스 (vLLM 직접 호출)
echo "[3] Gateway 서비스 시작 (vLLM 직접 연결)"
podman run -d \
  --name gateway-service \
  -p 8000:8000 \
  -v db-data:/app \
  -e DATABASE_URL=sqlite:///./llm_api.db \
  -e LLM_BACKEND_URL=http://host.containers.internal:8100 \
  -e ADMIN_HOST=host.containers.internal \
  -e ADMIN_PORT=8002 \
  authz-gateway:latest

if [ $? -eq 0 ]; then
  echo "✓ Gateway 서비스 시작됨 (포트 8000)"
else
  echo "✗ Gateway 서비스 시작 실패"
  exit 1
fi
echo

# 4. 상태 확인
echo "=========================================="
echo "서비스 상태"
echo "=========================================="
sleep 2
podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
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
echo "  Admin:    http://localhost:8002"
echo
echo "vLLM 확인:"
echo "  curl http://localhost:8100/v1/models"
echo
echo "로그 확인:"
echo "  podman logs --tail 100 gateway-service"
echo "  podman logs --tail 100 admin-service"
echo
echo "테스트 실행:"
echo "  python3 test_system.py"
echo
echo "중지:"
echo "  podman stop gateway-service admin-service"
echo "  podman rm gateway-service admin-service"
