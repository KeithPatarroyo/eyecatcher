# Eyecatcher

Time-varying CPPN (Compositional Pattern Producing Network) evolution system. Like Picbreeder, but patterns change over time.

## Features

- **CPPN Evolution**: Uses NEAT-Python to evolve neural networks that generate patterns
- **Time Dimension**: Patterns animate smoothly over time
- **Shader Compilation**: Convert CPPNs to GLSL shaders for GPU rendering
- **Mutation & Crossover**: Breed new patterns from existing ones

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run demos
python main.py
```

This will generate:
- Static patterns
- Animation frames
- GLSL shader code
- Mutation examples
- Crossover (breeding) examples

All outputs go to the `output/` folder.

## Core Components

### CPPN Engine (`cppn_engine.py`)
- Creates and evolves CPPNs
- Renders patterns as images
- Handles mutation and crossover
- Saves/loads genomes

### Shader Compiler (`shader_compiler.py`)
- Converts CPPN networks to GLSL code
- Enables real-time GPU rendering
- Exports shader bundles (JSON)

### Configuration (`neat_config.txt`)
- NEAT evolution parameters
- Network structure settings
- Mutation rates

## How It Works

1. **Input**: CPPN receives (x, y, distance, time, bias)
2. **Network**: Evolved neural network processes inputs
3. **Output**: RGB color values for that pixel at that time
4. **Animation**: Time changes → colors change → animation!

## CPPN Inputs (5)
- `x`: Horizontal position (-1 to 1)
- `y`: Vertical position (-1 to 1)  
- `distance`: Distance from center
- `time`: Animation time (-1 to 1)
- `bias`: Constant 1.0

## CPPN Outputs (3)
- `R`: Red channel (0-1)
- `G`: Green channel (0-1)
- `B`: Blue channel (0-1)

## Activation Functions

Available in the network:
- `sin`, `cos` - Periodic patterns
- `sigmoid`, `tanh` - Smooth gradients
- `gauss` - Gaussian bumps
- `relu` - Rectified linear
- `abs`, `square`, `cube` - Non-linear transforms

## Evolution Workflow

1. Generate random CPPNs
2. Render and evaluate patterns
3. Select favorites (manual or fitness function)
4. Breed new generation (mutation + crossover)
5. Repeat

## Usage Examples

### Run All Demos
```bash
python main.py
```

### Evolution Demo
```bash
python evolution_demo.py
```

### Test System
```bash
python test_basic.py
```

### View Shaders in Browser
1. Generate shaders: `python main.py` or `python evolution_demo.py`
2. Open `viewer.html` in a web browser
3. Click "Choose Shader File" and load from `output/` folder
4. Watch the pattern animate in real-time on GPU!

## API Usage

### Create and Render a Pattern
```python
from cppn_engine import CPPNEngine, create_random_genome
from PIL import Image

engine = CPPNEngine()
engine.create_population()

# Create random pattern
genome = create_random_genome(engine.config)

# Render at specific time
img = engine.render_image(genome, resolution=512, time=0.5)

# Save
Image.fromarray(img).save("pattern.png")
```

### Generate Animation
```python
frames = engine.render_animation_frames(
    genome, 
    resolution=256, 
    num_frames=60
)
```

### Compile to Shader
```python
from shader_compiler import ShaderCompiler

compiler = ShaderCompiler()
shader_code = compiler.compile_to_glsl(genome, engine.config)

with open("pattern.glsl", 'w') as f:
    f.write(shader_code)
```

### Evolution
```python
from evolution_demo import InteractiveEvolution

evo = InteractiveEvolution(population_size=16)
evo.initialize_population()

# Select best patterns
parents = evo.select_parents(num_parents=4)

# Create new generation
evo.breed_new_generation(parents)
```

## File Structure

```
eyecatcher/
├── cppn_engine.py          # Core CPPN engine
├── shader_compiler.py      # GLSL shader compiler
├── evolution_demo.py       # Evolution simulation
├── main.py                 # Basic demos
├── test_basic.py          # System tests
├── viewer.html            # WebGL shader viewer
├── neat_config.txt        # NEAT parameters
├── pyproject.toml         # Dependencies
└── output/                # Generated content
    ├── *.png              # Rendered images
    ├── *.glsl             # Shader code
    ├── *.json             # Shader bundles
    └── evolution/         # Evolution results
```

## Creating Videos

After generating animation frames:

```bash
# Using ffmpeg
ffmpeg -i output/frames/frame_%03d.png -c:v libx264 -pix_fmt yuv420p output.mp4

# Create looping GIF
ffmpeg -i output/frames/frame_%03d.png -vf "fps=30,scale=512:-1:flags=lanczos" output.gif
```

## Future Work

- [ ] Interactive web-based selection interface
- [ ] Direct video export (MP4/GIF)
- [ ] Multiple fitness functions for aesthetic properties
- [ ] 3D patterns (add z coordinate)
- [ ] Multi-resolution rendering
- [ ] Save/load evolution sessions
- [ ] Batch shader compilation
- [ ] Real-time shader editing
