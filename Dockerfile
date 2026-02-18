# =============================================================================
# UI Service - Smart Scale UI Microservice
# =============================================================================

# -----------------------------------------------------------------------------
# Build stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Final stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Service port (default matches existing uvicorn.sh)
ENV SERVICE_PORT=8500

WORKDIR /app

# Create non-root user for security
RUN useradd -ms /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code and config files
COPY app/ ./app/
COPY fruit.json .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE ${SERVICE_PORT}

# Run uvicorn server (using shell form to expand SERVICE_PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT}"]

