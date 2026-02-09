# Cleanup Checklist

Use this checklist to find and fix outdated or unneeded code, config, docs, and assets after refactors or growth. Work one section at a time; run relevant commands (grep, pytest, ruff) and fix issues before checking boxes. Update the list when you remove or change things so it stays accurate.

---

## 1. Code and package structure

### 1.1 Entry points and roots

- [x] **main.py** – Confirm whether to keep (legacy stub that points to demos) or remove; if kept, ensure it does not reference old paths or seeds.
- [x] **Run paths** – Verify `python -m eyecatcher.server` and `run.sh` (gunicorn `eyecatcher.server:app`) are the only documented/runtime entry points; no stray `server.py` or `python server.py` references in docs or scripts.

### 1.2 Imports and references

- [x] **Package imports** – No remaining absolute imports of old top-level modules (`cppn_engine`, `shader_compiler`, `genome_serialization`, `server`, etc.) outside `src/eyecatcher/`; demos and tests use `from eyecatcher.xxx`.
- [x] **Relative vs package** – All code inside `src/eyecatcher/` uses relative imports (e.g. `from .cppn_engine import ...`); no `from genome_serialization` or `from server` at package level.

  **Check:** From repo root, `grep -r 'from cppn_engine import\|from shader_compiler import\|from genome_serialization import\|from server import' --include='*.py' .` should find no matches outside `src/eyecatcher/` (or only in comments).

### 1.3 Dead or deprecated code

- [x] **Commented-out blocks** – `src/eyecatcher/server.py` lines ~424–438: "deprecated" stateful endpoint comments; decide keep (as history) or remove.
- [x] **TODO/FIXME/XXX/HACK** – Grep for these; either resolve or convert to tracked issues and remove from code.
- [x] **Unused exports** – From `src/eyecatcher/`: any public functions/classes never imported by demos, tests, or other modules; consider removing or documenting as internal. (Verified: public API is used by demos, tests, or re-exported.)

### 1.4 Dependencies

- [x] **pyproject.toml** – Every runtime dependency is used in code; remove any that are not. Dev deps (pytest, ruff) match CONTRIBUTING/AGENTS and CI.

---

## 2. Configuration

### 2.1 NEAT configs

- [x] **Which are used** – `cppn_engine.py` defaults: `neat_config_experimental.txt` and `neat_config_time_experimental.txt`. The non-experimental `neat_config.txt` and `neat_config_time.txt` are not default; decide keep for switching or remove if truly obsolete.
- [x] **Naming and docs** – README/AGENTS mention "config/"; list matches actual files and intended use (e.g. "experimental" vs "stable").

### 2.2 Environment and deploy

- [x] **.env.example** – Every variable used in code (or in README for deploy) is listed; no leftover seeds or removed feature vars.
- [x] **Docker** – Dockerfile and docker-compose.yml: no reference to `server.py`, `data/seeds.json`, or old paths; `PYTHONPATH` and `command` match package layout.
- [x] **railway.json** – `startCommand` and `healthcheckPath` still valid for current app.

---

## 3. Documentation vs reality

### 3.1 README

- [x] **Quick Start and run instructions** – Commands (Docker, `python -m eyecatcher.server`, pytest) work as written.
- [x] **Project layout** – Matches repo (e.g. `src/eyecatcher/`, `static/`, `config/`, `data/`); no seeds or removed features.
- [x] **API / endpoints** – List matches actual routes (no GET /api/seeds, etc.); server one-liner matches.
- [x] **Code examples** – Snippets use `eyecatcher` package and current API (e.g. `mutate_dual_genome(..., new_key=...)`).

### 3.2 AGENTS.md

- [x] **Commands** – Match current tooling (ruff, pytest, docker compose, `python -m eyecatcher.server`).
- [x] **Structure and boundaries** – `data/` and "Never" rules reflect current design (no seeds); paths and entry points correct.

### 3.3 CONTRIBUTING, SECURITY, RELEASE_CHECKLIST

- [x] **CONTRIBUTING** – Setup and commands (venv, `pip install -e ".[dev]"`, ruff, pytest) and branch/PR flow match repo and CI.
- [x] **SECURITY** – Supported versions and reporting flow still accurate.
- [x] **RELEASE_CHECKLIST** – Items still relevant; no seeds or obsolete steps.

---

## 4. Static assets and frontend

### 4.1 Server routes vs files

- [x] **JS/CSS routes** – Every file under `static/` that is served has a matching route in `server.py` (or is included by HTML); no route points to a missing file.
- [x] **HTML** – `interactive_viewer.html` and `genealogy_viewer.html` exist and are the only HTML entry points if that's intended.

### 4.2 Orphaned or duplicate assets

- [x] **Unused CSS/JS** – No file in `static/` that is never linked or requested (e.g. from HTML or other JS); remove or document if intentional.
- [x] **Broken or outdated links** – No script/link in HTML or JS pointing to old paths or removed endpoints (e.g. /api/seeds).

---

## 5. Data and generated content

### 5.1 data/

- [x] **Intent** – Only community and genealogy DBs (and any future runtime files); no seeds or legacy files. .gitignore ignores the DBs; nothing tracks `seeds.json` if it's gone.
- [x] **Docker/CI** – Image creates `data/` if needed; no COPY of removed seeds.

### 5.2 output/ and llm_test/

- [x] **output/** – Confirmed gitignored; README/docs describe it as generated.
- [x] **llm_test/** – Contains `chat prompt.png` and `pattern_gifs_gen*.zip`; not referenced by code. Decide: add to .gitignore and stop tracking, or move to docs/assets and reference, or remove from repo.

---

## 6. Tests and CI

### 6.1 Test suite

- [x] **Coverage** – Every public API surface (engine, compiler, serialization, server routes) has at least one test; no test file for a removed feature.
- [x] **Imports and assertions** – Tests use `eyecatcher` package and current signatures (e.g. `new_key` for mutate/crossover); no references to seeds or old modules.

### 6.2 CI

- [x] **.github/workflows/ci.yml** – Install command (`pip install -e ".[dev]"`), pytest, ruff check/format match repo; triggers (branches) match your workflow (e.g. main, dev).

---

## 7. Repository hygiene

### 7.1 .gitignore

- [x] **Ignore list** – Covers build artifacts, venvs, `.env`, DBs, output, and any local/tooling dirs (e.g. `.cursor/`). No need to ignore `*.md` or critical docs.
- [x] **.dockerignore** – Aligns with Dockerfile (e.g. no need to copy tests/docs into image unless intended); no accidental exclusion of `src/` or `config/`.

### 7.2 Branches and defaults

- [x] **Default branch** – Docs (CONTRIBUTING, AGENTS) and CI mention the correct default (e.g. dev or main).
- [x] **Stale branches** – Optional: list branches that are merged or abandoned and can be deleted. (Deferred; no change.)
