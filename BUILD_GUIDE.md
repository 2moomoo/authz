# Docker Compose 빌드 가이드

## 올바른 빌드 방법

### 방법 1: 가장 간단한 방법 (권장)

```bash
docker compose up --build
```

빌드 진행 중 출력이 없어 보여도 **기다리세요**. 2-5분 정도 걸립니다.

### 방법 2: 출력 확인하며 빌드

```bash
# 빌드만 먼저 (출력이 나옴)
docker compose build

# 빌드 완료 후 실행
docker compose up
```

### 방법 3: 서비스별 개별 빌드

```bash
# 하나씩 빌드하면서 진행상황 확인
docker compose build admin
docker compose build llm-backend
docker compose build gateway

# 모두 실행
docker compose up
```

### 방법 4: verbose 모드

```bash
docker compose --verbose build
docker compose up
```

## 첫 빌드 시간

- **Admin 서비스**: ~1분
- **LLM Backend 서비스**: ~1-2분
- **Gateway 서비스**: ~1-2분
- **총 첫 빌드**: 3-5분

다음 빌드부터는 캐시로 인해 10-30초로 단축됩니다.

## 빌드가 진행 중인지 확인

다른 터미널을 열어서:

```bash
# CPU/메모리 사용량 확인 (빌드 중이면 높음)
docker stats

# 또는 프로세스 확인
docker ps -a
```

## GPU 없이 테스트 (vLLM 제외)

```bash
# vLLM 없는 버전으로 빌드
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml up
```

## 문제 해결

### 빌드가 정말 멈췄다면

```bash
# 전부 정리하고 다시 시작
docker compose down -v
docker compose build --no-cache
docker compose up
```

### 개별 서비스 테스트

```bash
# Admin만 빌드하고 실행
docker compose up --build admin

# 성공하면 다음 서비스
docker compose up --build llm-backend

# 마지막으로 Gateway
docker compose up --build gateway
```

### 로그를 파일로 저장

```bash
docker compose build 2>&1 | tee build.log
docker compose up 2>&1 | tee run.log
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

## 결론

**가장 간단한 명령어:**

```bash
docker compose build
docker compose up
```

첫 빌드는 3-5분 걸립니다. 출력이 없어도 **기다리세요**.
