# GPU 없이 실행하기

## 상황

vLLM은 **GPU 전용**이므로 GPU 없이는 실행할 수 없습니다.

```
RuntimeError: Failed to infer device type
libcuda.so.1: cannot open shared object file: No such file or directory
```

## 해결 방법

### 옵션 1: GPU 없이 다른 서비스만 테스트 (권장)

```bash
# vLLM 제외하고 실행
docker compose -f docker-compose.nogpu.yml up --build
```

이렇게 하면:
- ✅ Admin Service (8002): API 키 관리, 이메일 인증
- ✅ Gateway Service (8000): 인증, 라우팅, Rate Limiting
- ✅ LLM Backend Service (8001): API 엔드포인트 제공 (vLLM 연결은 실패하지만 서비스는 시작됨)

### 옵션 2: GPU 설정 (WSL2 + NVIDIA GPU)

WSL2에서 GPU를 사용하려면:

1. **NVIDIA GPU 드라이버 설치** (Windows에)
   - https://www.nvidia.com/Download/index.aspx

2. **CUDA Toolkit 설치** (WSL2 내부)
   ```bash
   # WSL2에서 실행
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

   sudo apt-get update
   sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

3. **GPU 확인**
   ```bash
   nvidia-smi
   docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```

4. **vLLM 포함해서 실행**
   ```bash
   docker compose up --build
   ```

### 옵션 3: 외부 LLM API 사용

실제 LLM은 외부 서비스(OpenAI, Anthropic 등)를 사용하고, 이 시스템은 게이트웨이로만 사용:

1. `llm_backend/main.py`를 수정하여 외부 API 호출
2. vLLM 서비스 비활성화

## 테스트할 수 있는 기능 (GPU 없이)

### 1. 이메일 인증으로 API 키 발급

```bash
# Self-service portal 접속
open http://localhost:8002/user

# 또는 API로 직접
curl -X POST http://localhost:8002/auth/request-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@company.com"}'

# 콘솔에서 6자리 코드 확인 후
curl -X POST http://localhost:8002/auth/verify-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@company.com", "code": "123456"}'
```

### 2. Admin 대시보드

```bash
# Admin 포털 접속
open http://localhost:8002

# 로그인: username=admin, password=admin123
```

### 3. Gateway 인증 테스트

```bash
# API 키로 인증 테스트 (LLM 호출은 실패하지만 인증/rate limiting은 작동)
curl http://localhost:8000/health \
  -H "Authorization: Bearer sk-internal-your-api-key"
```

## 권장 사항

**GPU가 없는 환경**이라면:

1. `docker-compose.nogpu.yml` 사용
2. Admin, Gateway, Auth 기능만 테스트
3. 실제 LLM은 나중에 GPU 환경에서 테스트

**GPU가 있는 환경**이라면:
1. WSL2 + NVIDIA GPU 설정 완료
2. `nvidia-smi` 확인
3. `docker compose up --build` 실행

## 현재 실행 명령어

```bash
# 이전 컨테이너 정리
docker compose down -v

# GPU 없이 실행
docker compose -f docker-compose.nogpu.yml up --build
```

서비스가 시작되면:
- Admin: http://localhost:8002
- Gateway: http://localhost:8000
- LLM Backend: http://localhost:8001

vLLM 관련 에러는 무시하세요. 다른 기능들은 정상 작동합니다.
