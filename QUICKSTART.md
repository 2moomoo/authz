# 🚀 빠른 시작 가이드

## 1️⃣ Docker Compose로 실행 (가장 간단)

```bash
# 전체 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 상태 확인
curl http://localhost:8000/health
```

**완료!** 이제 사용할 수 있습니다.

---

## 2️⃣ API Key 발급 받기

### 방법 A: 웹 브라우저 (추천)

```
1. 브라우저에서 접속: http://localhost:8000/admin/user.html

2. 회사 이메일 입력: you@company.com

3. 터미널에서 검증 코드 확인:
   docker-compose logs admin | grep "VERIFICATION CODE"

4. 6자리 코드 입력

5. API Key 복사!
```

### 방법 B: curl 명령어

```bash
# 1. 검증 코드 요청
curl -X POST http://localhost:8000/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"email":"you@company.com"}'

# 2. 터미널에서 코드 확인
docker-compose logs admin | grep "VERIFICATION CODE"

# 3. 검증 코드로 API Key 받기
curl -X POST http://localhost:8000/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"email":"you@company.com","code":"123456"}'
```

---

## 3️⃣ LLM API 사용하기

```bash
# API Key를 환경 변수로 저장
export API_KEY="sk-internal-xxxxx"

# Chat API 호출
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Python 예시

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-internal-xxxxx",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="llama-2-7b",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

---

## 4️⃣ 관리자 대시보드

```
URL: http://localhost:8000/admin/index.html

기본 계정:
- Username: admin
- Password: admin123

할 수 있는 일:
- 전체 API Key 조회
- 키 활성화/비활성화
- Tier 변경 (standard → premium)
- 사용량 통계 확인
```

---

## 📋 포트 정리

| 서비스 | 포트 | 접속 방법 |
|--------|------|-----------|
| **Gateway** | 8000 | http://localhost:8000 |
| **사용자 포털** | 8000 | http://localhost:8000/admin/user.html |
| **관리자 포털** | 8000 | http://localhost:8000/admin/index.html |
| LLM Backend | 8001 | 내부 전용 |
| Admin Service | 8002 | 내부 전용 |
| vLLM Server | 8100 | 내부 전용 |

---

## 🛠️ 개별 서비스 실행 (개발용)

```bash
# 1. 의존성 설치
pip install -r shared/requirements.txt
pip install -r gateway/requirements.txt
pip install -r admin/requirements.txt
pip install -r llm_backend/requirements.txt

# 2. 각 터미널에서 실행

# Terminal 1: Admin
python -m uvicorn admin.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 2: LLM Backend
python -m uvicorn llm_backend.main_simple:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3: Gateway
python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ⚙️ 설정 변경

### 이메일 도메인 화이트리스트

`.env` 파일 생성:
```bash
cp .env.example .env
```

수정:
```bash
ALLOWED_EMAIL_DOMAINS=["yourcompany.com","yourcompany.net"]
```

### 실제 SMTP 사용

```bash
USE_MOCK_EMAIL=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourcompany.com
SMTP_PASSWORD=your-app-password
```

---

## 🔍 트러블슈팅

### 포트 충돌
```bash
# 프로세스 확인 및 종료
lsof -i :8000
kill -9 <PID>
```

### Docker 재시작
```bash
docker-compose down
docker-compose up -d --build
```

### Database 초기화
```bash
rm llm_api.db
docker-compose restart gateway admin
```

### 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스
docker-compose logs -f gateway
docker-compose logs -f admin
```

---

## 📚 추가 문서

- 전체 문서: [README.md](README.md)
- 아키텍처 설명: README.md의 "아키텍처" 섹션
- API 레퍼런스: README.md의 "API 엔드포인트" 섹션

---

## ✅ 체크리스트

시작하기 전:
- [ ] Docker 설치됨
- [ ] Docker Compose 설치됨
- [ ] 포트 8000-8002, 8100 사용 가능

첫 실행 시:
- [ ] `docker-compose up -d` 실행
- [ ] http://localhost:8000/health 확인
- [ ] 사용자 포털에서 API Key 발급
- [ ] LLM API 테스트

프로덕션 배포 시:
- [ ] Admin 기본 비밀번호 변경
- [ ] `ADMIN_SECRET_KEY` 환경 변수 변경
- [ ] 허용 이메일 도메인 설정
- [ ] 실제 SMTP 설정
- [ ] HTTPS 적용 (Nginx)
