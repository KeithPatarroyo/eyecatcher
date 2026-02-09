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
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
   This installs the package in editable mode plus dev dependencies (pytest, ruff, pre-commit).

3. **Install pre-commit hooks (recommended)**
   ```bash
   pre-commit install
   ```
   This runs Ruff (lint + format) and a few sanity checks automatically on each commit. You can still run `ruff check .` and `ruff format .` manually.

4. **Run tests**
   ```bash
   pytest
   ```
   Run a specific file: `pytest tests/test_visualization.py -v`.

5. **Optional: run the app locally**
   ```bash
   python -m eyecatcher.server
   ```
   Then open http://localhost:5001. See [README.md](README.md) for Docker and other options.

No `.env` file is required for running tests; the app can use defaults for local development.

## Code style

- **Formatting and linting**: We use [Ruff](https://docs.astral.sh/ruff/). We recommend [pre-commit](https://pre-commit.com/) so Ruff runs automatically on commit (`pre-commit install` after `pip install -e ".[dev]"`). Without pre-commit, run `ruff check .` and `ruff format .` before committing (or `ruff check . --fix` and `ruff format .` to auto-fix).
- **Docstrings**: Use docstrings for public modules, classes, and functions; include Args/Returns where helpful.

## Pull request process

1. **Open an issue** (optional but helpful) for non-trivial changes so we can align on approach.
2. **Branch from `dev`** (or the default branch). Use a short, descriptive branch name.
3. **Make your changes** and ensure tests pass (`pytest`).
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

Before tagging a release or going public, see [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).
