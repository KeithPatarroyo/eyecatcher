# Eyecatcher

[![CI](https://github.com/KeithPatarroyo/eyecatcher/actions/workflows/ci.yml/badge.svg)](https://github.com/KeithPatarroyo/eyecatcher/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Time-varying CPPN (Compositional Pattern Producing Network) evolution system. Like Picbreeder, but patterns change over time and react to user input.

## Quick Start

```bash
make docker-up
```

Then open **http://localhost:5001**. (Runs `docker compose -f docker/docker-compose.yml up --build` under the hood.) For other options (local Python, tests, deployment), see [Running the project](#running-the-project) below. Common dev tasks: **`make help`** (list targets), **`make test`**, **`make lint`**, **`make format`**.

## Features

- **Dual-CPPN Architecture**: Each individual has two evolved networks (visual + time signal).
- **Configurable input signals** (time, mouse, distance, etc.) and **signal controls** in the UI; see [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md) for how to add or change signals.
- **GPU Rendering**: CPPNs compile to GLSL for real-time WebGL in the browser.
- **Interactive Evolution**: Web interface for selection, evolution, saving, and community submission.
- **Genealogical Tree**: Track evolutionary history across generations and branches; explore and continue from any point.
- **Debug Overlay**: Real-time signal values; optional time-output sampling.

## Running the project

### 1. Run with Docker locally (test the website)

Use this to test the full stack as it runs in production, without installing Python or dependencies on your machine.

**Environment setup**

- Install [Docker](https://docs.docker.com/get-docker/) and Docker Compose.
- No `.env` file is required: `docker/docker-compose.yml` sets `PORT=8080`, `FLASK_ENV=development`, and `ADMIN_KEY=ALICE` for local use. Optionally copy [config/.env.example](config/.env.example) to `.env` in the repo root; Docker Compose loads `.env` from the project directory when you run from the repo root.
- The community DB (`data/community.db`) is created at first run.

**Commands**

```bash
# From the repo root
make docker-up
```

Then open **http://localhost:5001** in your browser. The app listens on 8080 inside the container; compose maps host 5001 → 8080.

To stop: `Ctrl+C`, or `docker compose -f docker/docker-compose.yml down` if you need to tear down the stack.

---

### 2. Deploy to Railway (from terminal)

Deploy the current project to [Railway](https://railway.app) using the Railway CLI. The repo already contains [railway.json](railway.json) and [docker/Dockerfile](docker/Dockerfile); Railway will build the image and run `./run.sh` (Gunicorn). No config files need to be edited for deploy.

**Environment setup**

- Install the [Railway CLI](https://docs.railway.app/develop/cli) and log in:
  ```bash
  npm i -g @railway/cli
  railway login
  ```
- Link this repo to a Railway project (first time only):
  ```bash
  cd /path/to/eyecatcher
  railway link
  ```
  If you don’t have a project yet, create one in the [Railway dashboard](https://railway.app/dashboard) or run `railway init` and follow the prompts.

**Constants / variables to set in Railway**

In the Railway project dashboard (or via CLI), set:

| Variable        | Description                          | Example / note                    |
| --------------- | ------------------------------------ | --------------------------------- |
| `ADMIN_KEY`     | Secret for community moderation API  | Pick a strong secret; e.g. not `ALICE` |
| `CORS_ORIGINS`  | Allowed origins (comma-separated)    | Your app URL, or `*` for dev      |
| `DATABASE_PATH` | Optional; SQLite path in container    | Default `data/community.db`       |

`PORT` is set by Railway automatically; do not override it.

**Commands**

```bash
# From the repo root (after railway link)
railway up
```

Railway will build from [docker/Dockerfile](docker/Dockerfile) and deploy. The dashboard shows the public URL. Health checks use `/health` (see [railway.json](railway.json)).

---

### 3. Run local tests (no Docker)

Run tests on your machine with Python. No server or browser required.

**Environment setup**

- Python 3.9+.
- From the repo root, run **`make install`** — it creates the venv, installs the Python package and dev deps (pytest, ruff, pre-commit), and installs npm deps for JS lint/format. Then activate the venv (`source .venv/bin/activate` or Windows: `.venv\Scripts\activate`) and run **`pre-commit install`** to run checks on each commit (see [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)). Alternatively, create a venv manually, then `pip install -e ".[dev]"` and `npm install`.
- NEAT config files in [config/neat/](config/neat/) (visual and time-signal; default is `*_experimental.txt`; `neat_config.txt` / `neat_config_time.txt` in that folder are alternatives).

**Commands**

```bash
# From the repo root (with venv activated)
make test
```

To run a specific test file:

```bash
pytest tests/test_visualization.py -v
```

No constants or templates need to be filled beforehand; tests use the default config paths and in-memory state. For all targets (lint, format, dev, docker, etc.), run **`make help`**.

---

### Other ways to run

**Interactive evolution server (plain Python, no Docker)**

After **`make install`** and activating the venv, run:

```bash
make dev
```

Or `python -m eyecatcher.server`. Then open **http://localhost:5001**. Optional: copy [config/.env.example](config/.env.example) to `.env` in the repo root and set `PORT`, `CORS_ORIGINS`, `ADMIN_KEY`, `DATABASE_PATH` if you want to override defaults.

**Examples (batch evolution, API usage, time-signal plot)** – Live in `examples/`. Run from repo root, e.g.:

```bash
python examples/api_usage.py            # create, render, compile, mutate, crossover
python examples/evolution_batch.py      # batch evolution with proxy fitness
python examples/time_signal_showcase.py # plot time CPPN output (requires matplotlib)
```

## Interactive Evolution (web UI)

The web interface lets you:

1. **View patterns** – Grid of animated CPPN patterns (zoom with controls).
2. **Click to select** – Left-click to increase fitness; right-click to undo.
3. **Breed** – Create a new generation from selected parents.
4. **Save** – Download patterns as shaders, images, and genome visualizations.
5. **Population** – New random, from community, or load/save/export from local storage.
6. **Submit to community** – Share patterns for moderation and inclusion in the community pool.
7. **Signal controls** – Toggle which inputs feed into each CPPN ([RESEARCHER_GUIDE](RESEARCHER_GUIDE.md)).
8. **Debug overlay** – Real-time signal values; optional time CPPN output sampling.
9. **Genealogical tree** – View evolutionary history; branch and continue from any generation.

## Genealogical Tree

The genealogy system automatically tracks all populations across evolution sessions:

- **Auto-save**: Every generation is automatically saved to a tree structure
- **Branch & explore**: Load any previous generation and continue evolving in a new branch
- **Tree visualization**: Interactive graph showing all populations, branches, and parent relationships
- **Time travel**: Click any node to load that population into the main viewer
- **Multiple branches**: Create parallel evolutionary paths; each "New random population" starts a new branch

Access the genealogy viewer at `/genealogy` or click "🌳 Genealogy Tree" in the main interface.

## Project layout

- **static/** – Frontend (viewer, community, genealogy). See [static/js/README.md](static/js/README.md) for structure.
- **data/** – Community and genealogy DBs (gitignored; created on first run).
- **tests/** – Pytest suite. See [tests/README.md](tests/README.md).
- **examples/** – [examples/README.md](examples/README.md): `api_usage.py`, `evolution_batch.py`, `time_signal_showcase.py`.
- **config/** – NEAT config in **config/neat/**; experiment presets in `experiments.json`. See [config/neat/README.md](config/neat/README.md) and [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md).
- **src/eyecatcher/** – Python package. Entry: `server.py`. Layout and “where to edit”: [src/eyecatcher/README.md](src/eyecatcher/README.md) and [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md).
- **Root** – Makefile, pyproject.toml, **docker/** (Dockerfile, docker-compose), **scripts/** (run.sh). Contributing: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

Generated output (saved patterns, frames) → `output/` (gitignored).

## Architecture

**Dual-CPPN default:** Each individual has two CPPNs (visual + time); inputs/outputs are defined by the signal system. **Stateless API:** The client stores genomes (e.g. IndexedDB) and sends them on compile/evolve/save; no server-side population. Endpoints: `POST /api/compile`, `/api/random`, `/api/evolve`, `/api/save`, `/api/time-output`, `/api/network`, `/api/adjust-weight`.

For object model, signals, NEAT, reproduction, and where to edit: [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md).

## API usage (programmatic)

Use the representation API; the server and examples use the same interface.

```python
from eyecatcher.experiment import get_configured_representation
from eyecatcher.representation import get_representation

rep = get_configured_representation()
ind = rep.create_random(0)
rep.render_to_image(ind, resolution=(256, 256), extra_inputs={"raw_time": 0.5})
rep.compile_to_shader(ind)
child = rep.mutate(ind, key=1)
```

See [examples/api_usage.py](examples/api_usage.py) and [RESEARCHER_GUIDE.md](RESEARCHER_GUIDE.md).

## Creating videos

After generating animation frames into `output/frames/`:

```bash
ffmpeg -i output/frames/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4
ffmpeg -i output/frames/frame_%03d.png -vf "fps=30,scale=512:-1:flags=lanczos" output.gif
```

## Requirements

Python 3.9+. Dependencies are in [pyproject.toml](pyproject.toml) (neat-python, numpy, pillow, flask, flask-cors, matplotlib). For development, run **`make install`** to get pytest, ruff, pre-commit, and JS lint/format tooling (or install manually: `pip install -e ".[dev]"` and `npm install`).

## Future work

- [ ] Direct video export (MP4/GIF) from UI
- [ ] Multiple fitness functions for aesthetic properties
- [ ] 3D patterns (add z coordinate)
- [ ] Multi-resolution rendering
- [ ] Save/load evolution sessions
- [ ] Real-time shader editing

## Contributing

Contributions are welcome. See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for setup, code style, and the pull request process. AI coding agents: see [.github/AGENTS.md](.github/AGENTS.md).

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
