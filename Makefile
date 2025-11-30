.PHONY: help build test format check-format lint clean docker-build docker-test docker-format docker-check-format

help:
	@echo "Available targets:"
	@echo "  build           - Build the Docker image"
	@echo "  test            - Run tests in Docker"
	@echo "  format          - Format code with black and isort"
	@echo "  check-format    - Check code formatting without making changes"
	@echo "  lint            - Run mypy type checking"
	@echo "  clean           - Clean up Docker artifacts"
	@echo "  docker-build    - Build Docker image"
	@echo "  docker-test     - Run tests in Docker"
	@echo "  docker-format    - Format code in Docker"
	@echo "  docker-check-format - Check formatting in Docker"

build:
	docker-compose build

test:
	docker-compose run --rm test

format:
	docker-compose run --rm format

check-format:
	docker-compose run --rm check-format

lint:
	docker-compose run --rm lint

clean:
	docker-compose down
	docker system prune -f

docker-build:
	docker build -t pyiv:latest .

docker-test:
	docker run --rm -v $(PWD):/app pyiv:latest pytest tests/ -v

docker-format:
	docker run --rm -v $(PWD):/app -w /app --user $(shell id -u):$(shell id -g) pyiv:latest sh -c "black pyiv/ tests/ && isort pyiv/ tests/"

docker-check-format:
	docker run --rm -v $(PWD):/app -w /app --user $(shell id -u):$(shell id -g) pyiv:latest sh -c "black --check pyiv/ tests/ && isort --check-only pyiv/ tests/"

