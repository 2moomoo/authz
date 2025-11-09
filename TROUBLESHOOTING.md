# 문제 해결 가이드

## docker compose up 실행 시 반응이 없는 경우

### 원인 1: vLLM GPU 요구사항
vLLM 서비스는 NVIDIA GPU와 nvidia-docker를 필요로 합니다.

**확인 방법:**
```bash
# GPU 확인
nvidia-smi

# nvidia-docker 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**해결책 1: GPU 없이 테스트**
```bash
# vLLM 없이 다른 서비스만 테스트
docker compose -f docker-compose.test.yml up --build

# 또는 개발 모드로 실행 (외부 vLLM 사용)
docker compose -f docker-compose.dev.yml up --build
```

**해결책 2: vLLM CPU 모드로 실행**
`docker-compose.yml`에서 vLLM 서비스 수정:
```yaml
vllm:
  image: vllm/vllm-openai:latest
  # runtime: nvidia  # 주석 처리
  command: >
    --model meta-llama/Llama-2-7b-chat-hf
    --host 0.0.0.0
    --port 8100
  # deploy 섹션 전체 주석 처리
```

### 원인 2: Healthcheck 대기 중
서비스들이 healthcheck를 통과할 때까지 대기 중일 수 있습니다.

**확인 방법:**
```bash
# 다른 터미널에서 로그 확인
docker compose logs -f

# 특정 서비스 로그만 확인
docker compose logs -f vllm
docker compose logs -f llm-backend
```

**해결책:**
Healthcheck 타임아웃을 늘리거나 제거:
```yaml
# vLLM healthcheck 수정
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8100/v1/models"]  # /health 대신 /v1/models
  start_period: 300s  # 5분으로 증가
```

### 원인 3: 포트 충돌
8000, 8001, 8002, 8100 포트가 이미 사용 중일 수 있습니다.

**확인 방법:**
```bash
# Linux/Mac
sudo lsof -i :8000
sudo lsof -i :8001
sudo lsof -i :8002
sudo lsof -i :8100

# Windows
netstat -ano | findstr :8000
```

**해결책:**
사용 중인 프로세스 종료 또는 `docker-compose.yml`에서 포트 변경:
```yaml
ports:
  - "9000:8000"  # 외부 포트 변경
```

### 원인 4: 이전 컨테이너 잔존
이전 실행의 컨테이너가 남아있을 수 있습니다.

**해결책:**
```bash
# 모든 컨테이너 정리
docker compose down -v

# 강제 재시작
docker compose down -v && docker compose up --build --force-recreate
```

### 원인 5: 디스크 공간 부족
Docker 이미지와 빌드 캐시가 디스크를 가득 채웠을 수 있습니다.

**확인 방법:**
```bash
df -h
docker system df
```

**해결책:**
```bash
# Docker 정리
docker system prune -a

# 볼륨까지 전부 정리 (주의: 데이터 손실)
docker system prune -a --volumes
```

## 빌드 오류

### ModuleNotFoundError
Python 패키지를 찾을 수 없는 경우:
```bash
# 캐시 없이 재빌드
docker compose build --no-cache

# 특정 서비스만 재빌드
docker compose build --no-cache gateway
```

### Import 오류
shared 모듈을 찾을 수 없는 경우, Dockerfile의 COPY 경로 확인:
```dockerfile
# 올바른 경로
COPY shared/ ./shared/
COPY gateway/ ./gateway/
```

## 런타임 오류

### Database is locked
SQLite를 여러 서비스가 동시에 접근할 때 발생:
```bash
# PostgreSQL로 전환 권장
# .env에서 DATABASE_URL 변경
DATABASE_URL=postgresql://user:password@localhost:5432/llm_api
```

### Connection refused to vLLM
vLLM 서비스가 아직 준비되지 않음:
```bash
# vLLM 로그 확인
docker compose logs vllm

# vLLM만 먼저 실행
docker compose up vllm
# 다른 터미널에서
curl http://localhost:8100/v1/models
```

## 서비스별 독립 테스트

### Admin 서비스만 실행
```bash
cd admin
pip install -r requirements.txt -r ../shared/requirements.txt
DATABASE_URL=sqlite:///./test.db python -m uvicorn admin.main:app --reload --port 8002
```

### Gateway 서비스만 실행
```bash
cd gateway
pip install -r requirements.txt -r ../shared/requirements.txt
LLM_BACKEND_URL=http://localhost:8001 python -m uvicorn gateway.main:app --reload --port 8000
```

### LLM Backend 서비스만 실행
```bash
cd llm_backend
pip install -r requirements.txt -r ../shared/requirements.txt
VLLM_BASE_URL=http://localhost:8100 python -m uvicorn llm_backend.main:app --reload --port 8001
```

## 로그 레벨 증가

더 자세한 로그를 보려면:
```bash
# Docker Compose 로그
docker compose up --build --verbose

# 서비스 로그 실시간 확인
docker compose logs -f --tail=100

# 특정 서비스만
docker compose logs -f gateway llm-backend admin
```

## 완전 초기화

모든 것을 처음부터 다시 시작:
```bash
# 1. 모든 컨테이너와 볼륨 삭제
docker compose down -v

# 2. 이미지 삭제
docker rmi $(docker images | grep 'authz' | awk '{print $3}')

# 3. 데이터베이스 파일 삭제
rm -f llm_api.db llm_api.db-journal

# 4. 재빌드 및 실행
docker compose up --build
```

## 추가 도움

위 방법으로 해결되지 않으면:
1. `docker compose logs -f > logs.txt`로 전체 로그 저장
2. `docker compose config`로 최종 설정 확인
3. 각 서비스를 Docker 없이 로컬에서 실행하여 테스트
