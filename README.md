# Eyecatcher

Time-varying CPPN (Compositional Pattern Producing Network) evolution system. Like Picbreeder, but patterns change over time and react to user input.

## Features

- **Dual-CPPN Architecture**: Each individual has two evolved networks:
  - **Visual CPPN**: Generates RGB colors from spatial coordinates and time
  - **Time Signal CPPN**: Transforms raw time into a unique temporal rhythm
- **Rich Input Signals**: Patterns react to multiple real-time inputs:
  - Mouse movement speed (instantaneous)
  - Distance from mouse to each pattern
  - User activity (smoothed, boosted by speed, decays when still)
- **Signal Controls**: Toggle which inputs affect each CPPN via interactive checkboxes
- **GPU Rendering**: Compiles CPPNs to GLSL shaders for real-time WebGL rendering
- **Interactive Evolution**: Web interface for selecting and breeding patterns
- **Debug Overlay**: Real-time visualization of all input signals
- **NEAT Evolution**: Uses NEAT-Python for evolving network topology and weights

## Quick Start

```bash
# Create and activate a virtual environment (name is up to you)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run interactive evolution server
python server.py
```

Then open **http://localhost:5001** in your browser.

## Interactive Evolution

The web interface allows you to:

1. **View patterns**: 12 animated CPPN patterns rendered in real-time
2. **Click to select**: Left-click patterns you like to increase their fitness
3. **Right-click to undo**: Right-click to decrease fitness (remove accidental clicks)
4. **Breed**: Create a new generation from selected parents
5. **Save**: Download favorite patterns as shaders and images
6. **Interact**: Move your mouse to see patterns react differently
7. **Signal controls**: Toggle which inputs (time, mouseSpeed, mouseDist, inactivity) affect each CPPN
8. **Debug overlay**: Click "Debug" button to see real-time signal values

## Architecture

### Dual-CPPN System

Each individual consists of two CPPNs that evolve together:

```
[rawTime, mouseSpeed, mouseDist, activity, bias] → Time Signal CPPN → modifiedTime
                                                                            ↓
[x, y, dist, modifiedTime, mouseSpeed, mouseDist, activity, bias] → Visual CPPN → RGB
```

This allows each pattern to have its own unique "heartbeat" - how it perceives and responds to time.

### Time Signal CPPN Inputs (5)
- `rawTime`: Linear animation time (-1 to 1)
- `mouseSpeed`: Instantaneous mouse movement speed (0 to 1)
- `mouseDist`: Distance from mouse to pattern center (0 to 1)
- `activity`: Smoothed activity level, boosted by speed, decays when still (0 to 1)
- `bias`: Constant 1.0

### Time Signal CPPN Outputs (1)
- `modifiedTime`: Transformed time signal (-1 to 1)

### Visual CPPN Inputs (8)
- `x`: Horizontal position (-1 to 1)
- `y`: Vertical position (-1 to 1)
- `distance`: Distance from center
- `time`: Modified time from Time Signal CPPN (-1 to 1)
- `mouseSpeed`: Instantaneous mouse movement speed (0 to 1)
- `mouseDist`: Distance from mouse to pattern center (0 to 1)
- `activity`: Smoothed activity level (0 to 1)
- `bias`: Constant 1.0

### Visual CPPN Outputs (3)
- `R`: Red channel (0-1)
- `G`: Green channel (0-1)
- `B`: Blue channel (0-1)

## Core Components

### CPPN Engine (`cppn_engine.py`)
- `CPPNEngine`: Main engine class supporting dual-CPPN individuals
- `DualGenome`: Dataclass holding paired visual and time signal genomes
- Mutation and crossover for both single and dual genomes
- Save/load functionality for dual genomes

### Shader Compiler (`shader_compiler.py`)
- Converts CPPN networks to GLSL fragment shaders
- `compile_to_glsl()`: Single CPPN compilation
- `compile_dual_to_glsl()`: Dual CPPN compilation (time signal + visual)
- Exports shader bundles as JSON

### Server (`server.py`)
- Flask-based web server for interactive evolution
- REST API for population management, breeding, and saving
- Serves the interactive viewer HTML

### Configuration Files
- `neat_config.txt`: Visual CPPN parameters (8 inputs, 3 outputs)
- `neat_config_time.txt`: Time Signal CPPN parameters (5 inputs, 1 output)

## Activation Functions

Available in both networks:
- `sin`, `cos` - Periodic patterns
- `sigmoid`, `tanh` - Smooth gradients
- `gauss` - Gaussian bumps
- `relu` - Rectified linear
- `abs`, `square`, `cube` - Non-linear transforms
- `identity`, `clamped`, `hat`, `inv`, `exp`

## API Usage

### Create Dual-CPPN Individual
```python
from cppn_engine import CPPNEngine, create_random_dual_genome

engine = CPPNEngine()
engine.create_population()

# Create random dual genome
dual_genome = create_random_dual_genome(engine, genome_id=0)

# Query the dual CPPN
r, g, b = engine.query_dual_cppn(
    dual_genome, 
    x=0.5, y=0.5, 
    raw_time=0.5, 
    mouse_speed=0.2,
    mouse_distance=0.3,
    inactivity=0.0
)
```

### Compile to Shader
```python
from shader_compiler import ShaderCompiler

compiler = ShaderCompiler()
shader_code = compiler.compile_dual_to_glsl(
    dual_genome, 
    engine.config, 
    engine.time_config
)
```

### Evolution Operations
```python
# Mutate a dual genome
child = engine.mutate_dual_genome(dual_genome, new_key=1)

# Crossover two dual genomes
offspring = engine.crossover_dual_genomes(parent1, parent2, new_key=2)
```

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
- NEAT config files ([neat_config.txt](neat_config.txt), [neat_config_time.txt](neat_config_time.txt)) must exist at repo root; they are in the repo already.

**Commands**

```bash
# From the repo root, with venv activated
pytest
```

To run a specific test file:

```bash
pytest test_visualization.py -v
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

**Basic demos (single CPPN)**

```bash
python main.py
```

**Evolution demo**

```bash
python evolution_demo.py
```

## Project layout

- **static/** – Frontend assets: HTML, CSS, and JavaScript (interactive viewer, debug overlay, population/community UI, pattern renderer). All browser-loaded files live here.
- **data/** – Runtime data: curated seeds (`seeds.json`) and community DB. Git tracks seeds; `community.db` is gitignored.
- **Root** – Backend and config: Python modules (`server.py`, `cppn_engine.py`, etc.), NEAT config files, `pyproject.toml`, Docker/deploy files (`Dockerfile`, `docker-compose.yml`, `railway.json`, `run.sh`). Entrypoint: `server:app`.

Generated content (saved patterns, network PDFs, frames) goes under `output/` (gitignored).

## Creating Videos

After generating animation frames:

```bash
# Using ffmpeg
ffmpeg -i output/frames/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4

# Create looping GIF
ffmpeg -i output/frames/frame_%03d.png -vf "fps=30,scale=512:-1:flags=lanczos" output.gif
```

## Requirements

- Python 3.9+
- neat-python >= 0.92
- numpy >= 1.24.0
- pillow >= 10.0.0
- flask >= 3.0.0
- flask-cors >= 4.0.0

## Future Work

- [x] Interactive web-based selection interface
- [x] Mouse speed reactivity
- [x] Dual-CPPN architecture (visual + time signal)
- [x] Mouse distance reactivity (per-pattern)
- [x] Activity signal (smoothed, speed-boosted engagement)
- [x] Signal enable/disable controls
- [x] Debug overlay for signal visualization
- [x] Right-click to remove clicks
- [ ] Direct video export (MP4/GIF)
- [ ] Multiple fitness functions for aesthetic properties
- [ ] 3D patterns (add z coordinate)
- [ ] Multi-resolution rendering
- [ ] Save/load evolution sessions
- [ ] Real-time shader editing
