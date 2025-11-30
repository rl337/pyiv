# Dockerfile for pyiv - Python Dependency Injection Library
# Used for building, testing, and formatting checks

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files (as root for now)
COPY pyproject.toml ./
COPY README.md ./
COPY pyiv/ ./pyiv/
COPY tests/ ./tests/
COPY run_checks.sh ./

# Install the project and dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Install pre-commit if not already installed
RUN pip install --no-cache-dir pre-commit || true

# Make run_checks.sh executable
RUN chmod +x run_checks.sh

# Create a non-root user and fix ownership
# Note: When using volumes, the host user should be used via --user flag
# This user is mainly for running commands without volumes
RUN useradd -m -u 1000 pyivuser && chown -R pyivuser:pyivuser /app

# Switch to non-root user
USER pyivuser

# Set default command to run checks
CMD ["./run_checks.sh"]

