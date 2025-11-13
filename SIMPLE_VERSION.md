# 간단 버전 (Simple Version)

## 구조

```
사용자 요청
    ↓
Gateway (포트 8000)
    ├─→ Admin (포트 8002) - API 키 관리
    └─→ vLLM (포트 8100) - LLM 추론 [별도 설치]
```

**LLM Backend 제거** - Gateway가 vLLM을 직접 호출

## 실행 방법

### 1. vLLM 먼저 실행
```bash
# vLLM 설치 후
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8100
```

### 2. 서비스 실행
```bash
./run_simple.sh
```

## 서비스 역할

### Admin Service (8002)
- API 키 생성/관리
- 이메일 인증 (Self-Service)
- Admin 대시보드

### Gateway Service (8000)
- API 키 인증
- Rate Limiting
- vLLM 직접 호출
- 요청/응답 로깅

### vLLM (8100) - 별도 설치
- 실제 LLM 추론

## 테스트

```bash
# 1. vLLM 확인
curl http://localhost:8100/v1/models

# 2. Admin 로그인하여 API 키 발급
# http://localhost:8002
# username: admin, password: admin123

# 3. 또는 Self-Service로 API 키 발급
# http://localhost:8002/user

# 4. API 테스트
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'

# 5. 자동 테스트
python3 test_system.py
```

## 장점

- ✅ 더 간단한 구조
- ✅ 관리할 컨테이너 1개 감소
- ✅ 지연 시간 감소 (프록시 제거)
- ✅ 메모리 사용량 감소

## 로그 확인

```bash
# Gateway 로그
podman logs --tail 100 gateway-service

# Admin 로그
podman logs --tail 100 admin-service

# 실시간 모니터링 (watch 사용)
watch -n 2 "podman logs --tail 20 gateway-service"
```

## 중지

```bash
podman stop gateway-service admin-service
podman rm gateway-service admin-service
```

## 재시작

```bash
podman restart gateway-service admin-service
```
