# Dockerfile for pyiv - Python Dependency Injection Library
# Used for building, testing, and formatting checks

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY README.md ./
COPY pyiv/ ./pyiv/
COPY tests/ ./tests/

# Install the project and dev dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Set default command to run tests
CMD ["pytest", "tests/", "-v"]

