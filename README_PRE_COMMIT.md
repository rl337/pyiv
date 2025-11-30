# Pre-commit Setup for pyiv

This project uses pre-commit hooks to ensure code quality before commits.

## Installation

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Or using the dev dependencies
pip install -e ".[dev]"

# Install the git hooks
pre-commit install
```

## Usage

Pre-commit hooks will run automatically on `git commit`. To run manually:

```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

## What Gets Checked

The pre-commit hooks run:

1. **Black** - Code formatting
2. **isort** - Import sorting
3. **run_checks.sh** - All validation checks:
   - Black formatting check
   - isort import sorting check
   - Pytest with coverage
   - mypy type checking
   - Bandit security check

## Running Checks Manually

You can also run the checks manually:

```bash
# Using Docker
docker-compose run --rm check-format
make check-format

# Or directly
./run_checks.sh
```

## Skipping Hooks

If you need to skip hooks (not recommended):

```bash
git commit --no-verify -m "Your message"
```

