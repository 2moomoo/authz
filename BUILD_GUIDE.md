# Docker Compose 빌드 가이드

## 올바른 빌드 방법

Docker는 빌드 진행상황을 **버퍼링**하기 때문에 출력이 늦게 나올 수 있습니다.

### 방법 1: 진행상황 실시간 출력 (권장)

```bash
DOCKER_BUILDKIT=1 docker compose build --progress=plain
docker compose up
```

또는 한 번에:

```bash
DOCKER_BUILDKIT=1 docker compose up --build --progress=plain
```

### 방법 2: 서비스별 개별 빌드

```bash
# Admin 먼저 빌드 (가장 빠름)
docker compose build --progress=plain admin

# LLM Backend 빌드
docker compose build --progress=plain llm-backend

# Gateway 빌드
docker compose build --progress=plain gateway

# 모두 실행
docker compose up
```

### 방법 3: 캐시 없이 깨끗하게 빌드

```bash
docker compose build --no-cache --progress=plain
docker compose up
```

## 최적화된 Dockerfile의 장점

현재 **멀티스테이지 빌드** 사용 중:

### 장점:
1. **이미지 크기 30-40% 감소**
   - 싱글스테이지: ~350-400MB
   - 멀티스테이지: ~220-250MB

2. **보안 강화**
   - Non-root user (appuser:1000) 사용
   - 빌드 도구(gcc 등) 최종 이미지에 포함 안 됨

3. **빌드/런타임 분리**
   - Builder 스테이지: 컴파일 도구 포함
   - Final 스테이지: 런타임만 포함

### 빌드 시간:
- 첫 빌드: 2-3분 (패키지 다운로드)
- 재빌드: 10-30초 (캐시 사용)

## GPU 없이 테스트

GPU가 없거나 vLLM을 사용하지 않는다면:

```bash
# vLLM 없는 테스트 버전
docker compose -f docker-compose.test.yml up --build --progress=plain

# 또는 vLLM 제외하고 빌드
docker compose up --build --progress=plain admin llm-backend gateway
```

## 문제 해결

### "반응이 없어요"

실제로는 빌드가 진행 중입니다. `--progress=plain` 옵션을 사용하세요.

```bash
# 이렇게 하면 모든 출력이 실시간으로 나옵니다
DOCKER_BUILDKIT=1 docker compose build --progress=plain
```

### 빌드가 정말 멈췄는지 확인

다른 터미널에서:

```bash
# CPU 사용량 확인 (빌드 중이면 높을 것)
docker stats

# 실행 중인 빌드 컨테이너 확인
docker ps -a
```

### 빌드 로그 저장

```bash
docker compose build --progress=plain 2>&1 | tee build.log
```

## 성능 비교

### 싱글스테이지 (간단한 버전)
```dockerfile
FROM python:3.11-slim
# ... 모든 작업
```
- 빌드: 빠름 (1-2분)
- 이미지: 큼 (~350MB)
- 보안: 낮음 (root 사용)

### 멀티스테이지 (최적화 버전) ✓
```dockerfile
FROM python:3.11-slim as builder
# ... 빌드
FROM python:3.11-slim
# ... 런타임만
```
- 빌드: 약간 느림 (2-3분)
- 이미지: 작음 (~220MB)
- 보안: 높음 (non-root)

## 결론

**멀티스테이지 빌드를 사용하세요.**

단, 빌드 시 반드시 `--progress=plain` 옵션을 사용하여 진행상황을 확인하세요.

```bash
# 최종 권장 명령어
DOCKER_BUILDKIT=1 docker compose up --build --progress=plain
```
