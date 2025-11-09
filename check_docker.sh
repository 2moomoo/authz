#!/bin/bash
# Docker Compose 진단 스크립트

echo "=========================================="
echo "Docker Compose 진단"
echo "=========================================="
echo

# 1. Docker 버전 확인
echo "[1] Docker 버전:"
docker --version 2>&1
docker compose version 2>&1
echo

# 2. 실행 중인 컨테이너 확인
echo "[2] 실행 중인 컨테이너:"
docker ps -a 2>&1
echo

# 3. 포트 사용 확인
echo "[3] 포트 사용 확인:"
for port in 8000 8001 8002 8100; do
    if command -v lsof &> /dev/null; then
        echo "  Port $port:"
        lsof -i :$port 2>&1 | head -5
    elif command -v netstat &> /dev/null; then
        echo "  Port $port:"
        netstat -tuln | grep ":$port " 2>&1
    else
        echo "  (lsof/netstat not available)"
        break
    fi
done
echo

# 4. Docker Compose 설정 검증
echo "[4] Docker Compose 설정 검증:"
docker compose config 2>&1 | head -20
echo "..."
echo

# 5. 디스크 공간
echo "[5] 디스크 공간:"
df -h . 2>&1
echo

# 6. Docker 디스크 사용량
echo "[6] Docker 디스크 사용량:"
docker system df 2>&1
echo

# 7. 최근 Docker 로그
echo "[7] 최근 Docker Compose 로그 (마지막 20줄):"
docker compose logs --tail=20 2>&1
echo

echo "=========================================="
echo "진단 완료"
echo "=========================================="
echo
echo "문제가 계속되면 다음을 시도하세요:"
echo "  1. docker compose down -v"
echo "  2. docker compose -f docker-compose.test.yml up --build"
echo "  3. 개별 서비스 로그: docker compose logs -f [service-name]"
