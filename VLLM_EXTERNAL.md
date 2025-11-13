# vLLM 별도 설치 후 사용하기

이 프로젝트는 vLLM을 별도로 설치하여 사용할 수 있습니다.

## vLLM 별도 설치

### 옵션 1: pip 설치 (권장)
```bash
# CUDA가 있는 환경에서
pip install vllm

# 실행
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8100
```

### 옵션 2: 공식 사이트에서 설치
https://docs.vllm.ai/en/latest/getting_started/installation.html

## 나머지 서비스 실행

vLLM이 `localhost:8100`에서 실행 중일 때:

```bash
./run_without_vllm.sh
```

이 스크립트는:
- ✅ Admin Service (포트 8002)
- ✅ LLM Backend Service (포트 8001)
- ✅ Gateway Service (포트 8000)

만 실행합니다.

**중요**: 컨테이너에서 호스트의 vLLM에 접근하기 위해 `host.containers.internal:8100`을 사용합니다.

## 확인

### 1. vLLM 확인
```bash
curl http://localhost:8100/v1/models
```

### 2. 전체 시스템 테스트
```bash
python3 test_system.py
```

## 아키텍처

```
[사용자 요청]
     ↓
[Gateway :8000]
     ↓
[LLM Backend :8001]
     ↓
[vLLM :8100] ← 별도 설치
```

## 서비스별 역할

- **Gateway**: API 키 인증, Rate Limiting, 요청 라우팅
- **Admin**: API 키 관리, 사용자 관리
- **LLM Backend**: vLLM 프록시, 요청/응답 변환
- **vLLM**: 실제 LLM 추론 (별도 설치)

## 포트 변경

vLLM을 다른 포트에서 실행하려면:

```bash
# vLLM을 8200에서 실행했다면
export VLLM_BASE_URL=http://localhost:8200

# 서비스 실행 시 환경 변수로 전달
podman run -d \
  --name llm-backend \
  -p 8001:8001 \
  -e VLLM_BASE_URL=http://localhost:8200 \
  authz-llm-backend:latest
```

## 문제 해결

### vLLM 연결 안 됨
```bash
# vLLM 상태 확인
curl http://localhost:8100/health

# Backend 로그 확인
podman logs --tail 100 llm-backend
```

### 서비스 재시작
```bash
# 전체 재시작
podman stop gateway-service llm-backend admin-service
podman rm gateway-service llm-backend admin-service
./run_without_vllm.sh

# 개별 재시작
podman restart gateway-service
```
