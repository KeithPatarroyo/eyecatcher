"""
Genealogy data layer: DB init, save, and pure query functions.

No Flask; all functions take no request state and return Python data.
Routes in genealogy_routes.py parse request and call these functions.
Researchers extend via populations.metadata_json (optional metadata dict).
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from ..lib.db_util import default_db_path, with_db_connection

GENEALOGY_DB_PATH = os.environ.get("GENEALOGY_DB_PATH") or default_db_path(
    "genealogy.db"
)
GENEALOGY_PRAGMAS = ("PRAGMA foreign_keys = ON",)


def init_genealogy_db() -> None:
    """Create populations and individuals tables and indexes if they do not exist."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_populations_parent "
            "ON populations(parent_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_individuals_population "
            "ON individuals(population_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_individuals_parents "
            "ON individuals(parent1_id, parent2_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_populations_branch_gen "
            "ON populations(branch_name, generation_num)"
        )
        conn.commit()


def save_generation_result(
    parent_population_id: int,
    generation_num: int,
    branch_name: str,
    children: list,
    metadata: dict[str, Any] | None = None,
) -> int | None:
    """
    Save a generation result (new population + individuals) to genealogy.

    Returns new population_id if saved, None if parent invalid or generation
    mismatch. metadata is stored in populations.metadata_json (for research).
    """
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        parent_row = conn.execute(
            "SELECT generation_num FROM populations WHERE id = ?",
            (parent_population_id,),
        ).fetchone()
        if not parent_row or generation_num != parent_row["generation_num"] + 1:
            return None
        meta_json = json.dumps(metadata) if metadata else "{}"
        cur = conn.execute(
            """INSERT INTO populations
               (parent_id, generation_num, created_at, branch_name, description,
                user_id, population_size, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                parent_population_id,
                generation_num,
                datetime.now(timezone.utc).isoformat(),
                branch_name,
                f"Generation {generation_num}",
                "user",
                len(children),
                meta_json,
            ),
        )
        new_population_id = cur.lastrowid
        for idx, child_genome in enumerate(children):
            genome_json = (
                json.dumps(child_genome)
                if not isinstance(child_genome, str)
                else child_genome
            )
            conn.execute(
                """INSERT INTO individuals
                   (population_id, genome_key, genome_json, fitness, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    new_population_id,
                    (
                        child_genome.get("key", idx)
                        if isinstance(child_genome, dict)
                        else idx
                    ),
                    genome_json,
                    0,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        conn.commit()
        return new_population_id


def save_population(
    genomes: list,
    parent_id: int | None = None,
    generation_num: int = 0,
    branch_name: str = "main",
    description: str = "",
    user_id: str = "anonymous",
    fitness_data: list[float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Insert a new population and its individuals. Validate parent if given.

    Returns { population_id, individual_ids, generation_num } on success.
    On validation error returns { "error": "parent_not_found" } or
    { "error": "generation_mismatch", "parent_generation_num": int }.
    """
    fitness_data = fitness_data or []
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        if parent_id is not None:
            parent_row = conn.execute(
                "SELECT generation_num FROM populations WHERE id = ?",
                (parent_id,),
            ).fetchone()
            if not parent_row:
                return {"error": "parent_not_found"}
            if generation_num != parent_row["generation_num"] + 1:
                return {
                    "error": "generation_mismatch",
                    "parent_generation_num": parent_row["generation_num"],
                }
        meta_json = json.dumps(metadata) if metadata else "{}"
        cur = conn.execute(
            """INSERT INTO populations
               (parent_id, generation_num, created_at, branch_name, description,
                user_id, population_size, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                parent_id,
                generation_num,
                datetime.now(timezone.utc).isoformat(),
                branch_name,
                description,
                user_id,
                len(genomes),
                meta_json,
            ),
        )
        population_id = cur.lastrowid
        individual_ids = []
        for idx, genome in enumerate(genomes):
            genome_json = json.dumps(genome) if not isinstance(genome, str) else genome
            fitness = fitness_data[idx] if idx < len(fitness_data) else 0
            cur = conn.execute(
                """INSERT INTO individuals
                   (population_id, genome_key, genome_json, fitness, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    population_id,
                    genome.get("key", idx) if isinstance(genome, dict) else idx,
                    genome_json,
                    fitness,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            individual_ids.append(cur.lastrowid)
        conn.commit()
        return {
            "population_id": population_id,
            "individual_ids": individual_ids,
            "generation_num": generation_num,
        }


def get_population(population_id: int) -> dict[str, Any] | None:
    """Load one population by id with its individuals (genomes with clicks=fitness)."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        pop_row = conn.execute(
            "SELECT * FROM populations WHERE id = ?", (population_id,)
        ).fetchone()
        if not pop_row:
            return None
        individual_rows = conn.execute(
            """SELECT genome_json, fitness FROM individuals
               WHERE population_id = ? ORDER BY genome_key""",
            (population_id,),
        ).fetchall()
        genomes = []
        for row in individual_rows:
            try:
                genome = json.loads(row["genome_json"])
                genome["clicks"] = row["fitness"]
                genomes.append(genome)
            except (json.JSONDecodeError, TypeError):
                continue
        metadata = {}
        row_dict = dict(pop_row)
        meta_raw = row_dict.get("metadata_json")
        if meta_raw:
            try:
                metadata = json.loads(meta_raw) or {}
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "population_id": pop_row["id"],
            "parent_id": pop_row["parent_id"],
            "generation_num": pop_row["generation_num"],
            "created_at": pop_row["created_at"],
            "branch_name": pop_row["branch_name"],
            "description": pop_row["description"],
            "user_id": pop_row["user_id"],
            "genomes": genomes,
            "metadata": metadata,
        }


def get_tree_nodes() -> list[dict[str, Any]]:
    """All population nodes ordered by created_at for tree view."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        rows = conn.execute(
            """SELECT id, parent_id, generation_num, created_at, branch_name,
                      description, user_id, population_size
               FROM populations ORDER BY created_at ASC"""
        ).fetchall()
        return [dict(row) for row in rows]


def get_branches() -> list[dict[str, Any]]:
    """Per-branch summary: name, latest_generation, latest_population_id, node_count."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
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
                (row["branch_name"], row["latest_gen"]),
            ).fetchone()
            branches.append(
                {
                    "name": row["branch_name"],
                    "latest_generation": row["latest_gen"],
                    "latest_population_id": latest_pop["id"] if latest_pop else None,
                    "node_count": row["node_count"],
                }
            )
        return branches


def reset_genealogy() -> None:
    """Delete all individuals and populations."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        conn.execute("DELETE FROM individuals")
        conn.execute("DELETE FROM populations")
        conn.commit()


def export_sizes() -> dict[str, Any]:
    """Full and per-branch counts and estimated export size in bytes."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        full_pop = conn.execute("SELECT COUNT(*) as c FROM populations").fetchone()["c"]
        full_ind = conn.execute(
            "SELECT COUNT(*) as c, "
            "COALESCE(SUM(LENGTH(genome_json)), 0) as total_json "
            "FROM individuals"
        ).fetchone()
        full_ind_count = full_ind["c"]
        full_json_bytes = full_ind["total_json"] or 0
        full_estimated = full_pop * 300 + full_ind_count * 80 + full_json_bytes

        branch_rows = conn.execute(
            """SELECT branch_name, COUNT(*) as pop_count
               FROM populations GROUP BY branch_name ORDER BY branch_name"""
        ).fetchall()
        branches = []
        for row in branch_rows:
            name = row["branch_name"]
            pop_count = row["pop_count"]
            pop_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM populations WHERE branch_name = ?", (name,)
                ).fetchall()
            ]
            if not pop_ids:
                ind_count = 0
                json_bytes = 0
            else:
                placeholders = ",".join("?" * len(pop_ids))
                ind_row = conn.execute(
                    f"""SELECT COUNT(*) as c,
                        COALESCE(SUM(LENGTH(genome_json)), 0) as total_json
                        FROM individuals
                        WHERE population_id IN ({placeholders})""",
                    pop_ids,
                ).fetchone()
                ind_count = ind_row["c"]
                json_bytes = ind_row["total_json"] or 0
            estimated = pop_count * 300 + ind_count * 80 + json_bytes
            branches.append(
                {
                    "name": name,
                    "populations": pop_count,
                    "individuals": ind_count,
                    "estimated_bytes": estimated,
                }
            )
        return {
            "full": {
                "populations": full_pop,
                "individuals": full_ind_count,
                "estimated_bytes": full_estimated,
            },
            "branches": branches,
        }


def export_genealogy_data(branch_name: str | None = None) -> dict[str, Any] | None:
    """
    Export populations and individuals as dict. branch_name filters to one branch.

    Returns None if branch_name given and no such branch (empty). Otherwise
    dict with exported_at, version, branch_name, populations, individuals
    (genome_json parsed to Python objects).
    """
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        if branch_name:
            pop_rows = conn.execute(
                """SELECT id, parent_id, generation_num, created_at, branch_name,
                          description, user_id, population_size, metadata_json
                   FROM populations
                   WHERE branch_name = ? ORDER BY id ASC""",
                (branch_name,),
            ).fetchall()
            pop_ids = [r["id"] for r in pop_rows]
            if not pop_ids:
                return None
            placeholders = ",".join("?" * len(pop_ids))
            ind_rows = conn.execute(
                f"""SELECT id, population_id, genome_key, genome_json,
                    fitness, created_at
                    FROM individuals
                    WHERE population_id IN ({placeholders}) ORDER BY id ASC""",
                pop_ids,
            ).fetchall()
        else:
            pop_rows = conn.execute(
                """SELECT id, parent_id, generation_num, created_at, branch_name,
                          description, user_id, population_size, metadata_json
                   FROM populations
                   ORDER BY id ASC"""
            ).fetchall()
            ind_rows = conn.execute(
                """SELECT id, population_id, genome_key, genome_json,
                   fitness, created_at
                   FROM individuals
                   ORDER BY id ASC"""
            ).fetchall()

        populations = [dict(r) for r in pop_rows]
        individuals = []
        for r in ind_rows:
            d = dict(r)
            d["genome_json"] = (
                json.loads(d["genome_json"])
                if isinstance(d["genome_json"], str)
                else d["genome_json"]
            )
            individuals.append(d)
        return {
            "exported_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "version": 1,
            "branch_name": branch_name,
            "populations": populations,
            "individuals": individuals,
        }


def get_stats() -> dict[str, Any]:
    """Return aggregate counts (populations, individuals, branches, max_gen)."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        stats = conn.execute(
            """SELECT
                COUNT(DISTINCT id) as total_pops,
                COUNT(DISTINCT branch_name) as total_branches,
                MAX(generation_num) as max_gen
               FROM populations"""
        ).fetchone()
        total_individuals = conn.execute(
            "SELECT COUNT(*) as total FROM individuals"
        ).fetchone()["total"]
        return {
            "total_populations": stats["total_pops"],
            "total_individuals": total_individuals,
            "total_branches": stats["total_branches"],
            "max_generation": stats["max_gen"] or 0,
        }


def get_population_thumbnail(
    population_id: int,
) -> dict[str, Any] | None:
    """Fittest individual (by fitness DESC); returns { genome, fitness } or None."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        row = conn.execute(
            """SELECT genome_json, fitness FROM individuals
               WHERE population_id = ?
               ORDER BY fitness DESC
               LIMIT 1""",
            (population_id,),
        ).fetchone()
        if not row:
            return None
        genome = json.loads(row["genome_json"])
        return {"genome": genome, "fitness": row["fitness"]}
