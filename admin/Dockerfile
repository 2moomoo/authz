FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY admin/requirements.txt ./admin/
COPY shared/requirements.txt ./shared/
RUN pip install --no-cache-dir -r admin/requirements.txt -r shared/requirements.txt

# Copy application code
COPY admin/ ./admin/
COPY shared/ ./shared/

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8002"]
