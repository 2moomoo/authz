#!/bin/bash
# Podman으로 GPU 사용하여 전체 시스템 실행

echo "=========================================="
echo "Podman + GPU로 LLM API 실행"
echo "=========================================="
echo

# 1. vLLM GPU로 실행
echo "[1] vLLM 서버 시작 (GPU)"
podman run -d \
  --name vllm-server \
  --device nvidia.com/gpu=all \
  -p 8100:8100 \
  --network llm-api-network \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8100 \
  --dtype auto \
  --max-model-len 4096

echo "vLLM 시작 중... (30초 대기)"
sleep 30

# 2. 네트워크 생성 (없으면)
podman network create llm-api-network 2>/dev/null || true

# 3. 나머지 서비스 빌드
echo
echo "[2] 다른 서비스 빌드"
podman build -t authz-admin:latest -f admin/Dockerfile .
podman build -t authz-llm-backend:latest -f llm_backend/Dockerfile .
podman build -t authz-gateway:latest -f gateway/Dockerfile .

# 4. Admin 서비스
echo
echo "[3] Admin 서비스 시작"
podman run -d \
  --name admin-service \
  --network llm-api-network \
  -p 8002:8002 \
  -v db-data:/app \
  -e DATABASE_URL=sqlite:///./llm_api.db \
  -e ADMIN_SECRET_KEY=change-this-secret-key-in-production \
  -e USE_MOCK_EMAIL=true \
  authz-admin:latest

# 5. LLM Backend 서비스
echo
echo "[4] LLM Backend 서비스 시작"
podman run -d \
  --name llm-backend \
  --network llm-api-network \
  -p 8001:8001 \
  -e VLLM_BASE_URL=http://vllm-server:8100 \
  -e VLLM_DEFAULT_MODEL=meta-llama/Llama-2-7b-chat-hf \
  authz-llm-backend:latest

# 6. Gateway 서비스
echo
echo "[5] Gateway 서비스 시작"
podman run -d \
  --name gateway-service \
  --network llm-api-network \
  -p 8000:8000 \
  -v db-data:/app \
  -e DATABASE_URL=sqlite:///./llm_api.db \
  -e LLM_BACKEND_URL=http://llm-backend:8001 \
  -e ADMIN_HOST=admin-service \
  -e ADMIN_PORT=8002 \
  -e VLLM_BASE_URL=http://vllm-server:8100 \
  authz-gateway:latest

echo
echo "=========================================="
echo "✓ 모든 서비스 시작 완료"
echo "=========================================="
echo
echo "서비스 확인:"
echo "  podman ps"
echo
echo "로그 확인:"
echo "  podman logs -f vllm-server"
echo "  podman logs -f gateway-service"
echo
echo "접속:"
echo "  Admin: http://localhost:8002"
echo "  Gateway: http://localhost:8000"
echo
echo "중지:"
echo "  podman stop vllm-server llm-backend admin-service gateway-service"
echo "  podman rm vllm-server llm-backend admin-service gateway-service"
