"""
Stateless API Blueprint for Eyecatcher.

Provides endpoints that don't depend on server-side population state:
- /api/compile: Compile genome JSON to GLSL shaders
- /api/random: Generate random population as genome JSON
- /api/seeds: Return curated seed patterns
"""
import json
import os
from flask import Blueprint, jsonify, request

from cppn_engine import CPPNEngine, DualGenome, create_random_dual_genome
from genome_serialization import dual_genome_from_json, dual_genome_to_json
from shader_compiler import ShaderCompiler


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
