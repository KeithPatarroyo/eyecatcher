# Eyecatcher — common development tasks
# Run `make` or `make help` to list targets.

.PHONY: help install dev test lint format generate generate-signals generate-representation-config generate-representation-includes generate-evolution-config check-generate new-representation docker-build docker-up clean

help:
	@echo "Eyecatcher — development targets"
	@echo ""
	@echo "  make install     Create venv and install project + dev deps (Python + optional JS tooling)"
	@echo "  make dev        Run the Flask dev server (python -m eyecatcher.server)"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run Ruff check (Python) and ESLint (JS)"
	@echo "  make generate   Run all codegen (signals + representation config + evolution config + representation includes)"
	@echo "  make check-generate  Exit with error if generated files are stale (for CI); run make generate to fix"
	@echo "  make generate-signals  Generate config_signals.generated.js from Python signal spec; validate NEAT"
	@echo "  make generate-representation-config  Generate config.generated.js from Python representation export"
	@echo "  make generate-representation-includes  Update representation script tags in HTML"
	@echo "  make generate-evolution-config  Generate config_defaults.generated.js from config/evolution_defaults.json"
	@echo "  make new-representation name=<snake_case>  Scaffold a new representation (Python, registry, JS adapter, includes)"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-up  Start app with docker compose up"
	@echo "  make clean      Remove build artifacts, caches, and optional venv/node_modules"
	@echo ""

install:
	@echo "==> Creating virtual environment..."
	python -m venv .venv 2>/dev/null || true
	@echo "==> Installing Python package + dev deps..."
	.venv/bin/pip install -e ".[dev]" 2>/dev/null || .venv\Scripts\pip install -e ".[dev]"
	@if [ -f package.json ]; then echo "==> Installing npm deps (JS lint/format)..."; npm install; else echo "==> No package.json, skipping npm install"; fi
	@echo "==> Done. Activate venv: source .venv/bin/activate (Windows: .venv\\Scripts\\activate)"
	@echo "==> Install pre-commit hooks: pre-commit install"

dev:
	.venv/bin/python -m eyecatcher.server

test:
	.venv/bin/python -m pytest --tb=short -v --cov=eyecatcher --cov-report=term-missing

lint:
	ruff check .
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npx eslint -c config/eslint.config.js static/; fi

format:
	ruff format .
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npm run format; fi

generate: generate-signals generate-representation-config generate-representation-includes generate-evolution-config

check-generate:
	.venv/bin/python scripts/check_codegen_sync.py

generate-signals:
	.venv/bin/python scripts/generate_signal_config.py

generate-representation-config:
	.venv/bin/python scripts/generate_representation_config.py

generate-representation-includes:
	.venv/bin/python scripts/generate_representation_includes.py

generate-evolution-config:
	.venv/bin/python scripts/generate_evolution_config.py

new-representation:
	@if [ -z "$(name)" ]; then echo "Usage: make new-representation name=<snake_case>"; echo "Example: make new-representation name=my_rep"; exit 1; fi
	.venv/bin/python scripts/new_representation.py "$(name)"

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up --build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__ .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Optional: rm -rf .venv node_modules"
