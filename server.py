"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding (stateless API only).

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)

Population state lives on the client; server provides compile, random, seeds, breed, save.
Save returns file contents for client-side download (works on Railway / no server filesystem).
"""
import base64
import io
import json
import os
import pickle
import random
import zipfile

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from cppn_engine import CPPNEngine, DualGenome, dual_genome_from_json, dual_genome_to_json
from shader_compiler import ShaderCompiler
from stateless_api import stateless_bp, init_stateless_api
from community_routes import community_bp

app = Flask(__name__)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, 'static')

# CORS: allow all in dev, or set CORS_ORIGINS env for production
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
if _cors_origins == "*":
    CORS(app)
else:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(",")])

# Engine and compiler (no server-side population state)
engine = CPPNEngine()
engine.create_population()  # Initialize NEAT populations for mutation/crossover
compiler = ShaderCompiler()

# Initialize and register API blueprints
_seeds_path = os.path.join(os.path.dirname(__file__), 'data', 'seeds.json')
init_stateless_api(engine, compiler, _seeds_path)
app.register_blueprint(stateless_bp)
app.register_blueprint(community_bp)


@app.route('/health')
def health():
    """Lightweight health check for Railway/deploy (no app state)."""
    return '', 200


@app.route('/')
def index():
    """Serve the viewer HTML."""
    return send_from_directory(STATIC_DIR, 'interactive_viewer.html')


@app.route('/debug.js')
def serve_debug_js():
    """Serve the debug module JavaScript."""
    return send_from_directory(STATIC_DIR, 'debug.js', mimetype='application/javascript')


@app.route('/debug.css')
def serve_debug_css():
    """Serve the debug module CSS."""
    return send_from_directory(STATIC_DIR, 'debug.css', mimetype='text/css')


@app.route('/storage.js')
def serve_storage_js():
    """Serve the IndexedDB storage module."""
    return send_from_directory(STATIC_DIR, 'storage.js', mimetype='application/javascript')


@app.route('/population_ui.js')
def serve_population_ui_js():
    """Serve the population UI module."""
    return send_from_directory(STATIC_DIR, 'population_ui.js', mimetype='application/javascript')


@app.route('/community.js')
def serve_community_js():
    """Serve the community UI module."""
    return send_from_directory(STATIC_DIR, 'community.js', mimetype='application/javascript')


@app.route('/community.css')
def serve_community_css():
    """Serve the community UI styles."""
    return send_from_directory(STATIC_DIR, 'community.css', mimetype='text/css')


@app.route('/viewer.css')
def serve_viewer_css():
    """Serve the interactive viewer main styles."""
    return send_from_directory(STATIC_DIR, 'viewer.css', mimetype='text/css')


@app.route('/pattern_renderer.js')
def serve_pattern_renderer_js():
    """Serve the pattern renderer WebGL module."""
    return send_from_directory(STATIC_DIR, 'pattern_renderer.js', mimetype='application/javascript')


@app.route('/api/breed', methods=['POST'])
def breed():
    """
    Breed next generation (stateless).
    Body: {
        "parents": [...],
        "population_size": 12,  (optional, default 12)
        "elitism": false        (optional, default false; if true, best parent is copied unchanged)
    }
    Returns { "children": [genome JSONs] }.
    """
    data = request.json or {}
    if 'parents' not in data:
        return jsonify({'error': 'parents array required'}), 400
    return _breed_stateless(data)


def _breed_stateless(data):
    """Stateless breed: parents in body, return children as genome JSONs."""
    from cppn_engine import copy_dual_genome, dual_genome_to_json
    try:
        parents_data = data.get('parents', [])
        population_size = data.get('population_size', 12)
        elitism = data.get('elitism', False)
        if not parents_data:
            return jsonify({'error': 'parents array required'}), 400
        parents = []
        for p in parents_data:
            genome_data = p.get('genome', p)
            dual = dual_genome_from_json(genome_data, engine)
            dual.fitness = p.get('clicks', 0)
            parents.append({'genome': dual, 'clicks': p.get('clicks', 0)})
        if not parents:
            return jsonify({'error': 'No valid parents'}), 400
        max_key = max(p['genome'].key for p in parents)
        next_key = max_key + 1
        children = []
        # Elitism: optionally keep best parent unchanged
        if elitism:
            best = max(parents, key=lambda x: x['clicks'])
            elite = copy_dual_genome(best['genome'], engine, next_key)
            children.append(dual_genome_to_json(elite))
            next_key += 1
        while len(children) < population_size:
            if len(parents) == 1:
                child = engine.mutate_dual_genome(parents[0]['genome'], next_key)
            else:
                if random.random() < 0.7:
                    parent = random.choice(parents)
                    child = engine.mutate_dual_genome(parent['genome'], next_key)
                else:
                    p1, p2 = random.sample(parents, 2)
                    child = engine.crossover_dual_genomes(
                        p1['genome'], p2['genome'], next_key
                    )
            children.append(dual_genome_to_json(child))
            next_key += 1
        return jsonify({'children': children})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save', methods=['POST'])
def save_individual():
    """
    Save a dual genome (stateless).
    Body: {
        "genome": { ... },       (required)
        "id": 123,               (optional, defaults to genome.key)
        "visualize": true        (optional, default true; generate network PDF)
    }
    """
    data = request.json or {}
    genome_json = data.get('genome')
    individual_id = data.get('id')
    visualize = data.get('visualize', True)
    if not genome_json:
        return jsonify({'error': 'genome required in request body'}), 400
    try:
        dual_genome = dual_genome_from_json(genome_json, engine)
        return _save_dual_genome(dual_genome, individual_id or dual_genome.key, visualize=visualize)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_network_data(genome, network_type, config):
    """Extract nodes and connections from a genome."""
    nodes = []
    node_id_map = {}
    
    num_inputs = config.genome_config.num_inputs
    num_outputs = config.genome_config.num_outputs
    
    # X-offset to separate visual and time networks horizontally
    x_offset = 1000 if network_type == 'time' else 0
    
    # Define input labels to match actual CPPN query inputs
    # Visual CPPN inputs: x, y, distance, time, mouse_speed, mouse_distance, inactivity, bias
    # Time Signal CPPN inputs: raw_time, mouse_speed, mouse_distance, inactivity, bias
    if network_type == 'time':
        input_labels = ['raw_time', 'mouse_speed', 'mouse_distance', 'inactivity', 'bias']
    else:
        input_labels = ['x', 'y', 'distance', 'time', 'mouse_speed', 'mouse_distance', 'inactivity', 'bias']
    
    # Add input nodes - position on left
    for i in range(num_inputs):
        neat_id = -(i + 1)
        vis_id = f'{network_type}_input_{neat_id}'
        node_id_map[neat_id] = vis_id
        label = input_labels[i] if i < len(input_labels) else f'Input {i}'
        nodes.append({
            'id': vis_id,
            'label': label,
            'type': 'input',
            'network': network_type,
            'index': i,
            'x': -400 + x_offset,
            'y': (i - num_inputs/2) * 80
        })
    
    # Add hidden nodes - position in middle
    hidden_list = sorted(genome.nodes.keys())
    for idx, neat_id in enumerate(hidden_list):
        node = genome.nodes[neat_id]
        vis_id = f'{network_type}_hidden_{neat_id}'
        node_id_map[neat_id] = vis_id
        nodes.append({
            'id': vis_id,
            'label': f'Node {neat_id}',
            'type': 'hidden',
            'network': network_type,
            'activation': node.activation,
            'bias': float(node.bias),
            'index': neat_id,
            'x': 0 + x_offset,
            'y': (idx - len(hidden_list)/2) * 80
        })
    
    # Add output nodes - position on right
    if network_type == 'time':
        output_labels = ['output']
    else:
        output_labels = ['red', 'green', 'blue']
    
    for i in range(num_outputs):
        neat_id = i
        vis_id = f'{network_type}_output_{neat_id}'
        node_id_map[neat_id] = vis_id
        label = output_labels[i] if i < len(output_labels) else f'Output {i}'
        nodes.append({
            'id': vis_id,
            'label': label,
            'type': 'output',
            'network': network_type,
            'index': i,
            'x': 400 + x_offset,
            'y': (i - num_outputs/2) * 80
        })
    
    # Extract connections
    connections = []
    for conn_id, conn in genome.connections.items():
        if conn.enabled:
            input_node, output_node = conn_id
            source_id = node_id_map.get(input_node, str(input_node))
            target_id = node_id_map.get(output_node, str(output_node))
            connections.append({
                'source': source_id,
                'target': target_id,
                'weight': float(conn.weight),
                'network': network_type
            })
    
    return nodes, connections

# NOTE: Old stateful endpoints below are deprecated - using stateless API now
# The stateless versions are in stateless_api.py (POST /api/network, etc.)

# @app.route('/api/network/<int:individual_id>', methods=['GET'])
# def get_network_data(individual_id):
#     """DEPRECATED: Get both CPPN networks (visual and time signal) for visualization."""
#     # This endpoint required current_population which doesn't exist in stateless mode
#     # Use POST /api/network with genome in body instead
#     return jsonify({'error': 'This endpoint is deprecated. Use POST /api/network with genome data.'}), 410

# @app.route('/api/adjust-weight', methods=['POST'])
# def adjust_weight():
#     """DEPRECATED: Adjust a connection weight in a network and return updated shader."""
#     # This endpoint required current_population which doesn't exist in stateless mode
#     return jsonify({'error': 'This endpoint is deprecated.'}), 410


def _save_dual_genome(dual_genome: DualGenome, individual_id: int, visualize: bool = True):
    """
    Build save assets in memory and return them for client-side download.
    Works on Railway (no server filesystem). Optionally write to disk if SAVE_TO_DISK=1.
    """
    shader_code = compiler.compile_dual_to_glsl(
        dual_genome, engine.config, engine.time_config
    )
    bundle = {
        "shader": shader_code,
        "metadata": {
            "type": "dual_cppn",
            "visual": {
                "num_nodes": len(dual_genome.visual.nodes),
                "num_connections": len([c for c in dual_genome.visual.connections.values() if c.enabled]),
            },
            "time_signal": {
                "num_nodes": len(dual_genome.time_signal.nodes),
                "num_connections": len([c for c in dual_genome.time_signal.connections.values() if c.enabled]),
            },
            "fitness": dual_genome.fitness,
        },
    }
    bundle_json = json.dumps(bundle, indent=2)
    genome_json = json.dumps(dual_genome_to_json(dual_genome), indent=2)

    # PNG image
    from PIL import Image
    img = engine.render_image(dual_genome.visual, resolution=512, time=0.5)
    img_buffer = io.BytesIO()
    Image.fromarray(img).save(img_buffer, format="PNG")
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode("ascii")

    # Pickle genome
    pkl_buffer = io.BytesIO()
    pickle.dump(
        {"visual": dual_genome.visual, "time_signal": dual_genome.time_signal, "key": dual_genome.key},
        pkl_buffer,
    )
    pkl_base64 = base64.b64encode(pkl_buffer.getvalue()).decode("ascii")

    # Optional: network PDF
    pdf_bytes = None
    if visualize:
        try:
            from genome_visualizer import GenomeVisualizer
            visualizer = GenomeVisualizer(engine.config)
            pdf_buffer = io.BytesIO()
            visualizer.visualize_genome(dual_genome.visual, pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()
        except Exception as e:
            print(f"Warning: Genome visualization failed: {e}")

    # Package all assets into a single zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"pattern_{individual_id}.png", base64.b64decode(img_base64))
        zf.writestr(f"pattern_{individual_id}.glsl", shader_code.encode("utf-8"))
        zf.writestr(f"pattern_{individual_id}_bundle.json", bundle_json.encode("utf-8"))
        zf.writestr(f"genome_{individual_id}.json", genome_json.encode("utf-8"))
        zf.writestr(f"dual_genome_{individual_id}.pkl", base64.b64decode(pkl_base64))
        if pdf_bytes:
            zf.writestr(f"dual_genome_{individual_id}_network.pdf", pdf_bytes)
    zip_base64 = base64.b64encode(zip_buffer.getvalue()).decode("ascii")

    downloads = [
        {"filename": f"pattern_{individual_id}.zip", "mime": "application/zip", "content_base64": zip_base64},
    ]

    # Optional: write to disk for local dev (e.g. SAVE_TO_DISK=1)
    if os.environ.get("SAVE_TO_DISK", "").strip() in ("1", "true", "yes"):
        os.makedirs("output/saved", exist_ok=True)
        with open(f"output/saved/pattern_{individual_id}.png", "wb") as f:
            f.write(base64.b64decode(img_base64))
        with open(f"output/saved/pattern_{individual_id}.glsl", "w") as f:
            f.write(shader_code)
        with open(f"output/saved/pattern_{individual_id}_bundle.json", "w") as f:
            f.write(bundle_json)
        with open(f"output/saved/genome_{individual_id}.json", "w") as f:
            f.write(genome_json)
        with open(f"output/saved/dual_genome_{individual_id}.pkl", "wb") as f:
            f.write(base64.b64decode(pkl_base64))
        if pdf_bytes:
            with open(f"output/saved/dual_genome_{individual_id}_network.pdf", "wb") as f:
                f.write(pdf_bytes)

    return jsonify({
        "id": individual_id,
        "status": "saved",
        "downloads": downloads,
    })


@app.route('/api/saved/<int:individual_id>/network')
def serve_saved_network(individual_id):
    """Serve the network visualization PDF for a saved pattern (from genome visualizer)."""
    path = os.path.join(APP_DIR, 'output', 'saved', f'dual_genome_{individual_id}_network.pdf')
    if not os.path.isfile(path):
        return jsonify({'error': 'Network visualization not found'}), 404
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype='application/pdf',
        as_attachment=False
    )


@app.route('/api/saved/<int:individual_id>/image')
def serve_saved_image(individual_id):
    """Serve the rendered PNG for a saved pattern."""
    path = os.path.join(APP_DIR, 'output', 'saved', f'pattern_{individual_id}.png')
    if not os.path.isfile(path):
        return jsonify({'error': 'Image not found'}), 404
    return send_from_directory(
        os.path.dirname(path),
        os.path.basename(path),
        mimetype='image/png',
        as_attachment=False
    )


if __name__ == '__main__':
    print("=" * 60)
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"

    print("EYECATCHER - Interactive Evolution Server")
    print("Dual-CPPN Mode: Visual + Time Signal Networks")
    print("=" * 60)
    print("\nStarting server...")
    print(f"Open http://localhost:{port} in your browser")
    print("\nPress Ctrl+C to stop")
    print("=" * 60)

    app.run(debug=debug, port=port, host="0.0.0.0")
