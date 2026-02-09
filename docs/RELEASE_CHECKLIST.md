# Release / Open-Source Readiness Checklist

Use this checklist before tagging a release or making the repository public.

## Security and secrets

- [ ] **No secrets in git history** — Run `git log -p | grep -iE 'password|secret|api_key|token'` (or use [git-secrets](https://github.com/awslabs/git-secrets)). The default `ADMIN_KEY=ALICE` in dev is documented as dev-only and is acceptable.
- [ ] **Env template only** — `.env.example` is the only env template and contains no real values (only placeholders like `your-admin-secret`).

## Code quality and tests

- [ ] **Tests pass** — From repo root: `make install` then `make test` (or `pip install -e ".[dev]"` and `pytest -v`).
- [ ] **Linting** — `make lint`; run `ruff format --check .` and `npm run format:check` for format checks (or rely on CI).

## Build and run

- [ ] **Docker build** — `make docker-up` or `docker compose -f docker/docker-compose.yml up --build`; open http://localhost:5001 and confirm the app loads.
- [ ] **Fresh clone** — In a separate directory, clone the repo, follow the README (e.g. Quick Start or local setup), and confirm you can run tests and the server.

## GitHub / repository

- [ ] **Repository description and topics** — Set description and topics (e.g. `cppn`, `neuroevolution`, `generative-art`, `interactive-evolution`) in repo Settings.
- [ ] **Social preview** — Optionally set a social preview image in Settings → General.
- [ ] **Branch protection** — For `main` (or default branch): require PR reviews and CI to pass before merge (optional but recommended).

## Before first public release

- [ ] **LICENSE** — Confirm copyright holder in [LICENSE](LICENSE) is correct.
- [ ] **CODE_OF_CONDUCT / SECURITY** — Add a contact method in [.github/CODE_OF_CONDUCT.md](../.github/CODE_OF_CONDUCT.md) and [.github/SECURITY.md](../.github/SECURITY.md) if you want private vulnerability reports.
