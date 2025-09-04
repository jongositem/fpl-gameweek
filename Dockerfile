# Use the official uv image which has uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Create non-root user first
RUN adduser --disabled-password --gecos '' appuser

# Set work directory and change ownership
WORKDIR /app
RUN chown -R appuser:appuser /app

# Switch to non-root user before installing dependencies
USER appuser

# Copy dependency files first for better layer caching
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

# Install Python dependencies with uv as the appuser
RUN uv sync --frozen --no-dev && rm -rf /tmp/uv-cache

# Copy application code
COPY --chown=appuser:appuser . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application with gunicorn through uv
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "app:app"]