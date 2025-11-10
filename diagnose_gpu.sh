#!/bin/bash
# WSL2 GPU 진단 스크립트

echo "=========================================="
echo "WSL2 GPU 진단"
echo "=========================================="
echo

# 1. nvidia-smi 확인
echo "[1] nvidia-smi 명령어 확인"
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi 사용 가능"
    nvidia-smi
else
    echo "✗ nvidia-smi를 찾을 수 없습니다"
    echo "   Windows에서 NVIDIA 드라이버가 설치되어 있나요?"
    echo "   WSL2는 Windows의 NVIDIA 드라이버를 공유합니다."
fi
echo

# 2. CUDA 라이브러리 확인
echo "[2] CUDA 라이브러리 확인"
if ldconfig -p | grep -q libcuda; then
    echo "✓ libcuda 발견"
    ldconfig -p | grep libcuda
else
    echo "✗ libcuda를 찾을 수 없습니다"
    echo "   NVIDIA Container Toolkit이 필요할 수 있습니다"
fi
echo

# 3. Docker GPU 지원 확인
echo "[3] Docker GPU 지원 확인"
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi 2>&1; then
    echo "✓ Docker에서 GPU 사용 가능"
else
    echo "✗ Docker에서 GPU를 사용할 수 없습니다"
    echo "   NVIDIA Container Toolkit 설치가 필요합니다"
fi
echo

# 4. nvidia-container-toolkit 확인
echo "[4] NVIDIA Container Toolkit 확인"
if dpkg -l | grep -q nvidia-container-toolkit; then
    echo "✓ NVIDIA Container Toolkit 설치됨"
    dpkg -l | grep nvidia-container-toolkit
else
    echo "✗ NVIDIA Container Toolkit이 설치되지 않았습니다"
    echo "   설치가 필요합니다"
fi
echo

echo "=========================================="
echo "진단 완료"
echo "=========================================="
echo
echo "다음 단계:"
echo "  1. 모든 항목이 ✓ 이면: docker compose up --build"
echo "  2. ✗ 가 있으면: ./fix_gpu_wsl2.sh 실행"
