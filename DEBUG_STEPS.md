# Docker Compose 반응 없음 - 디버깅 단계

## 즉시 실행해야 할 명령어:

### 1단계: 현재 상태 확인
```bash
# 실행 중인 컨테이너 확인
docker ps -a

# 멈춰있는 프로세스 강제 종료
docker compose down -v
killall docker-compose 2>/dev/null
```

### 2단계: 로그 확인
```bash
# 백그라운드에서 실행하고 로그 확인
docker compose up -d
docker compose logs -f

# 또는 특정 파일에 덮어쓰기 모드로 실행
docker compose up --build 2>&1 | tee docker-build.log
```

### 3단계: 개별 서비스 테스트
```bash
# Admin 서비스만 빌드
docker compose build admin
docker compose up admin

# 성공하면 다음 서비스
docker compose build llm-backend
docker compose up llm-backend
```

### 4단계: 간단한 테스트 설정 사용
```bash
# vLLM 없는 최소 설정
docker compose -f docker-compose.test.yml up --build
```

## Python 직접 실행 (Docker 없이)

### 필수 패키지 설치:
```bash
pip install -r shared/requirements.txt
pip install -r admin/requirements.txt
pip install -r gateway/requirements.txt
pip install -r llm_backend/requirements.txt
```

### import 테스트:
```bash
python3 test_imports.py
```

### Admin 서비스만 직접 실행:
```bash
cd /path/to/authz
export DATABASE_URL="sqlite:///./test.db"
export USE_MOCK_EMAIL="true"
python -m uvicorn admin.main:app --reload --port 8002
```

성공하면 브라우저에서 http://localhost:8002/health 확인

### Gateway 서비스 직접 실행:
```bash
export DATABASE_URL="sqlite:///./test.db"
export LLM_BACKEND_URL="http://localhost:8001"
export ADMIN_HOST="localhost"
export ADMIN_PORT="8002"
python -m uvicorn gateway.main:app --reload --port 8000
```

### LLM Backend 서비스 직접 실행:
```bash
export VLLM_BASE_URL="http://localhost:8100"
export VLLM_DEFAULT_MODEL="test-model"
python -m uvicorn llm_backend.main:app --reload --port 8001
```

## 알려주셔야 할 정보:

1. **정확히 어떤 명령어를 실행했나요?**
   - `docker compose up`
   - `docker compose up --build`
   - `docker-compose up` (하이픈 있음)

2. **화면에 무엇이 표시되나요?**
   - 아무것도 안 나옴
   - 빌드 중 메시지만 나오고 멈춤
   - 에러 메시지 (있다면 전체 복사)

3. **Ctrl+C로 종료할 수 있나요?**
   - 예 / 아니오

4. **다른 터미널에서 `docker ps -a` 실행하면?**
   - 컨테이너가 보이나요?
   - STATUS가 뭔가요? (Up, Exited, Restarting 등)

5. **이전 커밋으로 되돌리면 작동하나요?**
```bash
git checkout 59276c0  # 이전에 작동했던 커밋
docker compose down -v
docker compose up --build
```

## 빠른 원인 파악:

### 네트워크 문제
```bash
docker network ls
docker network inspect authz_llm-api-network
```

### 이미지 문제
```bash
docker images | grep authz
docker rmi $(docker images | grep 'authz' | awk '{print $3}')  # 이미지 전체 삭제
docker compose build --no-cache  # 캐시 없이 재빌드
```

### GPU 문제 (nvidia-docker)
```bash
nvidia-smi  # GPU 확인
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

GPU 없으면 docker-compose.yml에서 vLLM 관련 부분 주석 처리:
```yaml
# vllm:
#   ...전체 주석...
```

그리고 llm-backend의 depends_on에서 vllm 제거:
```yaml
llm-backend:
  # depends_on:
  #   vllm:
  #     condition: service_healthy
```
