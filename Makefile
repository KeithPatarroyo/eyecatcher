# Eyecatcher — common development tasks
# Run `make` or `make help` to list targets.

.PHONY: help install dev test lint format lint-js format-js docker-build docker-up clean

help:
	@echo "Eyecatcher — development targets"
	@echo ""
	@echo "  make install     Create venv and install project + dev deps (Python + optional JS tooling)"
	@echo "  make dev        Run the Flask dev server (python -m eyecatcher.server)"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run Ruff check (Python) and ESLint (JS)"
	@echo "  make format     Run Ruff format (Python) and Prettier (JS)"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-up  Start app with docker compose up"
	@echo "  make clean      Remove build artifacts, caches, and optional venv/node_modules"
	@echo ""

install:
	python -m venv .venv 2>/dev/null || true
	@echo "Activate the venv: source .venv/bin/activate (or .venv\\Scripts\\activate on Windows)"
	@echo "Then run: pip install -e \".[dev]\""
	@echo "For JS linting: npm install"
	@echo "For pre-commit: pre-commit install"

dev:
	python -m eyecatcher.server

test:
	pytest --tb=short -v

lint:
	ruff check .
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npx eslint static/; fi

format:
	ruff format .
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npx prettier --write "static/**/*.js" "static/**/*.html" "static/**/*.css"; fi

docker-build:
	docker compose build

docker-up:
	docker compose up --build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__ .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Optional: rm -rf .venv .eyecatcher-venv node_modules"
