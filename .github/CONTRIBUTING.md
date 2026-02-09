# Contributing to Eyecatcher

Thank you for your interest in contributing. This document explains how to get set up and how we work.

## Ways to contribute

- **Code**: Bug fixes, new features, refactors.
- **Documentation**: Improve README, docstrings, or add guides.
- **Issues**: Report bugs or suggest features via [GitHub Issues](https://github.com/KeithPatarroyo/eyecatcher/issues).
- **Testing**: Add or improve tests, or help verify behaviour on different setups.

## Development setup

1. **Clone and enter the repo**
   ```bash
   git clone https://github.com/KeithPatarroyo/eyecatcher.git
   cd eyecatcher
   ```

2. **Create a virtual environment and install the project**
   ```bash
   make install
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
   This creates `.venv`, installs the package in editable mode plus dev deps (pytest, ruff, pre-commit), and runs `npm install` for JS lint/format. Alternatively, run `python -m venv .venv`, activate it, then `pip install -e ".[dev]"` and `npm install` manually.

   For all available targets (test, lint, format, dev, etc.), run **`make help`**.

3. **Install pre-commit hooks (recommended)**
   ```bash
   pre-commit install
   ```
   This runs Ruff (lint + format) and a few sanity checks automatically on each commit. You can still run `ruff check .` and `ruff format .` manually.

4. **Run tests**
   ```bash
   make test
   ```
   Or `pytest` directly; run a specific file: `pytest tests/test_visualization.py -v`. See **`make help`** for other targets.

5. **Optional: run the app locally**
   ```bash
   python -m eyecatcher.server
   ```
   Then open http://localhost:5001. See [README.md](../README.md) for Docker and other options.

No `.env` file is required for running tests; the app can use defaults for local development.

## Code style

- **Formatting and linting**: We use [Ruff](https://docs.astral.sh/ruff/) for Python and ESLint/Prettier for JavaScript (see [package.json](../package.json)). We recommend [pre-commit](https://pre-commit.com/) so checks run automatically on commit (`pre-commit install` after `pip install -e ".[dev]"`). You can run **`make lint`** and **`make format`** for Python and JS; without Make, run `ruff check .`, `ruff format .`, and `npm run lint` / `npm run format:check` as needed.
- **Docstrings**: Use docstrings for public modules, classes, and functions; include Args/Returns where helpful.

## Pull request process

1. **Open an issue** (optional but helpful) for non-trivial changes so we can align on approach.
2. **Branch from `dev`** (or the default branch). Use a short, descriptive branch name.
3. **Make your changes** and ensure tests pass (`make test` or `pytest`).
4. **Commit** with clear, conventional-style messages:
   - `feat: add X`
   - `fix: correct Y`
   - `docs: update Z`
   - `refactor: ...`, `test: ...`, `chore: ...` as appropriate.
5. **Push** and open a Pull Request against the default branch.
6. **Address review** if requested. Once approved and CI is green, a maintainer will merge.

## Reporting bugs

Open an issue and include:

- What you did (steps to reproduce).
- What you expected vs what happened.
- Your environment (OS, Python version, how you ran the app — e.g. Docker, `python -m eyecatcher.server`).
- Any relevant logs or error messages.

## Asking for help

- **Questions and ideas**: Open a [GitHub Discussion](https://github.com/KeithPatarroyo/eyecatcher/discussions) or an issue.
- **Security concerns**: See [SECURITY.md](SECURITY.md); do not report security vulnerabilities in public issues.

Thank you for contributing.

## Maintainers: releasing

Before tagging a release or going public, see [docs/RELEASE_CHECKLIST.md](../docs/RELEASE_CHECKLIST.md).
