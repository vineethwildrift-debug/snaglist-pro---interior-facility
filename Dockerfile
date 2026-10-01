# Multi-stage build for Snaglist Pro - optimized image
# Uses Debian slim, excludes heavy AI/ML dependencies for faster builds

# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-minimal.txt .

# Build wheels (minimal, no heavy ML libraries)
RUN pip install --no-cache-dir --user --no-warn-script-location \
    -r requirements-minimal.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set environment
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SNAGLIST_APP_USERNAME=${SNAGLIST_APP_USERNAME:-admin} \
    SNAGLIST_APP_PASSWORD=${SNAGLIST_APP_PASSWORD:-password}

# Copy application
COPY snaglist_pro /app/snaglist_pro
COPY desktop_app.py /app/
COPY config.yaml /app/config.yaml

# Create directories
RUN mkdir -p /app/data /app/uploads /app/output /app/batch

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/healthz || exit 1

# Expose port
EXPOSE 5000

# Entrypoint for flexibility
ENTRYPOINT ["python", "-m"]

# Default: Flask web server (can override with CLI args)
CMD ["snaglist_pro", "--web", "--host", "0.0.0.0", "--port", "5000"]
