# AGENTS.md – Instructions for AI Coding Agents

This file gives AI coding agents the context needed to work effectively in the Eyecatcher codebase. See [CONTRIBUTING.md](CONTRIBUTING.md) for human contributor guidelines.

## Project overview

Eyecatcher is a **dual-CPPN interactive evolution** system: like Picbreeder, but patterns change over time and react to user input. CPPNs compile to GLSL for real-time WebGL in the browser.

**Tech stack:** Python 3.9+, Flask 3.0+, NEAT-Python, NumPy, Pillow, matplotlib (optional). Frontend: vanilla JavaScript + WebGL/GLSL; no React/Vue/etc. Backend is a stateless REST API; the client stores population state.

---

## Commands (run from repo root)

**Makefile (preferred):** Run `make help` to list all. Common targets:

| Target | Action |
|--------|--------|
| `make install` | Create venv, `pip install -e ".[dev]"`, `npm install` |
| `make test` | pytest --tb=short -v |
| `make lint` | Ruff (Python) + ESLint (JS) |
| `make format` | Ruff format + Prettier (JS) |
| `make generate-signals` | Generate config_signals.generated.js from Python signal spec; validate NEAT (run after changing signals) |
| `make dev` | Run Flask dev server |
| `make docker-up` | docker compose -f docker/docker-compose.yml up --build |
| `make clean` | Remove build artifacts, caches |

**npm scripts** (from repo root, after `npm install`): `npm run lint`, `npm run format:check`, `npm run format` (see [package.json](../package.json)).

**Direct commands** (if not using Make): `pip install -e ".[dev]"`, `pre-commit install`, `pytest -v --tb=short`, `ruff check .`, `ruff format .`, `docker compose -f docker/docker-compose.yml up --build`, `python -m eyecatcher.server`.

---

## Project structure

| Path | Purpose |
|------|---------|
| `src/eyecatcher/` | Python package. **Packages**: `experiment/` (config, presets, get_configured_representation), `evolution/` (reproduction, fitness), `genome/`, `representation/` (CPPN, CA, protocol), `signals/`, `inspection/`, `glsl/`, `web/`, `data/`. Top-level: `server`. |
| `static/` | Frontend: HTML, CSS, JS modules; served by Flask from repo root |
| `config/` | NEAT config files in **config/neat/** (read at runtime via `get_root_dir()`). Also `config/eslint.config.js`, `config/.env.example` (copy to root `.env`). |
| `tests/` | Pytest test suite |
| `examples/` | Example scripts (api_usage, evolution_batch, time_signal_showcase) |
| `data/` | Runtime data: `community.db`, `genealogy.db` (gitignored; created on first run) |

---

## Architecture notes

- **Researchers and evolution-only changes:** See [RESEARCHER_GUIDE.md](../RESEARCHER_GUIDE.md) for touchpoints (signals, NEAT, reproduction, rendering).
- **Src layout:** All Python lives in `src/eyecatcher/`. **Use relative imports** inside the package (e.g. `from ..representation import get_representation`). Code outside imports from `eyecatcher.experiment`, `eyecatcher.evolution`, `eyecatcher.representation`, `eyecatcher.genome`, `eyecatcher.glsl`, etc.
- **Stateless API:** The server does **not** hold population state. Clients send full genome payloads in requests (e.g. `/api/compile`, `/api/evolve`). Do not add server-side population storage.
- **Dual-CPPN:** Each individual is a `DualGenome`: two NEAT genomes (`visual` and `time_signal`) evolved together. Mutations and crossovers operate on both; keep the pairing consistent.
- **Paths:** `get_root_dir()` in `src/eyecatcher/__init__.py` returns the repo root. Use it (or paths relative to it) for `config/`, `static/`, `data/`. Flask's `static_folder` is set to that root `static/` directory.

---

## Code style

- **Python:** Ruff. Line length 88, target Python 3.9, rules E/F/I/N/W/UP, double quotes. Config in [pyproject.toml](../pyproject.toml).
- **Commits:** Conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`.
- **Docstrings:** Google style with Args/Returns where relevant.
- **Types:** Type hints used widely; `TYPE_CHECKING` for circular import guards.

---

## Testing

**Framework:** pytest (`testpaths = ["tests"]` in [pyproject.toml](../pyproject.toml)).
**Test modules:** `test_cppn_engine.py`, `test_substrate_compile.py`, `test_shader_compiler.py`, `test_genome_serialization.py`, `test_api.py`, `test_visualization.py`, `test_community_routes.py`, `test_genealogy_routes.py`, `test_signal_registry.py`. They cover `evolution/`, `genome/`, `representation/`, `glsl/`, `signals/`, `inspection/`, and web/API/genealogy/community routes.
**API tests:** Flask test client — `from eyecatcher.server import app` then `app.test_client()`.
**Evolution API:** Representation protocol: `rep.mutate(ind, key)`, `rep.crossover(a, b, key)`; genome operators also take a `key` argument.

### How to run tests (coding agents)

Run pytest from **whatever virtualenv the project uses** — the venv name is not fixed (the [Makefile](../Makefile) creates `.venv` by default, but the workspace may use another name). **Discover** a venv by trying common locations and use the first that has `pytest`. Do **not** use bare `pytest` or `make test` unless the venv is activated; otherwise you may get `ModuleNotFoundError: No module named 'eyecatcher'` or `No module named 'neat'`.

**1. Discover and run (Unix/macOS, from repo root)**

Try these venv directories in order; run the first that contains an executable `pytest`:

```bash
for v in .venv venv env; do
  [ -x "$v/bin/pytest" ] && "$v/bin/pytest" --tb=short -q && break
done
```

If you already know the venv path (e.g. from a previous run or the Makefile), you can call it directly:
`<venv_dir>/bin/pytest --tb=short -q`

**2. Windows**

Same idea: try in order `.venv`, `venv`, `env`; for each, if `<dir>\Scripts\pytest.exe` exists, run it with the same args.

**3. Subset or skip slow**

Append to the pytest invocation, e.g.:
`<venv_dir>/bin/pytest tests/test_cppn_engine.py tests/test_substrate_compile.py --tb=short -q`
or
`<venv_dir>/bin/pytest tests/ -m "not slow" --tb=short -q`

**4. Coverage (optional)**
For coverage reports, add `--cov=src/eyecatcher --cov-fail-under=40` (or see [pyproject.toml](../pyproject.toml) / CI). The above commands are the general way to run tests.

**5. If no venv works**

If none of the tried directories exist or pytest fails with import errors: do not block. Complete the change, then ask the user to run tests locally (`make install` then `make test`, or ensure a venv exists and run the command above). In restricted sandboxes, `pip install` often fails (network/SSL), so the agent should not depend on installing deps itself.

### Test quality (when adding or changing tests)

- **Avoid trivial assertions** — Assert things that would fail on regression (e.g. key, structure, exact values), not always-true conditions like `len(x) >= 0`.
- **Prefer deterministic tests** — For edge cases (e.g. "one hidden node"), construct minimal data (e.g. via JSON or a shared helper in conftest) instead of "try N random and skip if not found".
- **Round-trip tests** — For serialize/deserialize, assert that behavior is preserved (e.g. same query output), not only that types or ranges are correct.
- **Document skips** — If a test must skip (e.g. missing data), make the skip reason explicit so it's clear the skip is intentional.

---

## Git workflow

- Default development branch: `dev`. PRs target `dev` (or `main` once consolidated).
- CI (GitHub Actions) runs on push/PR to `main` and `dev`: pytest, `ruff check`, `ruff format --check`, ESLint/Prettier for JS.
- **Do not skip pre-commit:** Always let hooks run on commit (Ruff, Prettier, ESLint, etc.). Fix failures rather than using `--no-verify`.

---

## Boundaries

- **Always:** Run `pytest` and `ruff check` (and fix issues) before committing, or use `pre-commit install` so hooks run on commit; use relative imports inside `src/eyecatcher/`; preserve the stateless API contract (no server-side population state).
- **Ask first:** Adding new dependencies; changing NEAT config files; modifying the GLSL shader template in `src/eyecatcher/glsl/shader_compiler.py`; changing DB schema (community or genealogy).
- **Never:** Commit secrets or real API keys; modify files in `data/` (runtime-generated DBs); hardcode absolute paths; break the `DualGenome` visual + time_signal pairing; **skip repo health precautions** — do not use `git commit --no-verify` or otherwise bypass pre-commit hooks; fix lint/format/test failures so commits pass the hooks.
