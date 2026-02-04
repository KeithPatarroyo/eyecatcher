"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding.

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)
"""
import os
import random

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from cppn_engine import (
    CPPNEngine,
    DualGenome,
    copy_dual_genome,
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
)
from shader_compiler import ShaderCompiler
from stateless_api import stateless_bp, init_stateless_api, _shader_response_for_dual
from community_routes import community_bp

app = Flask(__name__)
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# CORS: allow all in dev, or set CORS_ORIGINS env for production
_cors_origins = os.environ.get("CORS_ORIGINS", "*")
if _cors_origins == "*":
    CORS(app)
else:
    CORS(app, origins=[o.strip() for o in _cors_origins.split(",")])

# Global state
engine = CPPNEngine()
engine.create_population()  # Initialize NEAT populations
compiler = ShaderCompiler()

current_population = []
current_generation = 0
genome_counter = 0

# Initialize and register API blueprints
_seeds_path = os.path.join(os.path.dirname(__file__), 'data', 'seeds.json')
init_stateless_api(engine, compiler, _seeds_path)
app.register_blueprint(stateless_bp)
app.register_blueprint(community_bp)


def create_population(size=12):
    """Create initial random population of dual genomes."""
    global current_population, genome_counter
    size = max(1, min(int(size), 50))
    current_population = []
    
    for i in range(size):
        dual_genome = create_random_dual_genome(engine, genome_id=genome_counter)
        genome_counter += 1
        current_population.append({
            'id': dual_genome.key,
            'genome': dual_genome,
            'fitness': 0,
            'clicks': 0
        })
    
    return current_population


def breed_next_generation(parents, population_size=12):
    """Breed new generation of dual genomes from selected parents."""
    global current_population, genome_counter
    
    new_population = []
    
    # Elitism: keep best parent (deep copy to avoid reference issues)
    best_parent = max(parents, key=lambda x: x['clicks'])
    elite = copy_dual_genome(best_parent['genome'], engine, best_parent['genome'].key)
    new_population.append({
        'id': elite.key,
        'genome': elite,
        'fitness': 0,
        'clicks': 0
    })
    
    # Generate offspring
    while len(new_population) < population_size:
        if len(parents) == 1:
            # Only one parent: mutate
            child = engine.mutate_dual_genome(parents[0]['genome'], genome_counter)
        else:
            # Multiple parents: 70% mutation, 30% crossover
            if random.random() < 0.7:
                parent = random.choice(parents)
                child = engine.mutate_dual_genome(parent['genome'], genome_counter)
            else:
                p1, p2 = random.sample(parents, 2)
                child = engine.crossover_dual_genomes(
                    p1['genome'], p2['genome'], genome_counter
                )
        
        genome_counter += 1
        
        new_population.append({
            'id': child.key,
            'genome': child,
            'fitness': 0,
            'clicks': 0
        })
    
    current_population = new_population
    return current_population


# Ensure initial population exists when app loads (e.g. under gunicorn)
if not current_population:
    create_population(12)


@app.route('/health')
def health():
    """Lightweight health check for Railway/deploy (no app state)."""
    return '', 200


@app.route('/')
def index():
    """Serve the viewer HTML."""
    return send_from_directory(APP_DIR, 'interactive_viewer.html')


@app.route('/debug.js')
def serve_debug_js():
    """Serve the debug module JavaScript."""
    return send_from_directory(APP_DIR, 'debug.js', mimetype='application/javascript')


@app.route('/debug.css')
def serve_debug_css():
    """Serve the debug module CSS."""
    return send_from_directory(APP_DIR, 'debug.css', mimetype='text/css')


@app.route('/storage.js')
def serve_storage_js():
    """Serve the IndexedDB storage module."""
    return send_from_directory(APP_DIR, 'storage.js', mimetype='application/javascript')


@app.route('/population_ui.js')
def serve_population_ui_js():
    """Serve the population UI module."""
    return send_from_directory(APP_DIR, 'population_ui.js', mimetype='application/javascript')


@app.route('/community.js')
def serve_community_js():
    """Serve the community UI module."""
    return send_from_directory(APP_DIR, 'community.js', mimetype='application/javascript')


@app.route('/community.css')
def serve_community_css():
    """Serve the community UI styles."""
    return send_from_directory(APP_DIR, 'community.css', mimetype='text/css')


@app.route('/viewer.css')
def serve_viewer_css():
    """Serve the interactive viewer main styles."""
    return send_from_directory(APP_DIR, 'viewer.css', mimetype='text/css')


@app.route('/pattern_renderer.js')
def serve_pattern_renderer_js():
    """Serve the pattern renderer WebGL module."""
    return send_from_directory(APP_DIR, 'pattern_renderer.js', mimetype='application/javascript')


@app.route('/api/init', methods=['POST'])
def init_population():
    """Initialize new population."""
    global current_generation
    data = request.json or {}
    size = data.get('size', 12)
    
    current_generation = 0
    create_population(size)
    
    return jsonify({
        'generation': current_generation,
        'population_size': len(current_population),
        'status': 'initialized'
    })


@app.route('/api/population', methods=['GET'])
def get_population():
    """Get current population as shaders. Optionally include genomes (for Submit to Community when load-balanced)."""
    include_genomes = request.args.get('include_genomes', '').lower() in ('1', 'true', 'yes')
    shaders = []
    genomes_out = [] if include_genomes else None

    for individual in current_population:
        dual_genome = individual['genome']

        # Compile dual CPPN to shader
        shader_code = compiler.compile_dual_to_glsl(
            dual_genome, engine.config, engine.time_config
        )

        # Count nodes and connections for both networks
        visual_nodes = len(dual_genome.visual.nodes)
        visual_conns = len([c for c in dual_genome.visual.connections.values() if c.enabled])
        time_nodes = len(dual_genome.time_signal.nodes)
        time_conns = len([c for c in dual_genome.time_signal.connections.values() if c.enabled])

        shaders.append({
            'id': individual['id'],
            'shader': shader_code,
            'clicks': individual['clicks'],
            'nodes': visual_nodes + time_nodes,
            'connections': visual_conns + time_conns,
            'visual_nodes': visual_nodes,
            'visual_connections': visual_conns,
            'time_nodes': time_nodes,
            'time_connections': time_conns
        })
        if include_genomes:
            genomes_out.append(dual_genome_to_json(dual_genome))

    out = {
        'generation': current_generation,
        'population': shaders
    }
    if genomes_out is not None:
        out['genomes'] = genomes_out
    return jsonify(out)


@app.route('/api/population/genomes', methods=['GET'])
def get_population_genomes():
    """Return current server population as genome JSON (for saving/export when client has no local genomes)."""
    genomes = []
    for ind in current_population:
        genomes.append(dual_genome_to_json(ind['genome']))
    return jsonify({
        'generation': current_generation,
        'genomes': genomes
    })


@app.route('/api/population/genome/<int:individual_id>', methods=['GET'])
def get_one_genome(individual_id):
    """Return one individual's genome as JSON (for Submit to Community from stateful session)."""
    for ind in current_population:
        if ind['id'] == individual_id:
            return jsonify({'genome': dual_genome_to_json(ind['genome'])})
    return jsonify({'error': 'Individual not found'}), 404


@app.route('/api/click', methods=['POST'])
def record_click():
    """Record a click (fitness) for an individual."""
    data = request.json
    individual_id = data.get('id')
    
    for individual in current_population:
        if individual['id'] == individual_id:
            individual['clicks'] += 1
            individual['fitness'] = individual['clicks']
            # Update fitness on the dual genome
            individual['genome'].fitness = individual['clicks']
            return jsonify({
                'id': individual_id,
                'clicks': individual['clicks'],
                'status': 'recorded'
            })
    
    return jsonify({'error': 'Individual not found'}), 404


@app.route('/api/unclick', methods=['POST'])
def remove_click():
    """Remove a click (decrease fitness) for an individual."""
    data = request.json
    individual_id = data.get('id')
    
    for individual in current_population:
        if individual['id'] == individual_id:
            if individual['clicks'] > 0:
                individual['clicks'] -= 1
                individual['fitness'] = individual['clicks']
                # Update fitness on the dual genome
                individual['genome'].fitness = individual['clicks']
            return jsonify({
                'id': individual_id,
                'clicks': individual['clicks'],
                'status': 'removed'
            })
    
    return jsonify({'error': 'Individual not found'}), 404


@app.route('/api/time-output', methods=['GET'])
def get_time_output():
    """
    Query the Time CPPN for a specific individual with given inputs.
    Used for debug sampling to show the actual time signal output.
    
    Query params:
        id: pattern ID
        time: raw animation time (0-1)
        mouseSpeed: mouse speed (0-1)
        mouseDist: distance from mouse to pattern (0-1)
        activity: activity level (0-1)
    """
    try:
        individual_id = int(request.args.get('id', -1))
        raw_time = float(request.args.get('time', 0))
        mouse_speed = float(request.args.get('mouseSpeed', 0))
        mouse_dist = float(request.args.get('mouseDist', 0))
        activity = float(request.args.get('activity', 0))
        
        # Find the individual
        for individual in current_population:
            if individual['id'] == individual_id:
                dual_genome = individual['genome']
                
                # Convert 0-1 inputs to -1 to 1 range (matching shader)
                raw_time_normalized = raw_time * 2.0 - 1.0
                mouse_speed_normalized = mouse_speed * 2.0 - 1.0
                mouse_dist_normalized = mouse_dist * 2.0 - 1.0
                activity_normalized = activity * 2.0 - 1.0
                
                # Query the time signal CPPN
                time_output = engine.query_time_signal(
                    dual_genome.time_signal,
                    raw_time_normalized,
                    mouse_speed_normalized,
                    mouse_dist_normalized,
                    activity_normalized
                )
                
                return jsonify({
                    'id': individual_id,
                    'timeOutput': time_output,
                    'inputs': {
                        'rawTime': raw_time,
                        'mouseSpeed': mouse_speed,
                        'mouseDist': mouse_dist,
                        'activity': activity
                    }
                })
        
        return jsonify({'error': 'Individual not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/breed', methods=['POST'])
def breed():
    """
    Breed next generation.
    - Stateless: Body has "parents" and optional "population_size" -> returns { "children": [genome JSONs] }.
    - Stateful: No "parents" in body -> use server-side population, update state, return generation info.
    """
    data = request.json or {}
    if 'parents' in data:
        return _breed_stateless(data)
    return _breed_stateful()


def _breed_stateful():
    """Stateful breed: use current_population, update server state."""
    global current_generation
    parents = [ind for ind in current_population if ind['clicks'] > 0]
    if not parents:
        return jsonify({'error': 'No individuals selected'}), 400
    parents.sort(key=lambda x: x['clicks'], reverse=True)
    num_parents = min(max(2, len(parents)), 4)
    selected_parents = parents[:num_parents]
    breed_next_generation(selected_parents)
    current_generation += 1
    return jsonify({
        'generation': current_generation,
        'parents_selected': num_parents,
        'parent_ids': [p['id'] for p in selected_parents],
        'parent_clicks': [p['clicks'] for p in selected_parents],
        'status': 'bred'
    })


def _breed_stateless(data):
    """Stateless breed: parents in body, return children as genome JSONs."""
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
        # Elitism: keep best parent (deep copy to avoid reference issues)
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
    Save a specific individual (dual genome).
    Supports both stateful mode (id only) and stateless mode (id + genome JSON).
    """
    data = request.json or {}
    individual_id = data.get('id')
    genome_json = data.get('genome')

    # Stateless mode: genome provided in request
    if genome_json:
        try:
            dual_genome = dual_genome_from_json(genome_json, engine)
            return _save_dual_genome(dual_genome, individual_id or dual_genome.key)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Stateful mode: look up genome in server population
    for individual in current_population:
        if individual['id'] == individual_id:
            return _save_dual_genome(individual['genome'], individual_id, visualize=True)

    return jsonify({'error': 'Individual not found (provide genome for stateless mode)'}), 404


def _save_dual_genome(dual_genome: DualGenome, individual_id: int, visualize: bool = False):
    """Internal helper to save a dual genome and return paths."""
    os.makedirs('output/saved', exist_ok=True)

    # Save dual genome (and optional network visualization PDF)
    genome_path = f'output/saved/dual_genome_{individual_id}.pkl'
    engine.save_dual_genome(dual_genome, genome_path, visualize=visualize)

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


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get evolution statistics."""
    total_clicks = sum(ind['clicks'] for ind in current_population)
    selected_count = len([ind for ind in current_population if ind['clicks'] > 0])
    
    return jsonify({
        'generation': current_generation,
        'population_size': len(current_population),
        'total_clicks': total_clicks,
        'selected_count': selected_count,
        'genome_counter': genome_counter,
        'dual_cppn': True  # Flag to indicate dual-CPPN mode
    })


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

    # Initialize first population
    create_population()

    app.run(debug=debug, port=port, host="0.0.0.0")
