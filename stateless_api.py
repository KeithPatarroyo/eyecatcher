"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state:
- /api/compile: Compile genome JSON to GLSL shaders
- /api/random: Generate random population as genome JSON
- /api/seeds: Return curated seed patterns
- /api/open-endedness: Compute open-endedness score for a genome
"""
import json
import os
from flask import Blueprint, jsonify, request

from cppn_engine import CPPNEngine, DualGenome, create_random_dual_genome
from genome_serialization import dual_genome_from_json, dual_genome_to_json
from shader_compiler import ShaderCompiler

# Optional imports for open-endedness scoring
_clip_embedder = None
_open_endedness_available = False

def _init_open_endedness():
    """Try to initialize CLIP embedder for open-endedness scoring."""
    global _clip_embedder, _open_endedness_available
    if _clip_embedder is not None:
        return _open_endedness_available
    try:
        from foundation_models.clip import CLIPEmbedder
        _clip_embedder = CLIPEmbedder()
        _open_endedness_available = True
    except ImportError:
        _open_endedness_available = False
    return _open_endedness_available


# Create blueprint
stateless_bp = Blueprint('stateless', __name__)

# Module-level references (set by init_stateless_api)
_engine: CPPNEngine = None
_compiler: ShaderCompiler = None
_curated_seeds: list = []


def init_stateless_api(engine: CPPNEngine, compiler: ShaderCompiler, seeds_path: str = None):
    """
    Initialize the stateless API with engine and compiler references.
    Call this before registering the blueprint with the app.
    """
    global _engine, _compiler, _curated_seeds
    _engine = engine
    _compiler = compiler
    
    # Load curated seeds
    if seeds_path and os.path.isfile(seeds_path):
        try:
            with open(seeds_path, 'r') as f:
                data = json.load(f)
                _curated_seeds = data.get('seeds', [])
        except Exception:
            _curated_seeds = []


def _shader_response_for_dual(dual_genome: DualGenome, individual_id: int, clicks: int = 0):
    """Build a single shader response dict for a dual genome."""
    shader_code = _compiler.compile_dual_to_glsl(
        dual_genome, _engine.config, _engine.time_config
    )
    v_nodes = len(dual_genome.visual.nodes)
    v_conns = len([c for c in dual_genome.visual.connections.values() if c.enabled])
    t_nodes = len(dual_genome.time_signal.nodes)
    t_conns = len([c for c in dual_genome.time_signal.connections.values() if c.enabled])
    return {
        'id': individual_id,
        'shader': shader_code,
        'clicks': clicks,
        'nodes': v_nodes + t_nodes,
        'connections': v_conns + t_conns,
        'visual_nodes': v_nodes,
        'visual_connections': v_conns,
        'time_nodes': t_nodes,
        'time_connections': t_conns,
    }


@stateless_bp.route('/api/compile', methods=['POST'])
def api_compile():
    """
    Stateless: compile a list of dual genomes to shaders.
    Body: { "genomes": [ { "key", "visual", "time_signal" }, ... ] }
    Returns: { "shaders": [ { "id", "shader", "clicks", "nodes", ... }, ... ] }
    """
    try:
        data = request.json or {}
        genomes_data = data.get('genomes', [])
        if not genomes_data:
            return jsonify({'error': 'genomes array required'}), 400
        shaders = []
        for i, g_data in enumerate(genomes_data):
            dual = dual_genome_from_json(g_data, _engine)
            individual_id = g_data.get('key', dual.key if dual else i)
            clicks = g_data.get('clicks', 0)
            shaders.append(_shader_response_for_dual(dual, individual_id, clicks))
        return jsonify({'shaders': shaders})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/random', methods=['POST'])
def api_random():
    """
    Stateless: create a new random population.
    Body: { "size": 12 }
    Returns: { "genomes": [ { "key", "visual", "time_signal" }, ... ] }
    """
    try:
        data = request.json or {}
        size = data.get('size', 12)
        size = max(1, min(int(size), 50))
        genomes = []
        for i in range(size):
            dual = create_random_dual_genome(_engine, genome_id=i)
            genomes.append(dual_genome_to_json(dual))
        return jsonify({'genomes': genomes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/seeds', methods=['GET'])
def api_seeds():
    """Return curated seed genomes (from data/seeds.json)."""
    return jsonify({'seeds': _curated_seeds})


@stateless_bp.route('/api/time-output', methods=['POST'])
def api_time_output():
    """
    Stateless: query the Time CPPN for a genome with given inputs (for debug panel).
    Body: { "genome": { "key", "visual", "time_signal" }, "time", "mouseSpeed", "mouseDist", "activity" } (0-1).
    Returns: { "timeOutput": float, "inputs": { ... } }.
    """
    try:
        data = request.json or {}
        genome_data = data.get('genome')
        if not genome_data:
            return jsonify({'error': 'genome required'}), 400
        raw_time = float(data.get('time', 0))
        mouse_speed = float(data.get('mouseSpeed', 0))
        mouse_dist = float(data.get('mouseDist', 0))
        activity = float(data.get('activity', 0))
        dual = dual_genome_from_json(genome_data, _engine)
        raw_time_n = raw_time * 2.0 - 1.0
        mouse_speed_n = mouse_speed * 2.0 - 1.0
        mouse_dist_n = mouse_dist * 2.0 - 1.0
        activity_n = activity * 2.0 - 1.0
        time_output = _engine.query_time_signal(
            dual.time_signal, raw_time_n, mouse_speed_n, mouse_dist_n, activity_n
        )
        return jsonify({
            'timeOutput': time_output,
            'inputs': {
                'rawTime': raw_time,
                'mouseSpeed': mouse_speed,
                'mouseDist': mouse_dist,
                'activity': activity
            }
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/open-endedness', methods=['POST'])
def api_open_endedness():
    """
    Compute open-endedness score for a genome's animation.

    The score measures temporal diversity - how much the pattern changes over time.
    Lower scores indicate more diverse/interesting animations.

    Body: {
        "genome": { "key", "visual", "time_signal" },
        "num_frames": 16,  // optional, default 16
        "resolution": 224  // optional, default 224
    }
    Returns: {
        "score": float,  // open-endedness score (lower = more interesting)
        "available": true,
        "genome_key": int
    }
    """
    try:
        # Check if open-endedness scoring is available
        if not _init_open_endedness():
            return jsonify({
                'error': 'Open-endedness scoring not available. Install: pip install jax flax transformers einops',
                'available': False
            }), 503

        data = request.json or {}
        genome_data = data.get('genome')
        if not genome_data:
            return jsonify({'error': 'genome required'}), 400

        num_frames = int(data.get('num_frames', 16))
        resolution = int(data.get('resolution', 64))

        # Parse genome
        dual = dual_genome_from_json(genome_data, _engine)
        genome_key = genome_data.get('key', dual.key if dual else 0)

        # Import required modules
        from rollout import render_video_rollout, compute_video_embeddings
        from asal_metrics import calc_open_endedness_score

        # Render video frames
        frames = render_video_rollout(
            _engine,
            dual,
            num_frames=num_frames,
            resolution=resolution,
            time_range=(0.0, 1.0),
        )

        # Compute embeddings
        embeddings = compute_video_embeddings(frames, _clip_embedder)

        # Compute open-endedness score
        score = calc_open_endedness_score(embeddings)
        score = float(score)  # Convert from JAX scalar

        return jsonify({
            'score': score,
            'available': True,
            'genome_key': genome_key,
            'num_frames': num_frames
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/open-endedness/batch', methods=['POST'])
def api_open_endedness_batch():
    """
    Compute open-endedness scores for multiple genomes.

    Body: {
        "genomes": [ { "key", "visual", "time_signal" }, ... ],
        "num_frames": 16,
        "resolution": 64,
        "generation": 0  // optional, for saving frames
    }
    Returns: {
        "scores": [ { "genome_key": int, "score": float }, ... ],
        "available": true
    }
    """
    import os
    from PIL import Image
    import numpy as np

    try:
        if not _init_open_endedness():
            return jsonify({
                'error': 'Open-endedness scoring not available',
                'available': False
            }), 503

        data = request.json or {}
        genomes_data = data.get('genomes', [])
        if not genomes_data:
            return jsonify({'error': 'genomes array required'}), 400

        num_frames = int(data.get('num_frames', 16))
        resolution = int(data.get('resolution', 64))
        generation = int(data.get('generation', 0))

        from rollout import render_video_rollout, compute_video_embeddings
        from asal_metrics import calc_open_endedness_score

        # Create output directory for this generation
        output_base = os.path.join(os.path.dirname(__file__), 'oe_frames')
        gen_dir = os.path.join(output_base, f'generation{generation}')
        os.makedirs(gen_dir, exist_ok=True)

        total = len(genomes_data)
        print(f"\n{'='*60}")
        print(f"Computing Open-Endedness Scores for {total} patterns")
        print(f"Resolution: {resolution}x{resolution}, Frames: {num_frames}")
        print(f"Saving frames to: {gen_dir}")
        print(f"{'='*60}")

        results = []
        for i, g_data in enumerate(genomes_data):
            dual = dual_genome_from_json(g_data, _engine)
            genome_key = g_data.get('key', dual.key if dual else 0)

            frames = render_video_rollout(
                _engine, dual,
                num_frames=num_frames,
                resolution=resolution,
                time_range=(0.0, 1.0),
            )

            # Save frames for this pattern
            pattern_dir = os.path.join(gen_dir, f'pattern{genome_key}')
            os.makedirs(pattern_dir, exist_ok=True)
            for frame_idx, frame in enumerate(frames):
                img = Image.fromarray(frame.astype(np.uint8))
                img.save(os.path.join(pattern_dir, f'frame_{frame_idx:02d}.png'))

            embeddings = compute_video_embeddings(frames, _clip_embedder)
            score = float(calc_open_endedness_score(embeddings))

            results.append({
                'genome_key': genome_key,
                'score': score
            })

            # Progress logging
            print(f"[{i+1}/{total}] Pattern {genome_key}: OE score = {score:.4f} (frames saved)")

        print(f"{'='*60}")
        print(f"Completed! Scores range: {min(r['score'] for r in results):.4f} - {max(r['score'] for r in results):.4f}")
        print(f"Frames saved to: {gen_dir}")
        print(f"{'='*60}\n")

        return jsonify({
            'scores': results,
            'available': True,
            'frames_dir': gen_dir
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/open-endedness/status', methods=['GET'])
def api_open_endedness_status():
    """Check if open-endedness scoring is available."""
    available = _init_open_endedness()
    return jsonify({'available': available})
