# Internal LLM API Platform

완전한 마이크로서비스 아키텍처 기반의 사내 LLM API 플랫폼입니다. OpenAI 호환 API, 관리자 대시보드, 인증 게이트웨이를 포함합니다.

## 아키텍처

```
┌──────────────────────────────────────────────────────┐
│                    Client (직원)                      │
│              IDE / Script / Browser                   │
└────────────────────┬─────────────────────────────────┘
                     ↓
┌────────────────────────────────────────────────────────┐
│                  Gateway Service                        │
│                   (Port 8000)                          │
│  ┌──────────────────────────────────────────────┐     │
│  │  • API Key 인증                               │     │
│  │  • Rate Limiting                              │     │
│  │  • Request Logging                            │     │
│  │  • Path-based Routing                         │     │
│  └──────────────────────────────────────────────┘     │
└──────┬────────────────────────┬────────────────────────┘
       │                        │
       ↓                        ↓
┌──────────────┐         ┌──────────────┐
│    Admin     │         │ LLM Backend  │
│   Service    │         │   Service    │
│  (Port 8002) │         │  (Port 8001) │
│              │         │              │
│ • API Key    │         │ • vLLM Proxy │
│   관리 UI     │         │ • /v1/...    │
│ • 사용량 통계  │         │   endpoints  │
│ • REST API   │         │              │
└──────┬───────┘         └──────┬───────┘
       │                        │
       ↓                        ↓
┌────────────┐           ┌─────────┐
│  Database  │           │  vLLM   │
│  (SQLite)  │           │ Server  │
│            │           │(Port    │
│ • API Keys │           │ 8100)   │
│ • Users    │           │         │
│ • Logs     │           │  GPU    │
└────────────┘           └─────────┘
```

## 서비스 구성

### 1. Gateway Service (Port 8000)
- **역할**: 인증, Rate Limiting, 라우팅
- **기능**:
  - API Key 검증 (Database)
  - 사용자별 Rate Limiting
  - Request/Response 로깅
  - `/v1/*` → LLM Backend로 프록시
  - `/admin/*` → Admin Service로 프록시

### 2. Admin Service (Port 8002)
- **역할**: API Key 관리
- **기능**:
  - 웹 UI 대시보드
  - API Key CRUD
  - 사용량 통계 조회
  - 관리자 인증 (JWT)
- **접근**: `http://localhost:8000/admin/` (Gateway를 통해)

### 3. LLM Backend Service (Port 8001)
- **역할**: vLLM 프록시
- **기능**:
  - `/v1/completions`
  - `/v1/chat/completions`
  - `/v1/models`
- **특징**: 인증 없음 (Gateway가 처리), Internal Only

### 4. vLLM Server (Port 8100)
- GPU 기반 LLM 추론 서버
- OpenAI 호환 API 제공

## 빠른 시작

### Docker Compose (추천)

```bash
# 전체 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f gateway
docker-compose logs -f admin
docker-compose logs -f llm-backend

# 서비스 상태 확인
curl http://localhost:8000/health
```

### 개별 서비스 실행 (개발용)

```bash
# 의존성 설치
pip install -r gateway/requirements.txt
pip install -r admin/requirements.txt
pip install -r llm_backend/requirements.txt
pip install -r shared/requirements.txt

# 각 터미널에서 실행

# Terminal 1: Admin Service
python -m uvicorn admin.main:app --host 0.0.0.0 --port 8002

# Terminal 2: LLM Backend
python -m uvicorn llm_backend.main_simple:app --host 0.0.0.0 --port 8001

# Terminal 3: Gateway
python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000
```

## 사용 가이드

### 1. 관리자 로그인

```bash
# 브라우저에서 접속
http://localhost:8000/admin/index.html

# 기본 계정
Username: admin
Password: admin123
```

**⚠️ 프로덕션 환경에서는 반드시 비밀번호를 변경하세요!**

### 2. API Key 생성

웹 UI에서:
1. "Create New Key" 버튼 클릭
2. User ID 입력 (예: `dev-team`)
3. Tier 선택 (Free/Standard/Premium)
4. 설명 입력 (선택)
5. 만료일 설정 (선택)
6. "Create" 클릭
7. 생성된 API Key 복사 (다시 보이지 않음!)

또는 API로:

```bash
# 로그인
TOKEN=$(curl -X POST http://localhost:8000/admin/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# API Key 생성
curl -X POST http://localhost:8000/admin/api/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "dev-team",
    "tier": "premium",
    "description": "Development team key"
  }'
```

### 3. LLM API 사용

#### Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-internal-YOUR-KEY-HERE" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100
  }'
```

#### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-internal-YOUR-KEY-HERE",
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

Tier별 요청 제한:

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

## API 엔드포인트

### Gateway (Port 8000)

| 엔드포인트 | 설명 | 인증 필요 |
|----------|------|----------|
| `GET /health` | 전체 시스템 상태 | ❌ |
| `POST /v1/chat/completions` | Chat 완성 | ✅ API Key |
| `POST /v1/completions` | Text 완성 | ✅ API Key |
| `GET /v1/models` | 모델 목록 | ✅ API Key |
| `GET /admin/index.html` | 관리자 UI | ❌ |
| `POST /admin/api/login` | 관리자 로그인 | ❌ |
| `GET /admin/api/keys` | API Key 목록 | ✅ Admin Token |
| `POST /admin/api/keys` | API Key 생성 | ✅ Admin Token |
| `PUT /admin/api/keys/{id}` | API Key 수정 | ✅ Admin Token |
| `DELETE /admin/api/keys/{id}` | API Key 삭제 | ✅ Admin Token |
| `GET /admin/api/usage` | 사용량 통계 | ✅ Admin Token |

## 프로젝트 구조

```
authz/
├── gateway/                    # Gateway Service
│   ├── main.py                # FastAPI app with routing
│   ├── auth.py                # API key authentication
│   ├── rate_limiter.py        # Rate limiting logic
│   ├── requirements.txt
│   └── Dockerfile.gateway
│
├── admin/                     # Admin Service
│   ├── main.py               # Admin API
│   ├── ui/                   # Web UI
│   │   ├── index.html        # Dashboard HTML
│   │   └── app.js            # Dashboard JavaScript
│   ├── requirements.txt
│   └── Dockerfile.admin
│
├── llm_backend/              # LLM Backend Service
│   ├── main_simple.py        # vLLM proxy (no auth)
│   ├── vllm_client.py        # vLLM HTTP client
│   ├── models.py             # Pydantic models
│   ├── requirements.txt
│   └── Dockerfile.llm-backend
│
├── shared/                   # 공통 라이브러리
│   ├── database.py           # SQLAlchemy setup
│   ├── models.py             # DB models
│   ├── crud.py               # CRUD operations
│   ├── config.py             # 공통 설정
│   └── requirements.txt
│
├── docker-compose.yml        # 전체 오케스트레이션
├── .env.example              # 환경 변수 템플릿
└── README.md                 # 이 문서
```

## 데이터베이스 스키마

### API Keys 테이블
- `id`: Primary key
- `key`: API key string (unique)
- `user_id`: 사용자 ID
- `tier`: free/standard/premium
- `is_active`: 활성화 상태
- `created_at`, `updated_at`: 타임스탬프
- `expires_at`: 만료일 (선택)
- `description`: 설명

### Request Logs 테이블
- `id`: Primary key
- `user_id`: 사용자 ID
- `api_key_id`: API Key ID
- `endpoint`: API 경로
- `method`: HTTP method
- `status_code`: 응답 코드
- `duration_ms`: 소요 시간
- `prompt_tokens`, `completion_tokens`: 토큰 사용량
- `model`: 사용한 모델
- `timestamp`: 요청 시각

### Admin Users 테이블
- `id`: Primary key
- `username`: 관리자 아이디
- `hashed_password`: 해시된 비밀번호
- `email`: 이메일
- `is_active`: 활성화 상태
- `last_login`: 마지막 로그인

## 환경 변수

`.env` 파일:

```bash
# Database
DATABASE_URL=sqlite:///./llm_api.db

# Gateway
GATEWAY_PORT=8000

# Admin
ADMIN_PORT=8002
ADMIN_SECRET_KEY=your-secret-key-here

# LLM Backend
LLM_BACKEND_PORT=8001
LLM_BACKEND_URL=http://localhost:8001

# vLLM
VLLM_BASE_URL=http://localhost:8100
VLLM_DEFAULT_MODEL=meta-llama/Llama-2-7b-chat-hf

# Rate Limits
RATE_LIMIT_PREMIUM_PER_MINUTE=100
RATE_LIMIT_PREMIUM_PER_HOUR=1000
RATE_LIMIT_STANDARD_PER_MINUTE=30
RATE_LIMIT_STANDARD_PER_HOUR=300
RATE_LIMIT_FREE_PER_MINUTE=10
RATE_LIMIT_FREE_PER_HOUR=100
```

## 모니터링

### 로그 확인

```bash
# Docker 로그
docker-compose logs -f gateway
docker-compose logs -f admin
docker-compose logs -f llm-backend

# 로그 파일 (개별 실행 시)
tail -f logs/gateway.log
```

### Health Checks

```bash
# 전체 시스템
curl http://localhost:8000/health

# 개별 서비스
curl http://localhost:8001/health  # LLM Backend
curl http://localhost:8002/health  # Admin
```

### 사용량 통계

웹 UI의 Dashboard 또는:

```bash
curl http://localhost:8000/admin/api/usage?days=7 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 보안 고려사항

### 프로덕션 배포 전 체크리스트

- [ ] Admin 기본 비밀번호 변경
- [ ] `ADMIN_SECRET_KEY` 환경 변수 변경
- [ ] HTTPS 적용 (Nginx reverse proxy)
- [ ] 내부망에서만 접근 가능하도록 방화벽 설정
- [ ] SQLite 대신 PostgreSQL 사용 권장
- [ ] API Key 저장소를 Secrets Manager로 이전
- [ ] Rate limiting 값 조정
- [ ] 로그 보관 정책 설정
- [ ] Backup 설정

### Nginx Reverse Proxy 예시

```nginx
server {
    listen 443 ssl;
    server_name llm-api.company.internal;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 긴 요청 타임아웃
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

## 트러블슈팅

### Gateway가 LLM Backend에 연결하지 못함

```bash
# 네트워크 확인
docker network inspect llm-api-network

# LLM Backend 상태 확인
curl http://localhost:8001/health

# 환경 변수 확인
docker exec gateway-service env | grep LLM_BACKEND_URL
```

### Admin UI에서 로그인 실패

```bash
# Database 확인
sqlite3 llm_api.db "SELECT * FROM admin_users;"

# 기본 admin 계정 재생성
docker exec -it admin-service python -c "
from shared.database import SessionLocal, init_db
from shared import crud
init_db()
db = SessionLocal()
crud.create_admin_user(db, 'admin', 'admin123')
"
```

### vLLM 연결 실패

```bash
# vLLM 상태 확인
curl http://localhost:8100/v1/models

# vLLM 로그 확인
docker logs vllm-server

# GPU 확인
nvidia-smi
```

## 개발 가이드

### 새 서비스 추가

1. 서비스 디렉토리 생성 (예: `new_service/`)
2. `Dockerfile.new-service` 생성
3. `docker-compose.yml`에 서비스 추가
4. Gateway에 라우팅 추가

### 데이터베이스 마이그레이션

```bash
# Alembic 설정 (선택)
pip install alembic
alembic init alembic
# alembic/env.py 수정
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## FAQ

**Q: API Key는 어디에 저장되나요?**
A: SQLite 데이터베이스 (`llm_api.db`)에 저장됩니다. 프로덕션에서는 PostgreSQL이나 Secrets Manager 사용을 권장합니다.

**Q: Rate limiting은 분산 환경에서 작동하나요?**
A: 현재는 인메모리 방식입니다. Redis 기반 분산 rate limiting으로 업그레이드 가능합니다.

**Q: 여러 vLLM 서버를 사용할 수 있나요?**
A: Gateway에 로드 밸런싱 로직을 추가하여 가능합니다.

**Q: 사용량 기반 과금을 구현할 수 있나요?**
A: `request_logs` 테이블의 토큰 사용량 데이터를 활용하여 구현 가능합니다.

## 라이선스

내부 사용 전용. 외부 배포 금지.

## 지원

- 이슈: GitHub Issues
- 사내 Slack: #llm-api-support
- 이메일: llm-support@company.com
