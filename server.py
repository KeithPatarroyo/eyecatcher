"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding (stateless API only).

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)

Population state lives on the client; server provides compile, random, seeds, breed, save.
"""
import os
import random

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from cppn_engine import CPPNEngine, DualGenome, dual_genome_from_json
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
    Breed next generation (stateless). Body: "parents" array and optional "population_size".
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
    Save a dual genome (stateless). Body must include "genome" JSON; "id" optional.
    """
    data = request.json or {}
    genome_json = data.get('genome')
    individual_id = data.get('id')
    if not genome_json:
        return jsonify({'error': 'genome required in request body'}), 400
    try:
        dual_genome = dual_genome_from_json(genome_json, engine)
        return _save_dual_genome(dual_genome, individual_id or dual_genome.key)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _save_dual_genome(dual_genome: DualGenome, individual_id: int):
    """Internal helper to save a dual genome and return paths."""
    os.makedirs('output/saved', exist_ok=True)

    # Save dual genome (and optional network visualization PDF)
    genome_path = f'output/saved/dual_genome_{individual_id}.pkl'
    engine.save_dual_genome(dual_genome, genome_path, visualize=False)

    network_path = f'output/saved/dual_genome_{individual_id}_network.pdf'
    has_network = os.path.isfile(network_path)

    # Save shader
    shader_code = compiler.compile_dual_to_glsl(
        dual_genome, engine.config, engine.time_config
    )
    shader_path = f'output/saved/pattern_{individual_id}.glsl'
    with open(shader_path, 'w') as f:
        f.write(shader_code)

    # Save shader bundle
    bundle_path = f'output/saved/pattern_{individual_id}_bundle.json'
    compiler.export_dual_shader_bundle(
        dual_genome, engine.config, engine.time_config, bundle_path
    )

    # Save image (using visual CPPN with linear time for static image)
    from PIL import Image
    img = engine.render_image(dual_genome.visual, resolution=512, time=0.5)
    img_path = f'output/saved/pattern_{individual_id}.png'
    Image.fromarray(img).save(img_path)

    out = {
        'id': individual_id,
        'genome_path': genome_path,
        'shader_path': shader_path,
        'bundle_path': bundle_path,
        'image_path': img_path,
        'status': 'saved'
    }
    if has_network:
        out['network_path'] = network_path
    return jsonify(out)


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
