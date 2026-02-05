# Eyecatcher

Time-varying CPPN (Compositional Pattern Producing Network) evolution system. Like Picbreeder, but patterns change over time and react to user input.

## Features

- **Dual-CPPN Architecture**: Each individual has two evolved networks (visual + time signal).
- **Rich Input Signals**: Patterns react to mouse speed, distance to cursor, and activity (smoothed, speed-boosted).
- **Signal Controls**: Toggle which inputs affect each CPPN via the web UI.
- **GPU Rendering**: CPPNs compile to GLSL for real-time WebGL in the browser.
- **Interactive Evolution**: Web interface for selection, breeding, saving, and community submission.
- **Debug Overlay**: Real-time signal values; optional time-output sampling.

## Running the project

### 1. Run with Docker locally (test the website)

Use this to test the full stack as it runs in production, without installing Python or dependencies on your machine.

**Environment setup**

- Install [Docker](https://docs.docker.com/get-docker/) and Docker Compose.
- No `.env` file is required: `docker-compose.yml` sets `PORT=8080`, `FLASK_ENV=development`, and `ADMIN_KEY=ALICE` for local use. Optionally copy [.env.example](.env.example) to `.env` and override (e.g. `ADMIN_KEY`) if you want; docker-compose will use it when you pass `env_file: .env` or set variables there.
- `data/seeds.json` is in the repo; the community DB (`data/community.db`) is created at first run.

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
  This installs pytest (and black); no `.env` or other config is needed for tests.
- NEAT config files in [config/](config/) (`neat_config.txt`, `neat_config_time.txt`) are in the repo already.

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
python server.py
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
5. **Population** – New random, from seeds, from community, or load/save/export from local storage.
6. **Submit to community** – Share patterns for moderation and inclusion in the seed pool.
7. **Signal controls** – Toggle which inputs (time, mouseSpeed, mouseDist, activity) feed into each CPPN.
8. **Debug overlay** – Real-time signal values; optional time CPPN output sampling.

## Project layout

- **static/** – Frontend assets: HTML, CSS, and JavaScript (interactive viewer, debug overlay, population/community UI, pattern renderer). All browser-loaded files live here.
- **data/** – Runtime data: curated seeds (`seeds.json`) and community DB. Git tracks seeds; `community.db` is gitignored.
- **tests/** – Test suite (pytest). Run with `pytest` from repo root.
- **demos/** – Runnable examples: batch evolution (`evolution_batch.py`), programmatic API (`api_usage.py`), time-signal plot (`time_signal_showcase.py`). Use dual-CPPN API; run from repo root.
- **config/** – NEAT config files (`neat_config.txt`, `neat_config_time.txt`) for visual and time-signal CPPNs.
- **Root** – Backend and deploy: Python modules (`server.py`, `cppn_engine.py`, etc.), `pyproject.toml`, Docker/deploy files (`Dockerfile`, `docker-compose.yml`, `railway.json`, `run.sh`). Entrypoint: `server:app`.

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

- **Endpoints:** `POST /api/compile` (genomes → shaders), `POST /api/random` (size → new genome JSONs), `GET /api/seeds` (curated seeds), `POST /api/breed` (body: `parents` + optional `population_size` → `children`), `POST /api/save` (body: `genome`), `POST /api/time-output` (body: genome + inputs, for debug).
- **Flow:** Open the page → "New random population" (or "New from Seeds" / "Load Saved") → client receives and stores genomes; compile, breed, and save all send or use those genomes. No server-side lookup by id.
- **Consequences:** Works with load balancing and multiple instances; sessions survive server restarts via client storage; local testing needs only the stateless endpoints.

### Core components

- **CPPN Engine** ([cppn_engine.py](cppn_engine.py)) – `CPPNEngine`, `DualGenome`, mutation/crossover, JSON serialization.
- **Shader Compiler** ([shader_compiler.py](shader_compiler.py)) – CPPN → GLSL; `compile_dual_to_glsl()` for the web renderer.
- **Server** ([server.py](server.py)) – Flask app: stateless API (compile, random, seeds, breed, save, time-output), community routes, static serving.

## API usage (programmatic)

```python
from cppn_engine import CPPNEngine, create_random_dual_genome

engine = CPPNEngine()
engine.create_population()
dual_genome = create_random_dual_genome(engine, genome_id=0)

# Query
r, g, b = engine.query_dual_cppn(
    dual_genome, x=0.5, y=0.5, raw_time=0.5,
    mouse_speed=0.2, mouse_distance=0.3, inactivity=0.0
)
```

Compile to shader: [shader_compiler.py](shader_compiler.py) `ShaderCompiler().compile_dual_to_glsl()`. Evolution: `engine.mutate_dual_genome()`, `engine.crossover_dual_genomes()`.

## Creating videos

After generating animation frames into `output/frames/`:

```bash
ffmpeg -i output/frames/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4
ffmpeg -i output/frames/frame_%03d.png -vf "fps=30,scale=512:-1:flags=lanczos" output.gif
```

## Requirements

Python 3.9+. Dependencies are in [pyproject.toml](pyproject.toml) (neat-python, numpy, pillow, flask, flask-cors, matplotlib). Dev: `pip install -e ".[dev]"` for pytest and black.

## Future work

- [ ] Direct video export (MP4/GIF) from UI
- [ ] Multiple fitness functions for aesthetic properties
- [ ] 3D patterns (add z coordinate)
- [ ] Multi-resolution rendering
- [ ] Save/load evolution sessions
- [ ] Real-time shader editing
