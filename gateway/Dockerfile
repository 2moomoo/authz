FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY gateway/requirements.txt ./gateway/
COPY shared/requirements.txt ./shared/
RUN pip install --no-cache-dir -r gateway/requirements.txt -r shared/requirements.txt

# Copy application code
COPY gateway/ ./gateway/
COPY shared/ ./shared/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
