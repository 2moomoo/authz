#!/bin/bash
# Startup script for Internal LLM API Server

set -e

# Configuration
HOST="${SERVER_HOST:-0.0.0.0}"
PORT="${SERVER_PORT:-8000}"
WORKERS="${SERVER_WORKERS:-4}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Internal LLM API Server${NC}"

# Check if config file exists
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}Error: config.yaml not found${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Run the server
echo -e "${GREEN}Starting server on ${HOST}:${PORT} with ${WORKERS} workers${NC}"
echo -e "${YELLOW}Press CTRL+C to stop${NC}"
echo ""

uvicorn src.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    --no-server-header
