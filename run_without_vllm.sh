#!/bin/bash
# vLLM 제외 - Gateway, Admin, Backend만 실행
# vLLM은 별도로 localhost:8100에서 실행 중이라고 가정

echo "=========================================="
echo "LLM API 서비스 실행 (vLLM 제외)"
echo "=========================================="
echo

# 0. 기존 컨테이너 정리
echo "[0] 기존 컨테이너 정리"
podman stop llm-backend admin-service gateway-service 2>/dev/null
podman rm llm-backend admin-service gateway-service 2>/dev/null
echo

# 1. 서비스 빌드
echo "[1] 서비스 빌드"
echo "  - Admin 빌드 중..."
podman build -t authz-admin:latest -f admin/Dockerfile . -q
echo "  - LLM Backend 빌드 중..."
podman build -t authz-llm-backend:latest -f llm_backend/Dockerfile . -q
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
fi
echo

# 3. LLM Backend 서비스
echo "[3] LLM Backend 서비스 시작"
podman run -d \
  --name llm-backend \
  -p 8001:8001 \
  -e VLLM_BASE_URL=http://localhost:8100 \
  -e VLLM_DEFAULT_MODEL=meta-llama/Llama-2-7b-chat-hf \
  authz-llm-backend:latest

if [ $? -eq 0 ]; then
  echo "✓ LLM Backend 서비스 시작됨 (포트 8001)"
else
  echo "✗ LLM Backend 서비스 시작 실패"
fi
echo

# 4. Gateway 서비스
echo "[4] Gateway 서비스 시작"
podman run -d \
  --name gateway-service \
  -p 8000:8000 \
  -v db-data:/app \
  -e DATABASE_URL=sqlite:///./llm_api.db \
  -e LLM_BACKEND_URL=http://localhost:8001 \
  -e ADMIN_HOST=localhost \
  -e ADMIN_PORT=8002 \
  -e VLLM_BASE_URL=http://localhost:8100 \
  authz-gateway:latest

if [ $? -eq 0 ]; then
  echo "✓ Gateway 서비스 시작됨 (포트 8000)"
else
  echo "✗ Gateway 서비스 시작 실패"
fi
echo

# 5. 상태 확인
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
echo "접속 URL:"
echo "  Gateway:  http://localhost:8000"
echo "  Admin:    http://localhost:8002"
echo "  Backend:  http://localhost:8001"
echo
echo "vLLM 확인:"
echo "  curl http://localhost:8100/v1/models"
echo
echo "로그 확인:"
echo "  podman logs --tail 100 gateway-service"
echo "  podman logs --tail 100 llm-backend"
echo "  podman logs --tail 100 admin-service"
echo
echo "테스트 실행:"
echo "  python3 test_system.py"
echo
echo "중지:"
echo "  podman stop gateway-service llm-backend admin-service"
echo "  podman rm gateway-service llm-backend admin-service"
