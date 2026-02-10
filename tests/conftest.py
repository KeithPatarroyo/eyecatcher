"""Shared pytest fixtures for Eyecatcher.

Provides client (Flask test client), cppn_engine (CPPNEngine with population),
random_dual_genome, minimal_dual, genealogy_db, community_db. All DB fixtures
use temp paths; no real data is modified.
"""

from unittest.mock import patch

import pytest
from eyecatcher import community_routes, genealogy_routes
from eyecatcher.evolution import (
    CPPNEngine,
    create_random_dual_genome,
    dual_genome_from_json,
)
from eyecatcher.server import app


def minimal_dual_genome_one_hidden_visual(engine: CPPNEngine):
    """Dual genome with exactly one hidden node in the visual CPPN (deterministic)."""
    vc = engine.config.genome_config
    tc = engine.time_config.genome_config
    visual_nodes = {
        str(i): {
            "bias": 0.0,
            "response": 1.0,
            "activation": "sigmoid",
            "aggregation": "sum",
        }
        for i in list(range(-vc.num_inputs, 0))
        + list(range(vc.num_outputs))
        + [vc.num_outputs]
    }
    visual_conns = {
        "-1_3": {"innovation": 1, "weight": 0.5, "enabled": True},
        "3_0": {"innovation": 2, "weight": 0.5, "enabled": True},
    }
    time_nodes = {
        str(i): {
            "bias": 0.0,
            "response": 1.0,
            "activation": "sigmoid",
            "aggregation": "sum",
        }
        for i in list(range(-tc.num_inputs, 0)) + [0]
    }
    time_conns = {"-1_0": {"innovation": 1, "weight": 0.5, "enabled": True}}
    data = {
        "key": 0,
        "visual": {
            "key": 0,
            "fitness": None,
            "nodes": visual_nodes,
            "connections": visual_conns,
        },
        "time_signal": {
            "key": 0,
            "fitness": None,
            "nodes": time_nodes,
            "connections": time_conns,
        },
    }
    return dual_genome_from_json(data, engine.config, engine.time_config)


@pytest.fixture
def client():
    """Flask test client with TESTING enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def cppn_engine():
    """CPPNEngine with population created (for mutation, crossover, query tests)."""
    engine = CPPNEngine()
    engine.create_population()
    return engine


@pytest.fixture
def minimal_dual(cppn_engine):
    """Dual genome with one hidden node in visual CPPN (deterministic)."""
    return minimal_dual_genome_one_hidden_visual(cppn_engine)


@pytest.fixture
def random_dual_genome(cppn_engine):
    """Random dual genome with genome_id=0 (for tests that need one random genome)."""
    return create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=0
    )


@pytest.fixture
def genealogy_db(tmp_path):
    """Use a temp DB for genealogy so tests don't touch the real one."""
    path = tmp_path / "genealogy.db"
    with patch.object(genealogy_routes, "GENEALOGY_DB_PATH", str(path)):
        genealogy_routes._init_genealogy_db()
        yield path


@pytest.fixture
def community_db(tmp_path):
    """Use a temp DB for community so tests don't touch the real one."""
    path = tmp_path / "community.db"
    with patch.object(community_routes, "DATABASE_PATH", str(path)):
        community_routes._init_community_db()
        yield path
