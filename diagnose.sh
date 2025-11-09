#!/bin/bash
# Docker 환경 진단 스크립트

echo "=========================================="
echo "Docker 환경 진단 시작"
echo "=========================================="
echo

# 1. Docker 설치 확인
echo "[1] Docker 설치 확인"
if command -v docker &> /dev/null; then
    docker --version
    echo "✓ Docker 설치됨"
else
    echo "✗ Docker가 설치되지 않았습니다"
    exit 1
fi
echo

# 2. Docker 데몬 실행 확인
echo "[2] Docker 데몬 실행 확인"
if docker info &> /dev/null; then
    echo "✓ Docker 데몬 실행 중"
else
    echo "✗ Docker 데몬이 실행되지 않았습니다"
    echo "다음 명령어로 시작하세요:"
    echo "  Linux: sudo systemctl start docker"
    echo "  Mac: Docker Desktop 앱 실행"
    echo "  Windows: Docker Desktop 앱 실행"
    exit 1
fi
echo

# 3. Docker Compose 확인
echo "[3] Docker Compose 확인"
if docker compose version &> /dev/null; then
    docker compose version
    echo "✓ Docker Compose 사용 가능"
elif docker-compose --version &> /dev/null; then
    docker-compose --version
    echo "✓ docker-compose (하이픈 버전) 사용 가능"
    echo "! 'docker compose' 대신 'docker-compose' 사용하세요"
else
    echo "✗ Docker Compose가 설치되지 않았습니다"
    exit 1
fi
echo

# 4. docker-compose.yml 유효성 검사
echo "[4] docker-compose.yml 유효성 검사"
if [ -f "docker-compose.yml" ]; then
    echo "✓ docker-compose.yml 파일 존재"
    if docker compose config &> /dev/null || docker-compose config &> /dev/null; then
        echo "✓ docker-compose.yml 구문 정상"
    else
        echo "✗ docker-compose.yml에 오류가 있습니다"
        docker compose config 2>&1 || docker-compose config 2>&1
        exit 1
    fi
else
    echo "✗ docker-compose.yml 파일이 없습니다"
    exit 1
fi
echo

# 5. 디스크 공간 확인
echo "[5] 디스크 공간 확인"
df -h . | tail -1
echo

# 6. 실행 중인 컨테이너 확인
echo "[6] 실행 중인 컨테이너"
docker ps -a
echo

# 7. Docker 이미지 확인
echo "[7] Docker 이미지"
docker images | head -10
echo

# 8. 네트워크 확인
echo "[8] Docker 네트워크"
docker network ls
echo

echo "=========================================="
echo "진단 완료"
echo "=========================================="
echo
echo "다음 단계:"
echo "1. 위에서 모든 항목이 ✓ 이면:"
echo "   docker compose build admin"
echo
echo "2. 오류가 있으면 해당 항목을 먼저 해결하세요"
