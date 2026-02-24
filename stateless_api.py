"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state:
- /api/compile: Compile genome JSON to GLSL shaders
- /api/random: Generate random population as genome JSON
- /api/open-endedness: Compute open-endedness score for a genome
"""
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


def init_stateless_api(engine: CPPNEngine, compiler: ShaderCompiler):
    """
    Initialize the stateless API with engine and compiler references.
    Call this before registering the blueprint with the app.
    """
    global _engine, _compiler
    _engine = engine
    _compiler = compiler


def _shader_response_for_dual(dual_genome: DualGenome, individual_id: int, clicks: int = 0, compiler=None):
    """Build a single shader response dict for a dual genome. Uses compiler or _compiler."""
    comp = compiler if compiler is not None else _compiler
    shader_code = comp.compile_dual_to_glsl(
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
    Body: { "genomes": [ ... ], "color_mode": "hsv"|"rgb" (optional, default from server) }
    Returns: { "shaders": [ { "id", "shader", "clicks", "nodes", ... }, ... ] }
    """
    try:
        data = request.json or {}
        genomes_data = data.get('genomes', [])
        if not genomes_data:
            return jsonify({'error': 'genomes array required'}), 400
        color_mode = (data.get('color_mode') or '').strip().lower()
        if color_mode and color_mode not in ('hsv', 'rgb'):
            color_mode = 'hsv'
        compiler = _compiler if (not color_mode or color_mode == _compiler.color_mode) else ShaderCompiler(color_mode=color_mode)
        shaders = []
        for i, g_data in enumerate(genomes_data):
            dual = dual_genome_from_json(g_data, _engine)
            individual_id = g_data.get('key', dual.key if dual else i)
            clicks = g_data.get('clicks', 0)
            shaders.append(_shader_response_for_dual(dual, individual_id, clicks, compiler=compiler))
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
        "resolution": 64  // optional, default 64
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


@stateless_bp.route('/api/open-endedness/from-frames', methods=['POST'])
def api_open_endedness_from_frames():
    """
    Compute open-endedness scores from pre-rendered frames (captured from WebGL).

    Body: {
        "patterns": [
            { "genome_key": int, "frames": [base64_rgb, ...], "width": int, "height": int },
            ...
        ],
        "num_frames": 16,
        "generation": 0
    }
    Returns: {
        "scores": [ { "genome_key": int, "score": float }, ... ],
        "available": true
    }
    """
    import os
    import base64
    from PIL import Image
    import numpy as np

    # Target resolution for CLIP (will resize if needed)
    TARGET_RESOLUTION = 64

    try:
        if not _init_open_endedness():
            return jsonify({
                'error': 'Open-endedness scoring not available',
                'available': False
            }), 503

        data = request.json or {}
        patterns_data = data.get('patterns', [])
        if not patterns_data:
            return jsonify({'error': 'patterns array required'}), 400

        num_frames = int(data.get('num_frames', 16))
        generation = int(data.get('generation', 0))

        from asal_metrics import calc_open_endedness_score

        # Create output directory for this generation
        output_base = os.path.join(os.path.dirname(__file__), 'oe_frames')
        gen_dir = os.path.join(output_base, f'generation{generation}')
        os.makedirs(gen_dir, exist_ok=True)

        total = len(patterns_data)
        print(f"\n{'='*60}")
        print(f"Computing OE Scores from WebGL-captured frames")
        print(f"Patterns: {total}, Frames: {num_frames}, Target: {TARGET_RESOLUTION}x{TARGET_RESOLUTION}")
        print(f"Saving frames to: {gen_dir}")
        print(f"{'='*60}")

        results = []
        for i, p_data in enumerate(patterns_data):
            genome_key = p_data.get('genome_key', i)
            frames_b64 = p_data.get('frames', [])
            width = p_data.get('width', TARGET_RESOLUTION)
            height = p_data.get('height', TARGET_RESOLUTION)

            if not frames_b64 or len(frames_b64) == 0:
                print(f"[{i+1}/{total}] Pattern {genome_key}: No frames provided, skipping")
                results.append({'genome_key': genome_key, 'score': None})
                continue

            # Decode frames from base64
            frames = []
            pattern_dir = os.path.join(gen_dir, f'pattern{genome_key}')
            os.makedirs(pattern_dir, exist_ok=True)

            for frame_idx, frame_b64 in enumerate(frames_b64):
                # Decode base64 RGB data
                rgb_bytes = base64.b64decode(frame_b64)
                rgb_array = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape(height, width, 3)

                # Resize to target resolution if needed
                img = Image.fromarray(rgb_array)
                if width != TARGET_RESOLUTION or height != TARGET_RESOLUTION:
                    img = img.resize((TARGET_RESOLUTION, TARGET_RESOLUTION), Image.LANCZOS)
                    rgb_array = np.array(img)

                frames.append(rgb_array)

                # Save frame as PNG (at target resolution)
                img_to_save = Image.fromarray(rgb_array)
                img_to_save.save(os.path.join(pattern_dir, f'frame_{frame_idx:02d}.png'))

            frames = np.array(frames)  # Shape: (T, H, W, C)

            # Compute CLIP embeddings for all frames (CLIPEmbedder handles normalization)
            frame_list = [frames[t] for t in range(frames.shape[0])]
            embeddings = _clip_embedder.embed_images(frame_list)  # Shape: (T, D)

            # Compute open-endedness score
            score = float(calc_open_endedness_score(embeddings))

            results.append({
                'genome_key': genome_key,
                'score': score
            })

            print(f"[{i+1}/{total}] Pattern {genome_key}: OE score = {score:.4f} (frames saved)")

        print(f"{'='*60}")
        valid_scores = [r['score'] for r in results if r['score'] is not None]
        if valid_scores:
            print(f"Completed! Scores range: {min(valid_scores):.4f} - {max(valid_scores):.4f}")
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


@stateless_bp.route('/api/network', methods=['POST'])
def api_network():
    """
    Stateless: get network visualization data for a genome.
    Body: { "genome": { "key", "visual", "time_signal" } }
    Returns: { "id": key, "nodes": [...], "connections": [...] }
    """
    try:
        data = request.json or {}
        genome_data = data.get('genome')
        if not genome_data:
            return jsonify({'error': 'genome required'}), 400

        dual = dual_genome_from_json(genome_data, _engine)
        individual_id = genome_data.get('key', dual.key if dual else 0)

        all_nodes = []
        all_connections = []

        # Extract visual network
        if dual.visual:
            from server import extract_network_data
            visual_nodes, visual_conns = extract_network_data(dual.visual, 'visual', _engine.config)
            all_nodes.extend(visual_nodes)
            all_connections.extend(visual_conns)

        # Extract time signal network
        if dual.time_signal:
            from server import extract_network_data
            time_nodes, time_conns = extract_network_data(dual.time_signal, 'time', _engine.time_config)
            all_nodes.extend(time_nodes)
            all_connections.extend(time_conns)

        return jsonify({
            'id': individual_id,
            'nodes': all_nodes,
            'connections': all_connections,
            'status': 'success'
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stateless_bp.route('/api/adjust-weight', methods=['POST'])
def api_adjust_weight():
    """
    Stateless: adjust a connection weight in a genome and return updated shader.
    Body: {
        "genome": { "key", "visual", "time_signal" },
        "network": "visual" or "time",
        "source": source_node_id (string like "visual_input_-1"),
        "target": target_node_id (string like "visual_hidden_5"),
        "weight": new_weight_value (float)
    }
    Returns: { "status": "success", "shader": "...", "genome": {...} }
    """
    try:
        data = request.json or {}
        genome_data = data.get('genome')
        if not genome_data:
            return jsonify({'error': 'genome required'}), 400

        network_type = data.get('network')  # 'visual' or 'time'
        source_node = data.get('source')
        target_node = data.get('target')
        new_weight = float(data.get('weight', 0))

        # Parse the genome
        dual = dual_genome_from_json(genome_data, _engine)

        # Select the appropriate network
        if network_type == 'visual':
            genome = dual.visual
            config = _engine.config
        elif network_type == 'time':
            genome = dual.time_signal
            config = _engine.time_config
        else:
            return jsonify({'error': f'Unknown network type: {network_type}'}), 400

        # Convert node IDs from strings to integers
        # Frontend sends IDs like "visual_input_-1" or "time_hidden_5"
        def extract_node_id(node_id_str):
            parts = node_id_str.split('_')
            if len(parts) >= 3:
                return int(parts[-1])  # Last part is the numeric ID
            return int(node_id_str)

        try:
            source_id = extract_node_id(source_node)
            target_id = extract_node_id(target_node)
        except (ValueError, IndexError) as e:
            return jsonify({
                'error': f'Invalid node ID format: {source_node} or {target_node}'
            }), 400

        # Update the weight in the connection
        conn_key = (source_id, target_id)
        if conn_key in genome.connections:
            genome.connections[conn_key].weight = new_weight

            # Recompile shader with updated weights
            shader_code = _compiler.compile_dual_to_glsl(
                dual, _engine.config, _engine.time_config
            )

            # Return updated genome as JSON so client can update its state
            from genome_serialization import dual_genome_to_json
            updated_genome = dual_genome_to_json(dual)

            return jsonify({
                'status': 'success',
                'shader': shader_code,
                'genome': updated_genome,
                'network': network_type,
                'source': source_node,
                'target': target_node,
                'weight': new_weight
            })
        else:
            return jsonify({
                'error': f'Connection not found: {conn_key} (from {source_node} -> {target_node})'
            }), 404

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
