# Internal LLM API Platform (Simple Version)

사내 LLM API 플랫폼 - OpenAI 호환 API, 셀프 서비스 API 키 발급, Rate Limiting 포함

## 아키텍처

```
사용자 → Gateway (:8000) → vLLM (:8100) [별도 설치]
           ↓
        Admin (:8002)
```

### 주요 특징
- ✅ OpenAI 호환 API (Chat Completions, Models 등)
- ✅ 이메일 인증 기반 Self-Service API 키 발급
- ✅ Admin 대시보드
- ✅ Tier별 Rate Limiting (Free/Standard/Premium)
- ✅ 간단한 2-서비스 구조 (Gateway + Admin)

## 빠른 시작

### 사전 준비: vLLM 설치 및 실행

모든 실행 방법 공통으로 vLLM을 먼저 실행해야 합니다.

```bash
# vLLM 설치
pip install vllm

# vLLM 실행 (GPU 사용)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8100

# vLLM 확인
curl http://localhost:8100/v1/models
```

### 방법 1: Docker Compose (권장)

가장 간단한 방법입니다.

```bash
# 서비스 시작
docker compose up -d

# 로그 확인
docker compose logs -f

# 서비스 중지
docker compose down
```

### 방법 2: 로컬 실행 (개발용)

Python 가상환경에서 직접 실행합니다.

```bash
# 서비스 시작 (자동으로 의존성 설치)
./run_local.sh

# 로그 확인
tail -f logs/gateway.log
tail -f logs/admin.log

# 서비스 중지
pkill -f 'uvicorn admin.main:app'
pkill -f 'uvicorn gateway.main:app'
```

### 방법 3: Podman (선택사항)

Podman을 사용하는 경우:

```bash
./run_simple.sh
```

## 서비스 구성

### Gateway Service (Port 8000)
**역할**: 인증, Rate Limiting, vLLM 프록시

**기능**:
- API Key 검증
- Tier별 Rate Limiting
- Request/Response 로깅
- `/v1/*` → vLLM으로 직접 프록시
- `/admin/*` → Admin Service로 프록시

### Admin Service (Port 8002)
**역할**: API Key 관리, Self-Service 포털

**기능**:
- 관리자 대시보드 (`/admin/index.html`)
- Self-Service 포털 (`/user/`)
- 이메일 인증 기반 API 키 발급
- API Key CRUD
- 사용량 통계

### vLLM Server (Port 8100)
**역할**: LLM 추론 (별도 설치)

## 사용 가이드

### 방법 1: Self-Service (일반 사용자)

```bash
# 1. 브라우저에서 접속
http://localhost:8002/user/

# 2. 회사 이메일 입력 (예: user@company.com)
# 3. 이메일로 받은 인증 코드 입력
# 4. API Key 발급 (Tier 선택 가능)
```

**참고**: Mock 이메일 모드가 활성화되어 있으면 인증 코드가 서버 로그에 출력됩니다.

### 방법 2: Admin 대시보드

```bash
# 브라우저에서 접속
http://localhost:8002/admin/index.html

# 기본 계정
Username: admin
Password: admin123
```

**⚠️ 프로덕션에서는 반드시 비밀번호를 변경하세요!**

### API 사용 예시

#### Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 50
  }'
```

#### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

## Rate Limiting

| Tier | 분당 요청 | 시간당 요청 |
|------|----------|-----------|
| Free | 10 | 100 |
| Standard | 30 | 300 |
| Premium | 100 | 1000 |

Rate limit 정보는 응답 헤더에 포함:
```
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 95
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Hour: 998
```

## 테스트

```bash
# 통합 테스트 (권장)
python3 test_system.py

# 헬스 체크
curl http://localhost:8000/health
curl http://localhost:8002/health
```

## 프로젝트 구조

```
authz/
├── gateway/                  # Gateway Service
│   ├── main.py              # FastAPI app
│   ├── auth.py              # API key authentication
│   ├── rate_limiter.py      # Rate limiting
│   ├── requirements.txt
│   └── Dockerfile
│
├── admin/                   # Admin Service
│   ├── main.py             # Admin API + UI
│   ├── ui/                 # Web UI files
│   │   ├── index.html      # Admin dashboard
│   │   ├── app.js
│   │   ├── user.html       # Self-service portal
│   │   └── user.js
│   ├── requirements.txt
│   └── Dockerfile
│
├── shared/                 # 공통 라이브러리
│   ├── database.py         # SQLAlchemy
│   ├── models.py           # DB models
│   ├── crud.py             # CRUD operations
│   ├── config.py           # 설정
│   ├── email_service.py    # 이메일 인증
│   └── requirements.txt
│
├── docker-compose.yml      # Docker Compose 설정
├── run_local.sh           # 로컬 실행 스크립트 (개발용)
├── run_simple.sh          # Podman 실행 스크립트 (선택)
├── test_system.py         # 통합 테스트
├── .env.example           # 환경 변수 예시
├── SIMPLE_VERSION.md      # 상세 가이드
└── README.md             # 이 문서
```

## 모니터링

### 로그 확인

**Docker Compose:**
```bash
# 전체 로그
docker compose logs -f

# 특정 서비스 로그
docker compose logs -f gateway
docker compose logs -f admin
```

**로컬 실행:**
```bash
# 로그 파일 확인
tail -f logs/gateway.log
tail -f logs/admin.log

# 실시간 모니터링
watch -n 2 "tail -20 logs/gateway.log"
```

**Podman:**
```bash
podman logs --tail 100 gateway-service
podman logs --tail 100 admin-service
```

### Health Checks

```bash
# 전체 시스템
curl http://localhost:8000/health

# 개별 서비스
curl http://localhost:8002/health  # Admin
```

## 관리

### Docker Compose

```bash
# 서비스 중지
docker compose stop

# 서비스 재시작
docker compose restart

# 서비스 삭제 (볼륨 유지)
docker compose down

# 서비스 삭제 (볼륨 포함)
docker compose down -v

# 재빌드
docker compose build
docker compose up -d
```

### 로컬 실행

```bash
# 서비스 중지
pkill -f 'uvicorn admin.main:app'
pkill -f 'uvicorn gateway.main:app'

# 또는 PID 파일 사용
kill $(cat logs/admin.pid)
kill $(cat logs/gateway.pid)

# 재시작
./run_local.sh
```

### Podman

```bash
# 서비스 중지
podman stop gateway-service admin-service

# 서비스 재시작
podman restart gateway-service admin-service

# 재빌드
./run_simple.sh
```

## 환경 변수

### Admin Service
- `DATABASE_URL`: SQLite DB 경로 (기본: `sqlite:///./llm_api.db`)
- `ADMIN_SECRET_KEY`: JWT 시크릿 키
- `USE_MOCK_EMAIL`: Mock 이메일 사용 여부 (기본: `true`)

### Gateway Service
- `DATABASE_URL`: SQLite DB 경로
- `LLM_BACKEND_URL`: vLLM 서버 URL (기본: `http://host.containers.internal:8100`)
- `ADMIN_HOST`: Admin 서비스 호스트
- `ADMIN_PORT`: Admin 서비스 포트

## 보안 고려사항

### 프로덕션 배포 전 체크리스트

- [ ] Admin 기본 비밀번호 변경
- [ ] `ADMIN_SECRET_KEY` 환경 변수 변경
- [ ] 이메일 도메인 화이트리스트 설정 (`allowed_email_domains`)
- [ ] SMTP 설정 (`USE_MOCK_EMAIL=false`)
- [ ] HTTPS 적용 (Nginx reverse proxy)
- [ ] 내부망에서만 접근 가능하도록 방화벽 설정
- [ ] SQLite 대신 PostgreSQL 사용 권장
- [ ] Rate limiting 값 조정
- [ ] 로그 보관 정책 설정

## 트러블슈팅

### Gateway가 vLLM에 연결하지 못함

```bash
# vLLM 상태 확인
curl http://localhost:8100/v1/models

# 컨테이너 환경 변수 확인
podman exec gateway-service env | grep LLM_BACKEND_URL
# 출력되어야 함: LLM_BACKEND_URL=http://host.containers.internal:8100
```

### 이메일 인증 코드를 받지 못함

```bash
# Admin 로그에서 인증 코드 확인 (Mock 모드)
podman logs admin-service | grep "Verification code"

# 출력 예시:
# [Mock Email] To: user@company.com
# Verification code: 123456
```

### 컨테이너 포트가 이미 사용 중

```bash
# 기존 컨테이너 확인
podman ps -a

# 중지 및 삭제
podman stop gateway-service admin-service
podman rm gateway-service admin-service
```

## FAQ

**Q: 왜 LLM Backend 서비스가 없나요?**
A: Gateway가 vLLM을 직접 호출하여 구조를 간소화했습니다. 추가 프록시 레이어가 불필요합니다.

**Q: Docker 대신 Podman을 사용하는 이유는?**
A: 라이선스 이슈를 피하고, rootless 컨테이너 환경을 사용하기 위함입니다.

**Q: API Key는 어디에 저장되나요?**
A: SQLite 데이터베이스 (`llm_api.db`)에 저장됩니다. Named volume으로 컨테이너 간 공유됩니다.

**Q: Rate limiting은 분산 환경에서 작동하나요?**
A: 현재는 인메모리 방식입니다. Redis 기반으로 업그레이드 가능합니다.

**Q: 이메일 도메인 제한을 어떻게 설정하나요?**
A: `shared/config.py`의 `allowed_email_domains` 리스트를 수정하세요.

## 라이선스

내부 사용 전용. 외부 배포 금지.
