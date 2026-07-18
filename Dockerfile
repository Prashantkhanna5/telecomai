# Use official python slim image
FROM python:3.11-slim

# Copy uv binary for rapid package installation and management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory inside container
WORKDIR /workspace

# Copy dependency configuration
COPY pyproject.toml uv.lock ./

# Sync dependencies (this creates a cached virtualenv)
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source
COPY app/ ./app/

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV DEEPSEEK_API_KEY=""

# Expose port
EXPOSE 8080

# Start the web service using uv
CMD ["uv", "run", "python", "app/main.py"]
