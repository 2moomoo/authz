# docker compose build가 반응이 없을 때

## 즉시 실행할 것

### 1. 진단 스크립트 실행
```bash
./diagnose.sh
```

이 스크립트가 어디서 문제인지 알려줍니다.

### 2. 일반적인 원인들

#### 원인 1: Docker 데몬이 실행되지 않음

**확인:**
```bash
docker info
```

**에러가 나면:**
```bash
# Linux
sudo systemctl start docker
sudo systemctl enable docker

# Mac/Windows
# Docker Desktop 앱을 실행하세요
```

#### 원인 2: docker-compose vs docker compose

**두 가지 모두 시도:**
```bash
# 방법 1 (새 버전)
docker compose build

# 방법 2 (구 버전)
docker-compose build
```

#### 원인 3: 권한 문제 (Linux)

```bash
# Docker를 sudo 없이 실행하도록 설정
sudo usermod -aG docker $USER
newgrp docker

# 또는 sudo 사용
sudo docker compose build
```

#### 원인 4: BuildKit 문제

BuildKit을 비활성화:
```bash
DOCKER_BUILDKIT=0 docker compose build
```

#### 원인 5: 이전 빌드가 멈춤

```bash
# 모든 컨테이너 중지
docker stop $(docker ps -aq)

# 빌드 캐시 정리
docker builder prune -a

# 다시 시도
docker compose build
```

### 3. 최소한의 테스트

**Docker가 작동하는지 확인:**
```bash
docker run hello-world
```

이것도 반응이 없으면 Docker 설치에 문제가 있습니다.

### 4. 멀티스테이지 빌드 없이 테스트

임시로 간단한 Dockerfile을 사용해봅시다:

**admin/Dockerfile을 임시로 수정:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY admin/requirements.txt ./admin/
COPY shared/requirements.txt ./shared/
RUN pip install -r admin/requirements.txt -r shared/requirements.txt
COPY admin/ ./admin/
COPY shared/ ./shared/
EXPOSE 8002
CMD ["python", "-m", "uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

**이것만 빌드:**
```bash
docker build -t test-admin -f admin/Dockerfile .
```

반응이 있나요?

### 5. Verbose 모드

```bash
docker compose --verbose build 2>&1 | tee build-debug.log
```

출력을 `build-debug.log` 파일에 저장합니다.

### 6. 환경 변수 확인

```bash
env | grep -i docker
```

DOCKER_HOST나 다른 환경 변수가 잘못 설정되어 있을 수 있습니다.

### 7. 로그 확인

```bash
# Linux
journalctl -u docker -n 50

# Mac/Windows
# Docker Desktop 앱의 Troubleshoot > Show logs
```

## 정확한 상황 알려주기

다음 정보를 알려주세요:

1. **OS는?**
   - Linux (배포판은?)
   - Mac (Intel/M1?)
   - Windows (WSL2?)

2. **`docker --version` 출력:**

3. **`docker info` 실행하면?**
   - 정상 출력
   - 에러 (어떤 에러?)
   - 반응 없음

4. **`docker run hello-world` 실행하면?**
   - 성공
   - 에러
   - 반응 없음

5. **`./diagnose.sh` 출력은?**

이 정보를 주시면 정확한 해결책을 드릴 수 있습니다.
