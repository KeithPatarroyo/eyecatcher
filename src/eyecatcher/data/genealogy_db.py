"""
Genealogy data layer: DB init, save, and pure query functions.

No Flask; all functions take no request state and return Python data.
Routes in genealogy_routes.py parse request and call these functions.
Researchers extend via populations.metadata_json (optional metadata dict).
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from .db_util import default_db_path, with_db_connection

GENEALOGY_DB_PATH = os.environ.get("GENEALOGY_DB_PATH") or default_db_path(
    "genealogy.db"
)
GENEALOGY_PRAGMAS = ("PRAGMA foreign_keys = ON",)


@contextmanager
def _genealogy_db():
    """Context manager for genealogy DB connection with standard pragmas."""
    with with_db_connection(GENEALOGY_DB_PATH, pragmas=GENEALOGY_PRAGMAS) as conn:
        yield conn


def _safe_parse_genome_json(value: Any) -> dict[str, Any] | None:
    """Parse genome_json string to dict; return None on error."""
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value if isinstance(value, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _validate_parent(
    conn: Any, parent_id: int | None, generation_num: int
) -> tuple[bool, dict[str, Any] | None]:
    """Check parent exists and generation_num is parent+1. Returns (valid, err)."""
    if parent_id is None:
        return True, None
    row = conn.execute(
        "SELECT generation_num FROM populations WHERE id = ?", (parent_id,)
    ).fetchone()
    if not row:
        return False, {"error": "parent_not_found"}
    if generation_num != row["generation_num"] + 1:
        return False, {
            "error": "generation_mismatch",
            "parent_generation_num": row["generation_num"],
        }
    return True, None


def init_genealogy_db() -> None:
    """Create populations and individuals tables and indexes if they do not exist."""
    with _genealogy_db() as conn:
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


def _insert_population_with_individuals(
    conn,
    parent_id: int | None,
    generation_num: int,
    branch_name: str,
    description: str,
    user_id: str,
    genomes: list,
    metadata: dict[str, Any] | None,
    fitness_data: list[float] | None = None,
) -> tuple[int, list[int]]:
    """
    Insert one population row and its individual rows. Caller must hold conn.
    Returns (population_id, list of individual_ids).
    """
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
    fitness_data = fitness_data or []
    for idx, genome in enumerate(genomes):
        genome_json = json.dumps(genome) if not isinstance(genome, str) else genome
        genome_key = genome.get("key", idx) if isinstance(genome, dict) else idx
        fitness = fitness_data[idx] if idx < len(fitness_data) else 0
        cur = conn.execute(
            """INSERT INTO individuals
               (population_id, genome_key, genome_json, fitness, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                population_id,
                genome_key,
                genome_json,
                fitness,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        individual_ids.append(cur.lastrowid)
    return population_id, individual_ids


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
    with _genealogy_db() as conn:
        valid, _ = _validate_parent(conn, parent_population_id, generation_num)
        if not valid:
            return None
        population_id, _ = _insert_population_with_individuals(
            conn,
            parent_population_id,
            generation_num,
            branch_name,
            f"Generation {generation_num}",
            "user",
            children,
            metadata,
            None,
        )
        conn.commit()
        return population_id


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
    with _genealogy_db() as conn:
        if parent_id is not None:
            valid, err = _validate_parent(conn, parent_id, generation_num)
            if not valid:
                return err
        population_id, individual_ids = _insert_population_with_individuals(
            conn,
            parent_id,
            generation_num,
            branch_name,
            description,
            user_id,
            genomes,
            metadata,
            fitness_data,
        )
        conn.commit()
        return {
            "population_id": population_id,
            "individual_ids": individual_ids,
            "generation_num": generation_num,
        }


# Column lists used by export and query helpers (single source of truth)
_POP_COLS = """id, parent_id, generation_num, created_at, branch_name,
                description, user_id, population_size, metadata_json"""
_IND_COLS = """id, population_id, genome_key, genome_json, fitness, created_at"""


def _fetch_individuals_by_population(
    conn: Any,
    population_id: int,
    order_by: str = "genome_key",
    limit: int | None = None,
) -> list[Any]:
    """Return rows (genome_json, fitness). order_by: 'genome_key' or 'fitness DESC'."""
    allowed_order = "fitness DESC" if order_by == "fitness DESC" else "genome_key"
    sql = f"""SELECT genome_json, fitness FROM individuals
              WHERE population_id = ? ORDER BY {allowed_order}"""
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, (population_id,)).fetchall()


def _fetch_population_rows(
    conn: Any, where_clause: str | None = None, where_params: tuple = ()
) -> list[Any]:
    """Return population rows (pop columns). Optional WHERE clause."""
    sql = f"SELECT {_POP_COLS} FROM populations"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += " ORDER BY id ASC"
    return conn.execute(sql, where_params).fetchall()


def _fetch_individual_rows_by_pop_ids(conn: Any, pop_ids: list[int]) -> list[Any]:
    """Return individual rows for the given population ids. Empty pop_ids → []."""
    if not pop_ids:
        return []
    placeholders = ",".join("?" * len(pop_ids))
    return conn.execute(
        f"SELECT {_IND_COLS} FROM individuals "
        f"WHERE population_id IN ({placeholders}) ORDER BY id ASC",
        pop_ids,
    ).fetchall()


def get_population(population_id: int) -> dict[str, Any] | None:
    """Load one population by id with its individuals (genomes with fitness)."""
    with _genealogy_db() as conn:
        pop_row = conn.execute(
            "SELECT * FROM populations WHERE id = ?", (population_id,)
        ).fetchone()
        if not pop_row:
            return None
        individual_rows = _fetch_individuals_by_population(conn, population_id)
        genomes = []
        for row in individual_rows:
            genome = _safe_parse_genome_json(row["genome_json"])
            if genome is not None:
                genome["fitness"] = row["fitness"]
                genomes.append(genome)
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


def get_experiment_log(limit: int = 200) -> list[dict[str, Any]]:
    """
    Recent population save events with metadata (for research / experiment log).
    Returns list of { id, created_at, branch_name, generation_num,
        population_size, metadata }.
    """
    with _genealogy_db() as conn:
        rows = conn.execute(
            """SELECT id, created_at, branch_name, generation_num, population_size,
                      metadata_json
               FROM populations
               ORDER BY created_at DESC
               LIMIT ?""",
            (max(1, min(limit, 1000)),),
        ).fetchall()
        out = []
        for row in rows:
            row_dict = dict(row)
            meta = {}
            if row_dict.get("metadata_json"):
                try:
                    meta = json.loads(row_dict["metadata_json"]) or {}
                except (json.JSONDecodeError, TypeError):
                    pass
            out.append(
                {
                    "id": row_dict["id"],
                    "created_at": row_dict["created_at"],
                    "branch_name": row_dict["branch_name"],
                    "generation_num": row_dict["generation_num"],
                    "population_size": row_dict["population_size"],
                    "metadata": meta,
                }
            )
        return out


def get_tree_nodes() -> list[dict[str, Any]]:
    """All population nodes ordered by created_at for tree view."""
    with _genealogy_db() as conn:
        rows = conn.execute(
            """SELECT id, parent_id, generation_num, created_at, branch_name,
                      description, user_id, population_size
               FROM populations ORDER BY created_at ASC"""
        ).fetchall()
        return [dict(row) for row in rows]


def get_branches() -> list[dict[str, Any]]:
    """Per-branch summary: name, latest_generation, latest_population_id, node_count."""
    with _genealogy_db() as conn:
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
    with _genealogy_db() as conn:
        conn.execute("DELETE FROM individuals")
        conn.execute("DELETE FROM populations")
        conn.commit()


def export_sizes() -> dict[str, Any]:
    """Full and per-branch counts and estimated export size in bytes."""
    with _genealogy_db() as conn:
        pop_row = conn.execute("SELECT COUNT(*) as c FROM populations").fetchone()
        full_pop = pop_row["c"]
        ind_row = conn.execute(
            "SELECT COUNT(*) as c, COALESCE(SUM(LENGTH(genome_json)), 0) as total_json "
            "FROM individuals"
        ).fetchone()
        full_ind_count = ind_row["c"]
        full_json_bytes = ind_row["total_json"] or 0
        full_estimated = full_pop * 300 + full_ind_count * 80 + full_json_bytes

        branch_rows = conn.execute(
            """SELECT branch_name, COUNT(*) as pop_count
               FROM populations
               GROUP BY branch_name ORDER BY branch_name"""
        ).fetchall()
        branches = []
        for row in branch_rows:
            name = row["branch_name"]
            pop_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM populations WHERE branch_name = ?", (name,)
                ).fetchall()
            ]
            pop_count = len(pop_ids)
            if not pop_ids:
                ind_count = json_bytes = 0
            else:
                placeholders = ",".join("?" * len(pop_ids))
                ind_row = conn.execute(
                    f"""SELECT COUNT(*) as c,
                        COALESCE(SUM(LENGTH(genome_json)), 0) as total_json
                        FROM individuals WHERE population_id IN ({placeholders})""",
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
    with _genealogy_db() as conn:
        if branch_name:
            pop_rows = _fetch_population_rows(conn, "branch_name = ?", (branch_name,))
        else:
            pop_rows = _fetch_population_rows(conn)
        pop_ids = [r["id"] for r in pop_rows]
        if branch_name and not pop_ids:
            return None
        ind_rows = _fetch_individual_rows_by_pop_ids(conn, pop_ids)

        populations = [dict(r) for r in pop_rows]
        individuals = []
        for r in ind_rows:
            d = dict(r)
            parsed = _safe_parse_genome_json(d["genome_json"])
            d["genome_json"] = parsed if parsed is not None else d["genome_json"]
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
    with _genealogy_db() as conn:
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
    with _genealogy_db() as conn:
        rows = _fetch_individuals_by_population(
            conn, population_id, order_by="fitness DESC", limit=1
        )
        if not rows:
            return None
        row = rows[0]
        genome = _safe_parse_genome_json(row["genome_json"])
        return {"genome": genome, "fitness": row["fitness"]} if genome else None
