# AGENTS.md – Instructions for AI Coding Agents

This file gives AI coding agents the context needed to work effectively in the Eyecatcher codebase. See [CONTRIBUTING.md](CONTRIBUTING.md) for human contributor guidelines.

## Project overview

Eyecatcher is a **dual-CPPN interactive evolution** system: like Picbreeder, but patterns change over time and react to user input. CPPNs compile to GLSL for real-time WebGL in the browser.

**Tech stack:** Python 3.9+, Flask 3.0+, NEAT-Python, NumPy, Pillow, matplotlib (optional). Frontend: vanilla JavaScript + WebGL/GLSL; no React/Vue/etc. Backend is a stateless REST API; the client stores population state.

---

## Commands (run from repo root)

```bash
pip install -e ".[dev]"       # Install package + dev deps (pytest, ruff)
pytest -v --tb=short         # Run tests
ruff check .                 # Lint
ruff format .                # Format
ruff check . --fix           # Auto-fix lint
docker compose up --build    # Run full stack locally (then open http://localhost:5001)
python -m eyecatcher.server  # Run dev server without Docker
```

---

## Project structure

| Path | Purpose |
|------|---------|
| `src/eyecatcher/` | Python package: `cppn_engine`, `shader_compiler`, `server`, `stateless_api`, `community_routes`, `genealogy_routes`, `genome_serialization`, `genome_visualizer` |
| `static/` | Frontend: HTML, CSS, JS modules; served by Flask from repo root |
| `config/` | NEAT config files (not in package); read at runtime via `get_root_dir()` |
| `tests/` | Pytest test suite |
| `demos/` | Example scripts (api_usage, evolution_batch, time_signal_showcase) |
| `data/` | Runtime data: `community.db`, `genealogy.db` (gitignored; created on first run) |

---

## Architecture notes

- **Src layout:** All Python lives in `src/eyecatcher/`. **Use relative imports** inside the package (e.g. `from .cppn_engine import ...`). Code outside the package (demos, tests) imports with `from eyecatcher.xxx import ...`.
- **Stateless API:** The server does **not** hold population state. Clients send full genome payloads in requests (e.g. `/api/compile`, `/api/breed`). Do not add server-side population storage.
- **Dual-CPPN:** Each individual is a `DualGenome`: two NEAT genomes (`visual` and `time_signal`) evolved together. Mutations and crossovers operate on both; keep the pairing consistent.
- **Paths:** `get_root_dir()` in `src/eyecatcher/__init__.py` returns the repo root. Use it (or paths relative to it) for `config/`, `static/`, `data/`. Flask’s `static_folder` is set to that root `static/` directory.

---

## Code style

- **Python:** Ruff. Line length 88, target Python 3.9, rules E/F/I/N/W/UP, double quotes. Config in [pyproject.toml](pyproject.toml).
- **Commits:** Conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- **Docstrings:** Google style with Args/Returns where relevant.
- **Types:** Type hints used widely; `TYPE_CHECKING` for circular import guards.

---

## Testing

- **Framework:** pytest; `testpaths = ["tests"]` in [pyproject.toml](pyproject.toml).
- **Test modules:** `tests/test_cppn_engine.py`, `tests/test_shader_compiler.py`, `tests/test_genome_serialization.py`, `tests/test_api.py`, `tests/test_visualization.py`.
- **API tests:** Use Flask test client: `from eyecatcher.server import app` then `app.test_client()`.
- **Engine API:** `mutate_dual_genome(dual, new_key)` and `crossover_dual_genomes(dual1, dual2, new_key)` **require** the `new_key` argument.

---

## Git workflow

- Default development branch: `dev`. PRs target `dev` (or `main` once consolidated).
- CI (GitHub Actions) runs on push/PR to `main` and `dev`: pytest, `ruff check`, `ruff format --check`.

---

## Boundaries

- **Always:** Run `pytest` and `ruff check` (and fix issues) before committing; use relative imports inside `src/eyecatcher/`; preserve the stateless API contract (no server-side population state).
- **Ask first:** Adding new dependencies; changing NEAT config files; modifying the GLSL shader template in `shader_compiler.py`; changing DB schema (community or genealogy).
- **Never:** Commit secrets or real API keys; modify files in `data/` (runtime-generated DBs); hardcode absolute paths; break the `DualGenome` visual + time_signal pairing.
