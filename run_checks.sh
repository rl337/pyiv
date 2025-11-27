#!/bin/bash

# PyIV - Comprehensive Validation Script
# This script runs all automated tests, static checks, style linting, and test coverage

# Don't use set -e here - we want to continue even if some checks fail
# set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run command and capture exit code
run_check() {
    local check_name="$1"
    local command="$2"
    local expected_exit_code="${3:-0}"
    
    print_status "Running $check_name..."
    
    eval "$command"
    local exit_code=$?
    
    if [ $exit_code -eq $expected_exit_code ]; then
        print_success "$check_name passed"
        return 0
    else
        print_error "$check_name failed with exit code $exit_code (expected $expected_exit_code)"
        return 1
    fi
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] && [ ! -d "pyiv" ]; then
    print_error "This script must be run from the project root directory (where pyproject.toml is located)"
    exit 1
fi

print_status "Starting comprehensive validation checks..."
print_status "Project: PyIV"
print_status "Timestamp: $(date)"
echo ""

# Track overall success
overall_success=true

# 1. Code Formatting Checks
echo "=========================================="
print_status "1. CODE FORMATTING CHECKS"
echo "=========================================="

# Black formatting check
if command_exists black; then
    if ! run_check "Black formatting check" "black --check --line-length 120 pyiv/ tests/"; then
        print_warning "Code formatting issues found. Run 'black pyiv/ tests/' to fix."
        overall_success=false
    fi
else
    print_warning "Black not installed, skipping formatting check"
    print_status "Install with: pip install black"
fi

# isort import sorting check
if command_exists isort; then
    if ! run_check "isort import sorting check" "isort --check-only --line-length 120 pyiv/ tests/"; then
        print_warning "Import sorting issues found. Run 'isort pyiv/ tests/' to fix."
        overall_success=false
    fi
else
    print_warning "isort not installed, skipping import sorting check"
    print_status "Install with: pip install isort"
fi

echo ""

# 2. Linting Checks
echo "=========================================="
print_status "2. LINTING CHECKS"
echo "=========================================="

# Pylint (optional, may have compatibility issues)
if command_exists pylint; then
    if ! run_check "Pylint" "pylint pyiv/ --max-line-length=120 --disable=C0103,C0114,C0116" 0; then
        print_warning "Pylint found issues. Review output above."
        # Don't fail the build for pylint warnings
    fi
else
    print_status "Pylint not installed, skipping (optional)"
fi

echo ""

# 3. Type Checking
echo "=========================================="
print_status "3. TYPE CHECKING"
echo "=========================================="

# MyPy type checking
if command_exists mypy; then
    if ! run_check "MyPy type checking" "mypy pyiv/ --ignore-missing-imports"; then
        print_warning "Type checking found issues. Review output above."
        overall_success=false
    fi
else
    print_warning "MyPy not installed, skipping type checking"
    print_status "Install with: pip install mypy"
fi

echo ""

# 4. Security Checks
echo "=========================================="
print_status "4. SECURITY CHECKS"
echo "=========================================="

# Bandit security analysis
if command_exists bandit; then
    if ! run_check "Bandit security analysis" "bandit -r pyiv/ -f json -o bandit-report.json" 0; then
        print_warning "Security issues found. Review bandit-report.json for details."
        overall_success=false
    fi
else
    print_warning "Bandit not installed, skipping security analysis"
    print_status "Install with: pip install bandit"
fi

echo ""

# 5. Testing
echo "=========================================="
print_status "5. TESTING"
echo "=========================================="

# Run tests with coverage
if command_exists pytest; then
    # Check if pytest-cov is available
    if python -c "import pytest_cov" 2>/dev/null; then
        # Run with coverage
        if ! run_check "Pytest with coverage" "pytest --cov=pyiv --cov-report=xml --cov-report=html --cov-report=term-missing tests/"; then
            print_error "Tests failed. Review output above."
            overall_success=false
        fi
    else
        # Run without coverage
        print_warning "pytest-cov not installed, running tests without coverage"
        if ! run_check "Pytest" "pytest tests/"; then
            print_error "Tests failed. Review output above."
            overall_success=false
        fi
    fi
else
    print_error "Pytest not installed. Install with: pip install pytest pytest-cov"
    overall_success=false
fi

echo ""

# 6. Additional Checks
echo "=========================================="
print_status "6. ADDITIONAL CHECKS"
echo "=========================================="

# Check for TODO/FIXME comments in production code
print_status "Checking for TODO/FIXME comments in production code..."
todo_count=$(grep -r "TODO\|FIXME" pyiv/ --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$todo_count" -gt 0 ]; then
    print_warning "Found $todo_count TODO/FIXME comments in production code:"
    grep -r "TODO\|FIXME" pyiv/ --include="*.py" 2>/dev/null || true
    # Don't fail for TODO comments
else
    print_success "No TODO/FIXME comments found in production code"
fi

# Check for docstrings in Python files
print_status "Checking for docstrings in Python files..."
python_files=$(find pyiv/ -name "*.py" -type f 2>/dev/null | wc -l)
files_with_docstrings=$(grep -r '"""' pyiv/ --include="*.py" 2>/dev/null | wc -l || echo "0")
if [ "$python_files" -gt 0 ]; then
    docstring_ratio=$((files_with_docstrings * 100 / python_files))
    if [ "$docstring_ratio" -lt 50 ]; then
        print_warning "Only $docstring_ratio% of Python files have docstrings"
        # Don't fail for docstring coverage
    else
        print_success "Documentation coverage: $docstring_ratio% of files have docstrings"
    fi
fi

echo ""

# 7. Documentation Checks
echo "=========================================="
print_status "7. DOCUMENTATION CHECKS"
echo "=========================================="

# Check if README exists and has content
if [ -f "README.md" ] && [ -s "README.md" ]; then
    print_success "README.md exists and has content"
else
    print_warning "README.md is missing or empty"
    overall_success=false
fi

echo ""

# 8. Final Summary
echo "=========================================="
print_status "VALIDATION SUMMARY"
echo "=========================================="

if [ "$overall_success" = true ]; then
    print_success "All checks passed! Repository is compliant with project requirements."
    echo ""
    print_status "Generated files:"
    [ -f "coverage.xml" ] && echo "  - coverage.xml (test coverage report)"
    [ -f "htmlcov/index.html" ] && echo "  - htmlcov/index.html (HTML coverage report)"
    [ -f "bandit-report.json" ] && echo "  - bandit-report.json (security report)"
    echo ""
    print_status "To view HTML coverage report: open htmlcov/index.html"
    exit 0
else
    print_error "Some checks failed. Please review the output above and fix the issues."
    echo ""
    print_status "Common fixes:"
    echo "  - Format code: black pyiv/ tests/ && isort pyiv/ tests/"
    echo "  - Fix types: mypy pyiv/"
    echo "  - Run tests: pytest"
    echo "  - Security: bandit -r pyiv/"
    exit 1
fi

