"""
Interactive Evolution Server
Serves dual-CPPN population and handles breeding.

Each individual has two CPPNs:
- Visual CPPN: (x, y, dist, time, mouseSpeed, bias) -> (R, G, B)
- Time Signal CPPN: (rawTime, mouseSpeed, bias) -> (modifiedTime)
"""
import json
import os
import random
import sqlite3
from datetime import datetime

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

# Curated seeds (loaded once at startup)
_seeds_path = os.path.join(os.path.dirname(__file__), 'data', 'seeds.json')
_curated_seeds = []
if os.path.isfile(_seeds_path):
    try:
        with open(_seeds_path, 'r') as f:
            data = json.load(f)
            _curated_seeds = data.get('seeds', [])
    except Exception:
        pass

# Community submissions DB
DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'data', 'community.db'))


def _get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_community_db():
    conn = _get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            creator TEXT,
            genome_json TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP,
            approved_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


_init_community_db()


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
    """Get current population as shaders."""
    shaders = []
    
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
    
    return jsonify({
        'generation': current_generation,
        'population': shaders
    })


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

    # Save dual genome
    genome_path = f'output/saved/dual_genome_{individual_id}.pkl'
    engine.save_dual_genome(dual_genome, genome_path, visualize=visualize)

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

    return jsonify({
        'id': individual_id,
        'genome_path': genome_path,
        'shader_path': shader_path,
        'bundle_path': bundle_path,
        'image_path': img_path,
        'status': 'saved'
    })


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


# ---------------------------------------------------------------------------
# Stateless API (client holds population; server compiles/breeds/randomizes)
# ---------------------------------------------------------------------------


def _shader_response_for_dual(dual_genome: DualGenome, individual_id: int, clicks: int = 0):
    """Build a single shader response dict for a dual genome."""
    shader_code = compiler.compile_dual_to_glsl(
        dual_genome, engine.config, engine.time_config
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


@app.route('/api/compile', methods=['POST'])
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
            dual = dual_genome_from_json(g_data, engine)
            individual_id = g_data.get('key', dual.key if dual else i)
            clicks = g_data.get('clicks', 0)
            shaders.append(_shader_response_for_dual(dual, individual_id, clicks))
        return jsonify({'shaders': shaders})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/random', methods=['POST'])
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
            dual = create_random_dual_genome(engine, genome_id=i)
            genomes.append(dual_genome_to_json(dual))
        return jsonify({'genomes': genomes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/seeds', methods=['GET'])
def api_seeds():
    """Return curated seed genomes (from data/seeds.json)."""
    return jsonify({'seeds': _curated_seeds})


@app.route('/api/community/submit', methods=['POST'])
def api_community_submit():
    """
    Submit a pattern to the community pool.
    Body: { "genome": { key, visual, time_signal }, "name": "...", "creator": "..." }
    Returns: { "id": ..., "status": "pending" }
    """
    try:
        data = request.json or {}
        genome = data.get('genome')
        name = (data.get('name') or '').strip() or 'Unnamed'
        creator = (data.get('creator') or '').strip() or 'Anonymous'
        if not genome or not isinstance(genome, dict):
            return jsonify({'error': 'genome object required'}), 400
        genome_json = json.dumps(genome)
        conn = _get_db()
        cur = conn.execute(
            """INSERT INTO submissions (name, creator, genome_json, status, submitted_at)
               VALUES (?, ?, ?, 'pending', ?)""",
            (name, creator, genome_json, datetime.utcnow().isoformat())
        )
        conn.commit()
        sid = cur.lastrowid
        conn.close()
        return jsonify({'id': sid, 'status': 'pending'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/community', methods=['GET'])
def api_community():
    """Return approved community submissions (genome list)."""
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, approved_at
               FROM submissions WHERE status = 'approved' ORDER BY approved_at DESC"""
        ).fetchall()
        conn.close()
        patterns = []
        for row in rows:
            try:
                genome = json.loads(row['genome_json'])
                patterns.append({
                    'id': row['id'],
                    'name': row['name'],
                    'creator': row['creator'],
                    'genome': genome,
                    'approved_at': row['approved_at'],
                })
            except (json.JSONDecodeError, TypeError):
                continue
        return jsonify({'patterns': patterns})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Admin moderation endpoints (requires ADMIN_KEY)
# ---------------------------------------------------------------------------

# Default to ALICE when unset so local dev works without setting env
ADMIN_KEY = (os.environ.get('ADMIN_KEY') or 'ALICE').strip()
# Normalize: strip and remove any carriage returns (env can have \r in some Docker setups)
ADMIN_KEY = ADMIN_KEY.replace('\r', '').replace('\n', '').strip()


def _normalize_key(raw):
    """Normalize key from request for comparison."""
    if raw is None:
        return ''
    s = str(raw).strip().replace('\r', '').replace('\n', '')
    return s


def _check_admin_key():
    """Check if request has valid admin key (header X-Admin-Key or query admin_key)."""
    raw = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
    key = _normalize_key(raw)
    # In development, always accept ALICE so it works regardless of env
    if os.environ.get("FLASK_ENV") == "development" and key == "ALICE":
        return True, None, None
    if not ADMIN_KEY:
        return False, jsonify({'error': 'Admin key not configured'}), 500
    if key != ADMIN_KEY:
        if os.environ.get("FLASK_ENV") == "development":
            import sys
            print("Admin key mismatch: expected len=%d got len=%d key_repr=%r" % (len(ADMIN_KEY), len(key), key), file=sys.stderr)
        return False, jsonify({'error': 'Invalid admin key'}), 403
    return True, None, None


@app.route('/api/admin/status', methods=['GET'])
def api_admin_status():
    """Public endpoint: report if admin key is configured and its length (for debugging 403)."""
    return jsonify({
        'configured': bool(ADMIN_KEY),
        'key_length': len(ADMIN_KEY),
    })


@app.route('/api/admin/submissions', methods=['GET'])
def api_admin_submissions():
    """List all pending submissions (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        conn = _get_db()
        rows = conn.execute(
            """SELECT id, name, creator, genome_json, status, submitted_at
               FROM submissions WHERE status = 'pending' ORDER BY submitted_at ASC"""
        ).fetchall()
        conn.close()
        submissions = []
        for row in rows:
            try:
                genome = json.loads(row['genome_json'])
                submissions.append({
                    'id': row['id'],
                    'name': row['name'],
                    'creator': row['creator'],
                    'genome': genome,
                    'status': row['status'],
                    'submitted_at': row['submitted_at'],
                })
            except (json.JSONDecodeError, TypeError):
                continue
        return jsonify({'submissions': submissions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/approve', methods=['POST'])
def api_admin_approve():
    """Approve a submission (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get('id')
        if not submission_id:
            return jsonify({'error': 'id required'}), 400
        conn = _get_db()
        conn.execute(
            """UPDATE submissions SET status = 'approved', approved_at = ?
               WHERE id = ? AND status = 'pending'""",
            (datetime.utcnow().isoformat(), submission_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'id': submission_id, 'status': 'approved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reject', methods=['POST'])
def api_admin_reject():
    """Reject a submission (admin only)."""
    ok, err_response, status = _check_admin_key()
    if not ok:
        return err_response, status
    try:
        data = request.json or {}
        submission_id = data.get('id')
        if not submission_id:
            return jsonify({'error': 'id required'}), 400
        conn = _get_db()
        conn.execute(
            """UPDATE submissions SET status = 'rejected'
               WHERE id = ? AND status = 'pending'""",
            (submission_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({'id': submission_id, 'status': 'rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
