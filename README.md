# Internal LLM API Server

Production-ready OpenAI-compatible API server for internal GPU-based LLM models. Provides secure API access to company LLM resources with authentication, rate limiting, and monitoring.

## Features

- ✅ **OpenAI API Compatible**: Drop-in replacement for OpenAI API clients
- 🔐 **API Key Authentication**: Secure access with user-specific API keys
- ⚡ **Rate Limiting**: Per-user request limits (per minute and per hour)
- 📊 **Request Logging**: Comprehensive request/response logging for monitoring
- 🚀 **vLLM Backend**: High-performance GPU inference with vLLM
- 📈 **Prometheus Metrics**: Built-in metrics for monitoring and alerting
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- 🔄 **Multi-GPU Support**: Scalable GPU resource management

## Architecture

```
Employee IDE/Script
      ↓
  [API Key Auth]
      ↓
Internal LLM API Server (FastAPI)
      ↓
  [Rate Limiting]
      ↓
  [Request Logging]
      ↓
vLLM Server (GPU-backed)
      ↓
   LLM Model (H100)
```

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd authz

# Copy environment template
cp .env.example .env

# Edit configuration
nano config.yaml
```

### 2. Start with Docker Compose (Recommended)

```bash
# Start all services (vLLM + API Server + Redis)
docker-compose up -d

# Check logs
docker-compose logs -f api-server

# Check health
curl http://localhost:8000/health
```

### 3. Start Manually (Development)

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start vLLM server first (in another terminal)
# See "vLLM Setup" section below

# Start API server
./start.sh

# Or use uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

### config.yaml

Main configuration file for the API server:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4

vllm:
  base_url: "http://localhost:8100/v1"
  default_model: "meta-llama/Llama-2-7b-chat-hf"

api_keys:
  sk-internal-dev-key-001:
    user_id: "dev-team"
    tier: "premium"

rate_limits:
  premium:
    requests_per_minute: 100
    requests_per_hour: 1000
  standard:
    requests_per_minute: 30
    requests_per_hour: 300
```

### API Key Management

API keys are defined in `config.yaml`:

```yaml
api_keys:
  sk-internal-YOUR-KEY-HERE:
    user_id: "your-team"
    tier: "standard"  # or "premium" or "free"
```

**Production Note**: In production, use a database or secrets manager instead of storing keys in the config file.

## vLLM Setup

### Option 1: Docker Compose (Included)

vLLM is automatically started with docker-compose.yml.

### Option 2: Manual vLLM Installation

```bash
# Install vLLM
pip install vllm

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8100 \
  --dtype auto \
  --max-model-len 4096

# For multi-GPU
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4 \
  --host 0.0.0.0 \
  --port 8100
```

### Option 3: Using Text Generation Inference (TGI)

```bash
docker run --gpus all --shm-size 1g -p 8100:80 \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id meta-llama/Llama-2-7b-chat-hf \
  --port 80
```

## API Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model": "meta-llama/Llama-2-7b-chat-hf",
  "vllm_status": "connected"
}
```

### List Models

```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-internal-dev-key-001"
```

### Text Completion

```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-internal-dev-key-001" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "prompt": "Once upon a time",
    "max_tokens": 50,
    "temperature": 0.7
  }'
```

### Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-internal-dev-key-001" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

## Client Integration

### Python (OpenAI SDK)

```python
from openai import OpenAI

# Configure client to use internal API
client = OpenAI(
    api_key="sk-internal-dev-key-001",
    base_url="http://localhost:8000/v1"
)

# Chat completion
response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### Python (requests)

```python
import requests

API_KEY = "sk-internal-dev-key-001"
BASE_URL = "http://localhost:8000/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100
}

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json=data
)

print(response.json())
```

### JavaScript/TypeScript

```javascript
const API_KEY = "sk-internal-dev-key-001";
const BASE_URL = "http://localhost:8000/v1";

async function chatCompletion() {
  const response = await fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: "meta-llama/Llama-2-7b-chat-hf",
      messages: [
        { role: "user", content: "Hello!" }
      ],
      max_tokens: 100
    })
  });

  const data = await response.json();
  console.log(data);
}
```

### cURL Scripts

Create a test script `test_api.sh`:

```bash
#!/bin/bash
API_KEY="sk-internal-dev-key-001"
BASE_URL="http://localhost:8000"

# Test health
echo "Testing health endpoint..."
curl -s "$BASE_URL/health" | jq

# Test chat completion
echo -e "\nTesting chat completion..."
curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }' | jq
```

## Rate Limiting

Rate limits are enforced per API key based on the user's tier:

| Tier | Requests/Minute | Requests/Hour |
|------|----------------|---------------|
| Premium | 100 | 1000 |
| Standard | 30 | 300 |
| Free | 10 | 100 |

Rate limit information is included in response headers:

```
X-RateLimit-Limit-Minute: 30
X-RateLimit-Remaining-Minute: 25
X-RateLimit-Limit-Hour: 300
X-RateLimit-Remaining-Hour: 275
```

When rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded. Maximum 30 requests per minute allowed for tier 'standard'."
}
```

## Monitoring

### Logs

Logs are stored in the `logs/` directory:

- `app_YYYY-MM-DD.log` - Application logs
- `requests_YYYY-MM-DD.log` - Request/response logs (JSON format)

### Prometheus Metrics

Metrics are available at `http://localhost:9090/metrics`:

- `api_requests_total` - Total API requests by endpoint and status
- `api_request_duration_seconds` - Request duration histogram
- `api_tokens_total` - Total tokens processed by type and user

### Example Prometheus Queries

```promql
# Request rate per endpoint
rate(api_requests_total[5m])

# Average request duration
rate(api_request_duration_seconds_sum[5m]) / rate(api_request_duration_seconds_count[5m])

# Token usage by user
sum by (user) (api_tokens_total)

# Error rate
rate(api_requests_total{status=~"5.."}[5m])
```

## Production Deployment

### Systemd Service

1. Install the service:

```bash
# Copy service file
sudo cp llm-api.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/llm-api

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable llm-api

# Start service
sudo systemctl start llm-api

# Check status
sudo systemctl status llm-api
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name llm-api.internal.company.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for long requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### HTTPS with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d llm-api.internal.company.com

# Auto-renewal is configured automatically
```

### Environment Variables

For production, use environment variables instead of config.yaml:

```bash
export VLLM_BASE_URL="http://vllm-server:8100/v1"
export VLLM_DEFAULT_MODEL="meta-llama/Llama-2-70b-chat-hf"
export REQUIRE_HTTPS="true"
export LOG_LEVEL="info"
```

## Security Best Practices

1. **HTTPS**: Always use HTTPS in production
2. **API Keys**: Use a secrets manager (AWS Secrets Manager, HashiCorp Vault)
3. **Network**: Deploy on internal network only
4. **Firewall**: Restrict access to authorized IP ranges
5. **Logging**: Disable body logging for sensitive data
6. **Updates**: Keep dependencies updated
7. **Monitoring**: Set up alerts for unusual activity

## Troubleshooting

### API Server won't start

```bash
# Check if port is in use
sudo lsof -i :8000

# Check logs
tail -f logs/app_*.log

# Verify config
python -c "from src.config import config; print(config)"
```

### vLLM connection failed

```bash
# Check vLLM is running
curl http://localhost:8100/v1/models

# Check vLLM logs
docker logs vllm-server

# Test vLLM directly
curl -X POST http://localhost:8100/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"meta-llama/Llama-2-7b-chat-hf","messages":[{"role":"user","content":"Hi"}]}'
```

### Rate limit issues

```bash
# Check current limits
curl -I http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-internal-dev-key-001"

# View rate limit headers
# X-RateLimit-Remaining-Minute: 25
```

### High memory usage

```bash
# Check vLLM model size
# Reduce max_model_len in vLLM config
# Use quantization (--quantization awq)
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Formatting

```bash
# Install formatters
pip install black isort

# Format code
black src/
isort src/
```

## API Reference

### Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/` | GET | API information | No |
| `/health` | GET | Health check | No |
| `/metrics` | GET | Prometheus metrics | No |
| `/v1/models` | GET | List available models | Yes |
| `/v1/completions` | POST | Text completion | Yes |
| `/v1/chat/completions` | POST | Chat completion | Yes |

### Authentication

All protected endpoints require an `Authorization` header:

```
Authorization: Bearer sk-internal-your-key-here
```

### Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 401 | Unauthorized (invalid or missing API key) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable (vLLM backend down) |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Internal use only. Not for public distribution.

## Support

For issues or questions:
- Internal Wiki: [link]
- Slack Channel: #llm-api-support
- Email: llm-support@company.com
