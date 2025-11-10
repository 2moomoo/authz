#!/bin/bash
# Fedora에서 Podman + GPU 설정

echo "=========================================="
echo "Fedora GPU 설정 시작"
echo "=========================================="
echo

# 1. NVIDIA Container Toolkit Repository 추가
echo "[1] NVIDIA Container Toolkit Repository 추가"
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# 2. NVIDIA Container Toolkit 설치
echo
echo "[2] NVIDIA Container Toolkit 설치"
sudo dnf install -y nvidia-container-toolkit

# 3. CDI 설정 생성
echo
echo "[3] CDI 설정 생성"
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

echo
echo "[4] CDI 확인"
ls -l /etc/cdi/nvidia.yaml
cat /etc/cdi/nvidia.yaml | head -20

# 4. GPU 테스트
echo
echo "[5] GPU 테스트"
echo "Podman에서 GPU 사용 테스트 중..."
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

if [ $? -eq 0 ]; then
    echo
    echo "=========================================="
    echo "✓ GPU 설정 완료!"
    echo "=========================================="
    echo
    echo "이제 다음 명령어로 실행하세요:"
    echo "  ./run_podman_gpu.sh"
else
    echo
    echo "=========================================="
    echo "✗ GPU 설정 실패"
    echo "=========================================="
    echo
    echo "문제 해결:"
    echo "  1. Windows에서 NVIDIA 드라이버 확인"
    echo "  2. WSL2 재시작: wsl --shutdown (Windows PowerShell)"
    echo "  3. 다시 시도"
fi
