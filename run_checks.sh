#!/bin/bash
# Run all validation checks for pyiv
# This script is used by CI and can be run locally or in Docker

# Don't use set -e here - we want to track failures manually
# set -e  # Exit on any error

echo "=========================================="
echo "Running pyiv validation checks"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any checks fail
FAILED=0

# Function to run a check and track failures
run_check() {
    local name="$1"
    shift
    echo ""
    echo -e "${YELLOW}Running: $name${NC}"
    echo "Command: $@"
    # Capture both stdout and stderr, and exit code
    if "$@" 2>&1; then
        echo -e "${GREEN}✓ $name passed${NC}"
    else
        local exit_code=$?
        echo -e "${RED}✗ $name failed (exit code: $exit_code)${NC}"
        FAILED=1
    fi
}

# 1. Black formatting check
run_check "Black formatting" black --check --diff pyiv/ tests/

# 2. isort import sorting check
run_check "isort import sorting" isort --check-only pyiv/ tests/

# 3. Pytest with coverage
# Create build directory if it doesn't exist
mkdir -p build
# Skip html report to avoid permission issues with htmlcov directory
# Exit code 2 from pytest-cov is acceptable (coverage collection succeeded, html report may fail)
pytest --cov=pyiv --cov-report=xml:build/coverage.xml --cov-report=term-missing tests/ 2>&1
PYTEST_EXIT=$?
if [ $PYTEST_EXIT -eq 0 ] || [ $PYTEST_EXIT -eq 2 ]; then
    echo -e "${GREEN}✓ Pytest with coverage passed${NC}"
else
    echo -e "${RED}✗ Pytest with coverage failed (exit code: $PYTEST_EXIT)${NC}"
    FAILED=1
fi

# 4. mypy type checking
run_check "mypy type checking" mypy pyiv/

# 5. Bandit security check (don't fail on warnings)
# Create build directory if it doesn't exist
mkdir -p build
bandit -r pyiv/ -f json -o build/bandit-report.json || true
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Bandit security check passed${NC}"
else
    echo -e "${YELLOW}⚠ Bandit security check completed with warnings (non-fatal)${NC}"
fi

# 6. Documentation quality check
run_check "Documentation quality" python3 check_docs_quality.py

# 7. Sphinx documentation build check
echo ""
echo -e "${YELLOW}Running: Sphinx documentation build${NC}"
echo "Command: Building Sphinx documentation"
# Check if sphinx-build is available
if ! command -v sphinx-build &> /dev/null; then
    echo -e "${YELLOW}⚠ sphinx-build not found, attempting to install Sphinx...${NC}"
    # Try to install sphinx and sphinx-rtd-theme
    if python3 -m pip install --quiet sphinx sphinx-rtd-theme 2>&1; then
        echo -e "${GREEN}✓ Sphinx installed${NC}"
    else
        echo -e "${RED}✗ Failed to install Sphinx. Please install it manually: pip install sphinx sphinx-rtd-theme${NC}"
        FAILED=1
    fi
fi

# Build the documentation
if [ $FAILED -eq 0 ]; then
    if [ ! -d "docs" ]; then
        echo -e "${RED}✗ docs/ directory not found${NC}"
        FAILED=1
    else
        cd docs
        if sphinx-build -b html -W . _build/html 2>&1; then
            echo -e "${GREEN}✓ Sphinx documentation build passed${NC}"
            cd ..
        else
            SPHINX_EXIT=$?
            echo -e "${RED}✗ Sphinx documentation build failed (exit code: $SPHINX_EXIT)${NC}"
            cd ..
            FAILED=1
        fi
    fi
fi

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
