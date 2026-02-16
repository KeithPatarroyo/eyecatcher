# Eyecatcher — common development tasks
# Run `make` or `make help` to list targets.

.PHONY: help install dev test lint format generate generate-config generate-includes generate-neat check-generate new-representation docker-build docker-up clean

help:
	@echo "Eyecatcher — development targets"
	@echo ""
	@echo "  make install     Create venv and install project + dev deps (Python + optional JS tooling)"
	@echo "  make dev        Run the Flask dev server (python -m eyecatcher.server)"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run Ruff check (Python) and ESLint (JS)"
	@echo "  make generate   Run all codegen (unified config + representation includes + NEAT update)"
	@echo "  make check-generate  Exit with error if generated files are stale (for CI); run make generate to fix"
	@echo "  make generate-config  Generate static/js/config.generated.js (representations, signals, defaults)"
	@echo "  make generate-includes  Update representation script tags in HTML"
	@echo "  make generate-neat  Update config/neat/*.txt num_inputs/num_outputs from catalog"
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
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npx eslint -c eslint.config.js static/; fi

format:
	ruff format .
	@if command -v npx >/dev/null 2>&1 && [ -f package.json ]; then npm run format; fi

generate: generate-config generate-includes generate-neat

check-generate:
	.venv/bin/python scripts/check_codegen_sync.py

generate-config:
	.venv/bin/python scripts/generate_config.py

generate-includes:
	.venv/bin/python scripts/generate_representation_includes.py

generate-neat:
	.venv/bin/python scripts/update_neat_config.py

new-representation:
	@if [ -z "$(name)" ]; then echo "Usage: make new-representation name=<snake_case> [substrate=image|field|grid]"; echo "Example: make new-representation name=my_rep substrate=field"; exit 1; fi
	.venv/bin/python scripts/new_representation.py "$(name)" $(if $(substrate),--substrate=$(substrate),)

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up --build

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__ .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Optional: rm -rf .venv node_modules"
