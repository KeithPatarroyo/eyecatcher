# Eyecatcher

[![CI](https://github.com/KeithPatarroyo/eyecatcher/actions/workflows/ci.yml/badge.svg)](https://github.com/KeithPatarroyo/eyecatcher/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Time-varying CPPN (Compositional Pattern Producing Network) evolution system. Like Picbreeder, but patterns change over time and react to user input.

## Quick Start

```bash
docker compose up --build
```

Then open **http://localhost:5001**. You can also use **`make docker-up`** from the repo root. For other options (local Python, tests, deployment), see [Running the project](#running-the-project) below. Common dev tasks: **`make help`** (list targets), **`make test`**, **`make lint`**, **`make format`**.

## Features

- **Dual-CPPN Architecture**: Each individual has two evolved networks (visual + time signal).
- **Rich Input Signals**: Patterns react to mouse speed, distance to cursor, and activity (smoothed, speed-boosted).
- **Signal Controls**: Toggle which inputs affect each CPPN via the web UI.
- **GPU Rendering**: CPPNs compile to GLSL for real-time WebGL in the browser.
- **Interactive Evolution**: Web interface for selection, breeding, saving, and community submission.
- **Genealogical Tree**: Track evolutionary history across generations and branches; explore and continue from any point.
- **Debug Overlay**: Real-time signal values; optional time-output sampling.

## Running the project

### 1. Run with Docker locally (test the website)

Use this to test the full stack as it runs in production, without installing Python or dependencies on your machine.

**Environment setup**

- Install [Docker](https://docs.docker.com/get-docker/) and Docker Compose.
- No `.env` file is required: `docker-compose.yml` sets `PORT=8080`, `FLASK_ENV=development`, and `ADMIN_KEY=ALICE` for local use. Optionally copy [.env.example](.env.example) to `.env` and override (e.g. `ADMIN_KEY`) if you want; docker-compose will use it when you pass `env_file: .env` or set variables there.
- The community DB (`data/community.db`) is created at first run.

**Commands**

```bash
# From the repo root
docker compose up --build
```

Then open **http://localhost:5001** in your browser. The app listens on 8080 inside the container; compose maps host 5001 → 8080.

To stop: `Ctrl+C`, or `docker compose down`.

---

### 2. Deploy to Railway (from terminal)

Deploy the current project to [Railway](https://railway.app) using the Railway CLI. The repo already contains [railway.json](railway.json) and [Dockerfile](Dockerfile); Railway will build the image and run `./run.sh` (Gunicorn). No config files need to be edited for deploy.

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

Railway will build from the Dockerfile and deploy. The dashboard shows the public URL. Health checks use `/health` (see [railway.json](railway.json)).

---

### 3. Run local tests (no Docker)

Run tests on your machine with Python. No server or browser required.

**Environment setup**

- Python 3.9+.
- Create a virtual environment and install the project plus dev dependencies:
  ```bash
  python -m venv .venv
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  pip install -e ".[dev]"
  ```
  This installs pytest, ruff, and pre-commit; no `.env` or other config is needed for tests. Run `pre-commit install` to run Ruff on each commit (see [CONTRIBUTING.md](CONTRIBUTING.md)).
- NEAT config files in [config/](config/) (visual and time-signal; default is `*_experimental.txt`; `neat_config.txt` / `neat_config_time.txt` are alternatives).

**Commands**

```bash
# From the repo root, with venv activated
pytest
```

To run a specific test file:

```bash
pytest tests/test_visualization.py -v
```

No constants or templates need to be filled beforehand; tests use the default config paths and in-memory state.

---

### Other ways to run

**Interactive evolution server (plain Python, no Docker)**

```bash
# After creating a venv, activating it, and running: pip install -e .
python -m eyecatcher.server
```

Then open **http://localhost:5001**. Optional: copy [.env.example](.env.example) to `.env` and set `PORT`, `CORS_ORIGINS`, `ADMIN_KEY`, `DATABASE_PATH` if you want to override defaults.

**Demos (batch evolution, API usage, time-signal plot)** – Live in `demos/`. Run from repo root, e.g.:

```bash
python demos/api_usage.py            # create, render, compile, mutate, crossover
python demos/evolution_batch.py      # batch evolution with proxy fitness
python demos/time_signal_showcase.py # plot time CPPN output (requires matplotlib)
```

## Interactive Evolution (web UI)

The web interface lets you:

1. **View patterns** – Grid of animated CPPN patterns (zoom with controls).
2. **Click to select** – Left-click to increase fitness; right-click to undo.
3. **Breed** – Create a new generation from selected parents.
4. **Save** – Download patterns as shaders, images, and genome visualizations.
5. **Population** – New random, from community, or load/save/export from local storage.
6. **Submit to community** – Share patterns for moderation and inclusion in the community pool.
7. **Signal controls** – Toggle which inputs (time, mouseSpeed, mouseDist, activity) feed into each CPPN.
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

- **static/** – Frontend assets: HTML, CSS, and JavaScript (interactive viewer, debug overlay, population/community UI, pattern renderer). All browser-loaded files live here.
- **data/** – Runtime data: community DB and genealogy DB (both gitignored; created on first run).
- **tests/** – Test suite (pytest). Run with `pytest` from repo root.
- **demos/** – Runnable examples: batch evolution (`evolution_batch.py`), programmatic API (`api_usage.py`), time-signal plot (`time_signal_showcase.py`). Use dual-CPPN API; run from repo root.
- **config/** – NEAT config files for visual and time-signal CPPNs (`*_experimental.txt` are default; `neat_config.txt`, `neat_config_time.txt` are alternatives).
- **src/eyecatcher/** – Python package: `server`, `cppn_engine`, `shader_compiler`, `genome_serialization`, routes, etc. Entrypoint: `eyecatcher.server:app`.
- **Root** – `pyproject.toml`, Docker/deploy files (`Dockerfile`, `docker-compose.yml`, `railway.json`, `run.sh`), [CONTRIBUTING.md](CONTRIBUTING.md), [LICENSE](LICENSE).

Generated content (saved patterns, network PDFs, frames) goes under `output/` (gitignored).

## Architecture

### Dual-CPPN system

Each individual has two CPPNs that evolve together:

```
[rawTime, mouseSpeed, mouseDist, activity, bias] → Time Signal CPPN → modifiedTime
                                                                            ↓
[x, y, dist, modifiedTime, mouseSpeed, mouseDist, activity, bias] → Visual CPPN → RGB
```

Time Signal has 5 inputs, 1 output; Visual has 8 inputs, 3 outputs. See [config/neat_config_time.txt](config/neat_config_time.txt) and [config/neat_config.txt](config/neat_config.txt) for exact parameters and activation options.

### Stateless API

The server does not hold population state. The client (web UI) stores genomes (e.g. in IndexedDB) and sends them when needed.

- **Endpoints:** `POST /api/compile` (genomes → shaders), `POST /api/random` (size → new genome JSONs), `POST /api/breed` (body: `parents`, optional `population_size`, optional `elitism` → `children`), `POST /api/save` (body: `genome`, optional `visualize` for network PDF), `POST /api/time-output` (body: genome + inputs, for debug).
- **Flow:** Open the page → "New random population" (or "New from Seeds" / "Load Saved") → client receives and stores genomes; compile, breed, and save all send or use those genomes. No server-side lookup by id.
- **Consequences:** Works with load balancing and multiple instances; sessions survive server restarts via client storage; local testing needs only the stateless endpoints. You can run multiple Gunicorn workers (no in-memory population to share).
- **Breeding options:** `elitism` (default `false`) keeps the best parent unchanged in the next generation; set to `true` to preserve top performers.
- **Save options:** `visualize` (default `true`) generates a network PDF alongside pkl, glsl, bundle, and PNG; set to `false` to skip the PDF. The server packages PNG, GLSL, bundle JSON, genome pickle, and optional network PDF into a single zip and returns it in the response; the client triggers one download, so save works on Railway and other hostings with no server filesystem. Set `SAVE_TO_DISK=1` in the environment to also write files under `output/saved/` (e.g. for local dev).

### Core components

- **CPPN Engine** (`src/eyecatcher/cppn_engine.py`) – `CPPNEngine`, `DualGenome`, mutation/crossover, JSON serialization.
- **Shader Compiler** (`src/eyecatcher/shader_compiler.py`) – CPPN → GLSL; `compile_dual_to_glsl()` for the web renderer.
- **Server** (`src/eyecatcher/server.py`) – Flask app: stateless API (compile, random, breed, save, time-output), community routes, static serving.

## API usage (programmatic)

```python
from eyecatcher.cppn_engine import CPPNEngine, create_random_dual_genome

engine = CPPNEngine()
engine.create_population()
dual_genome = create_random_dual_genome(engine, genome_id=0)

# Query
r, g, b = engine.query_dual_cppn(
    dual_genome, x=0.5, y=0.5, raw_time=0.5,
    mouse_speed=0.2, mouse_distance=0.3, inactivity=0.0
)
```

Compile to shader: `eyecatcher.shader_compiler.ShaderCompiler().compile_dual_to_glsl()`. Evolution: `engine.mutate_dual_genome()`, `engine.crossover_dual_genomes()`.

## Creating videos

After generating animation frames into `output/frames/`:

```bash
ffmpeg -i output/frames/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4
ffmpeg -i output/frames/frame_%03d.png -vf "fps=30,scale=512:-1:flags=lanczos" output.gif
```

## Requirements

Python 3.9+. Dependencies are in [pyproject.toml](pyproject.toml) (neat-python, numpy, pillow, flask, flask-cors, matplotlib). Dev: `pip install -e ".[dev]"` for pytest, ruff, and pre-commit.

## Future work

- [ ] Direct video export (MP4/GIF) from UI
- [ ] Multiple fitness functions for aesthetic properties
- [ ] 3D patterns (add z coordinate)
- [ ] Multi-resolution rendering
- [ ] Save/load evolution sessions
- [ ] Real-time shader editing

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, code style, and the pull request process.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
