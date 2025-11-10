#!/bin/bash
# WSL2에서 GPU 사용 설정 스크립트

echo "=========================================="
echo "WSL2 GPU 설정 시작"
echo "=========================================="
echo

# 1. Windows에서 NVIDIA 드라이버 확인
echo "[1] Windows NVIDIA 드라이버 확인"
echo "    Windows에서 최신 NVIDIA 드라이버가 설치되어 있어야 합니다."
echo "    https://www.nvidia.com/Download/index.aspx"
echo "    설치 완료 후 Enter를 누르세요..."
read

# 2. NVIDIA Container Toolkit 설치
echo
echo "[2] NVIDIA Container Toolkit 설치"
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# GPG 키 추가
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Repository 추가
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 패키지 설치
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

echo
echo "[3] Docker 설정 업데이트"
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

echo
echo "[4] 테스트"
echo "Docker에서 GPU를 테스트합니다..."
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

if [ $? -eq 0 ]; then
    echo
    echo "=========================================="
    echo "✓ GPU 설정 완료!"
    echo "=========================================="
    echo
    echo "이제 다음 명령어로 실행하세요:"
    echo "  docker compose down -v"
    echo "  docker compose up --build"
else
    echo
    echo "=========================================="
    echo "✗ GPU 설정 실패"
    echo "=========================================="
    echo
    echo "문제 해결:"
    echo "  1. Windows에서 NVIDIA 드라이버가 제대로 설치되었는지 확인"
    echo "  2. WSL2를 재시작: wsl --shutdown (Windows PowerShell에서)"
    echo "  3. Docker Desktop을 재시작"
fi
