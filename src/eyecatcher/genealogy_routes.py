"""
Genealogy API Blueprint for Eyecatcher.

Tracks evolutionary history: populations, individuals, and their relationships.
Auto-saves every generation to enable branch exploration and time-travel evolution.
"""
import json
import os
import sqlite3
from datetime import datetime

from flask import Blueprint, jsonify, request


# Create blueprint
genealogy_bp = Blueprint('genealogy', __name__)

# Database path (same location as community DB)
def _default_genealogy_db_path():
    from . import get_root_dir
    return os.path.join(get_root_dir(), "data", "genealogy.db")


GENEALOGY_DB_PATH = os.environ.get("GENEALOGY_DB_PATH") or _default_genealogy_db_path()


def _get_db():
    """Get a connection to the genealogy database."""
    os.makedirs(os.path.dirname(GENEALOGY_DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(GENEALOGY_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _init_genealogy_db():
    """Initialize the genealogy database schema."""
    conn = _get_db()
    
    # Population nodes (generations)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS populations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER REFERENCES populations(id),
            generation_num INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL,
            branch_name TEXT NOT NULL DEFAULT 'main',
            description TEXT,
            user_id TEXT,
            population_size INTEGER,
            metadata_json TEXT
        )
    """)
    
    # Individual genomes within populations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS individuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            population_id INTEGER NOT NULL REFERENCES populations(id),
            genome_key INTEGER NOT NULL,
            genome_json TEXT NOT NULL,
            fitness REAL DEFAULT 0,
            parent1_id INTEGER REFERENCES individuals(id),
            parent2_id INTEGER REFERENCES individuals(id),
            mutation_only BOOLEAN DEFAULT 0,
            created_at TIMESTAMP NOT NULL
        )
    """)
    
    # Indexes for performance
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_populations_parent 
        ON populations(parent_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_individuals_population 
        ON individuals(population_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_individuals_parents 
        ON individuals(parent1_id, parent2_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_populations_branch_gen 
        ON populations(branch_name, generation_num)
    """)

    conn.commit()
    conn.close()


# Initialize DB on module load
_init_genealogy_db()


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@genealogy_bp.route('/api/genealogy/save-population', methods=['POST'])
def save_population():
    """
    Save a complete population (generation) to the genealogy tree.
    
    Body: {
        "genomes": [{ key, visual, time_signal }, ...],
        "parent_id": <int or null>,  # parent population ID
        "generation_num": <int>,
        "branch_name": <string>,
        "description": <string>,
        "user_id": <string>,
        "fitness_data": [<clicks>, ...]  # optional fitness per genome
    }
    
    Returns: { "population_id": <int>, "individual_ids": [<int>, ...] }
    """
    try:
        data = request.json or {}
        genomes = data.get('genomes', [])
        parent_id = data.get('parent_id')
        generation_num = data.get('generation_num', 0)
        branch_name = data.get('branch_name', 'main')
        description = data.get('description', '')
        user_id = data.get('user_id', 'anonymous')
        fitness_data = data.get('fitness_data', [])
        
        if not genomes:
            return jsonify({'error': 'genomes array required'}), 400
        
        conn = _get_db()
        try:
            if parent_id is not None:
                parent_row = conn.execute(
                    "SELECT generation_num FROM populations WHERE id = ?", (parent_id,)
                ).fetchone()
                if not parent_row:
                    return jsonify({'error': 'parent_id not found'}), 400
                if generation_num != parent_row['generation_num'] + 1:
                    return jsonify({
                        'error': 'generation_num must be parent generation_num + 1',
                        'parent_generation_num': parent_row['generation_num']
                    }), 400

            cur = conn.execute(
                """INSERT INTO populations 
                   (parent_id, generation_num, created_at, branch_name, description, 
                    user_id, population_size, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (parent_id, generation_num, datetime.utcnow().isoformat(),
                 branch_name, description, user_id, len(genomes), '{}')
            )
            population_id = cur.lastrowid

            individual_ids = []
            for idx, genome in enumerate(genomes):
                genome_json = json.dumps(genome)
                fitness = fitness_data[idx] if idx < len(fitness_data) else 0
                cur = conn.execute(
                    """INSERT INTO individuals 
                       (population_id, genome_key, genome_json, fitness, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (population_id, genome.get('key', idx), genome_json,
                     fitness, datetime.utcnow().isoformat())
                )
                individual_ids.append(cur.lastrowid)

            conn.commit()
            return jsonify({
                'population_id': population_id,
                'individual_ids': individual_ids,
                'generation_num': generation_num
            })
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/load-population/<int:population_id>', methods=['GET'])
def load_population(population_id):
    """
    Load a complete population by ID.
    
    Returns: {
        "population_id": <int>,
        "parent_id": <int or null>,
        "generation_num": <int>,
        "created_at": <timestamp>,
        "branch_name": <string>,
        "description": <string>,
        "genomes": [{ key, visual, time_signal }, ...]
    }
    """
    try:
        conn = _get_db()
        try:
            pop_row = conn.execute(
                """SELECT * FROM populations WHERE id = ?""",
                (population_id,)
            ).fetchone()

            if not pop_row:
                return jsonify({'error': 'Population not found'}), 404

            individual_rows = conn.execute(
                """SELECT genome_json, fitness FROM individuals 
                   WHERE population_id = ? ORDER BY genome_key""",
                (population_id,)
            ).fetchall()

            genomes = []
            for row in individual_rows:
                try:
                    genome = json.loads(row['genome_json'])
                    genome['clicks'] = row['fitness']
                    genomes.append(genome)
                except (json.JSONDecodeError, TypeError):
                    continue

            return jsonify({
                'population_id': pop_row['id'],
                'parent_id': pop_row['parent_id'],
                'generation_num': pop_row['generation_num'],
                'created_at': pop_row['created_at'],
                'branch_name': pop_row['branch_name'],
                'description': pop_row['description'],
                'user_id': pop_row['user_id'],
                'genomes': genomes
            })
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/tree', methods=['GET'])
def get_tree():
    """
    Get the complete genealogical tree structure.
    
    Returns: {
        "nodes": [
            {
                "id": <int>,
                "parent_id": <int or null>,
                "generation_num": <int>,
                "created_at": <timestamp>,
                "branch_name": <string>,
                "description": <string>,
                "population_size": <int>
            },
            ...
        ]
    }
    """
    try:
        conn = _get_db()
        try:
            rows = conn.execute(
                """SELECT id, parent_id, generation_num, created_at, branch_name,
                          description, user_id, population_size
                   FROM populations ORDER BY created_at ASC"""
            ).fetchall()

            nodes = [
                {
                    'id': row['id'],
                    'parent_id': row['parent_id'],
                    'generation_num': row['generation_num'],
                    'created_at': row['created_at'],
                    'branch_name': row['branch_name'],
                    'description': row['description'],
                    'user_id': row['user_id'],
                    'population_size': row['population_size']
                }
                for row in rows
            ]
            return jsonify({'nodes': nodes})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/branches', methods=['GET'])
def get_branches():
    """
    Get all branch names and their latest generations.
    
    Returns: {
        "branches": [
            {
                "name": <string>,
                "latest_generation": <int>,
                "latest_population_id": <int>,
                "node_count": <int>
            },
            ...
        ]
    }
    """
    try:
        conn = _get_db()
        try:
            rows = conn.execute(
                """SELECT branch_name,
                          MAX(generation_num) as latest_gen,
                          COUNT(*) as node_count
                   FROM populations
                   GROUP BY branch_name
                   ORDER BY branch_name"""
            ).fetchall()

            branches = []
            for row in rows:
                latest_pop = conn.execute(
                    """SELECT id FROM populations
                       WHERE branch_name = ? AND generation_num = ?
                       ORDER BY created_at DESC LIMIT 1""",
                    (row['branch_name'], row['latest_gen'])
                ).fetchone()
                branches.append({
                    'name': row['branch_name'],
                    'latest_generation': row['latest_gen'],
                    'latest_population_id': latest_pop['id'] if latest_pop else None,
                    'node_count': row['node_count']
                })
            return jsonify({'branches': branches})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/reset', methods=['POST'])
def reset_genealogy():
    """
    Clear all genealogy data (populations and individuals).
    Use for a fresh start; data cannot be recovered.
    Returns: { "status": "ok" }
    """
    try:
        conn = _get_db()
        try:
            conn.execute("DELETE FROM individuals")
            conn.execute("DELETE FROM populations")
            conn.commit()
            return jsonify({'status': 'ok'})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/export-sizes', methods=['GET'])
def export_sizes():
    """
    Return estimated export sizes for full tree and per branch (for download modal).
    Returns: { "full": { "populations", "individuals", "estimated_bytes" },
               "branches": [ { "name", "populations", "individuals", "estimated_bytes" }, ... ] }
    """
    try:
        conn = _get_db()
        try:
            # Full: counts and total genome JSON size
            full_pop = conn.execute("SELECT COUNT(*) as c FROM populations").fetchone()['c']
            full_ind = conn.execute(
                "SELECT COUNT(*) as c, COALESCE(SUM(LENGTH(genome_json)), 0) as total_json FROM individuals"
            ).fetchone()
            full_ind_count = full_ind['c']
            full_json_bytes = full_ind['total_json'] or 0
            # Overhead: populations ~300 bytes each, individuals wrapper ~80 bytes each
            full_estimated = full_pop * 300 + full_ind_count * 80 + full_json_bytes

            # Per branch
            branch_rows = conn.execute(
                """SELECT branch_name, COUNT(*) as pop_count
                   FROM populations GROUP BY branch_name ORDER BY branch_name"""
            ).fetchall()
            branches = []
            for row in branch_rows:
                name = row['branch_name']
                pop_count = row['pop_count']
                pop_ids = [r['id'] for r in conn.execute(
                    "SELECT id FROM populations WHERE branch_name = ?", (name,)
                ).fetchall()]
                if not pop_ids:
                    ind_count = 0
                    json_bytes = 0
                else:
                    placeholders = ','.join('?' * len(pop_ids))
                    ind_row = conn.execute(
                        f"""SELECT COUNT(*) as c, COALESCE(SUM(LENGTH(genome_json)), 0) as total_json
                            FROM individuals WHERE population_id IN ({placeholders})""",
                        pop_ids
                    ).fetchone()
                    ind_count = ind_row['c']
                    json_bytes = ind_row['total_json'] or 0
                estimated = pop_count * 300 + ind_count * 80 + json_bytes
                branches.append({
                    'name': name,
                    'populations': pop_count,
                    'individuals': ind_count,
                    'estimated_bytes': estimated,
                })
            return jsonify({
                'full': {
                    'populations': full_pop,
                    'individuals': full_ind_count,
                    'estimated_bytes': full_pop * 300 + full_ind_count * 80 + full_json_bytes,
                },
                'branches': branches,
            })
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/export', methods=['GET'])
def export_genealogy():
    """
    Export genealogy as JSON (populations + individuals with genomes).
    Query: ?branch_name=<name> to export only that branch; omit for full tree.
    """
    branch_name = request.args.get('branch_name', '').strip() or None
    try:
        conn = _get_db()
        try:
            if branch_name:
                pop_rows = conn.execute(
                    """SELECT id, parent_id, generation_num, created_at, branch_name,
                              description, user_id, population_size, metadata_json
                       FROM populations WHERE branch_name = ? ORDER BY id ASC""",
                    (branch_name,)
                ).fetchall()
                pop_ids = [r['id'] for r in pop_rows]
                if not pop_ids:
                    return jsonify({'error': 'Branch not found or empty', 'branch_name': branch_name}), 404
                placeholders = ','.join('?' * len(pop_ids))
                ind_rows = conn.execute(
                    f"""SELECT id, population_id, genome_key, genome_json, fitness, created_at
                        FROM individuals WHERE population_id IN ({placeholders}) ORDER BY id ASC""",
                    pop_ids
                ).fetchall()
            else:
                pop_rows = conn.execute(
                    """SELECT id, parent_id, generation_num, created_at, branch_name,
                              description, user_id, population_size, metadata_json
                       FROM populations ORDER BY id ASC"""
                ).fetchall()
                ind_rows = conn.execute(
                    """SELECT id, population_id, genome_key, genome_json, fitness, created_at
                       FROM individuals ORDER BY id ASC"""
                ).fetchall()

            populations = [
                {
                    'id': r['id'],
                    'parent_id': r['parent_id'],
                    'generation_num': r['generation_num'],
                    'created_at': r['created_at'],
                    'branch_name': r['branch_name'],
                    'description': r['description'],
                    'user_id': r['user_id'],
                    'population_size': r['population_size'],
                    'metadata_json': r['metadata_json'],
                }
                for r in pop_rows
            ]
            individuals = []
            for r in ind_rows:
                individuals.append({
                    'id': r['id'],
                    'population_id': r['population_id'],
                    'genome_key': r['genome_key'],
                    'genome_json': json.loads(r['genome_json']) if isinstance(r['genome_json'], str) else r['genome_json'],
                    'fitness': r['fitness'],
                    'created_at': r['created_at'],
                })
            return jsonify({
                'exported_at': datetime.utcnow().isoformat() + 'Z',
                'version': 1,
                'branch_name': branch_name,
                'populations': populations,
                'individuals': individuals,
            })
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/stats', methods=['GET'])
def get_stats():
    """
    Get overall genealogy statistics.
    
    Returns: {
        "total_populations": <int>,
        "total_individuals": <int>,
        "total_branches": <int>,
        "max_generation": <int>
    }
    """
    try:
        conn = _get_db()
        try:
            stats = conn.execute(
                """SELECT
                    COUNT(DISTINCT id) as total_pops,
                    COUNT(DISTINCT branch_name) as total_branches,
                    MAX(generation_num) as max_gen
                   FROM populations"""
            ).fetchone()
            total_individuals = conn.execute(
                "SELECT COUNT(*) as total FROM individuals"
            ).fetchone()['total']
            return jsonify({
                'total_populations': stats['total_pops'],
                'total_individuals': total_individuals,
                'total_branches': stats['total_branches'],
                'max_generation': stats['max_gen'] or 0
            })
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@genealogy_bp.route('/api/genealogy/population-thumbnail/<int:population_id>', methods=['GET'])
def get_population_thumbnail(population_id):
    """
    Get the fittest individual's genome from a population for thumbnail rendering.
    
    Returns: {
        "genome": <genome JSON>,
        "fitness": <float>
    }
    """
    try:
        conn = _get_db()
        try:
            row = conn.execute(
                """SELECT genome_json, fitness FROM individuals
                   WHERE population_id = ?
                   ORDER BY fitness DESC
                   LIMIT 1""",
                (population_id,)
            ).fetchone()

            if not row:
                return jsonify({'error': 'No individuals found in this population'}), 404

            genome = json.loads(row['genome_json'])
            return jsonify({
                'genome': genome,
                'fitness': row['fitness']
            })
        except (json.JSONDecodeError, TypeError):
            return jsonify({'error': 'Invalid genome data'}), 500
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
