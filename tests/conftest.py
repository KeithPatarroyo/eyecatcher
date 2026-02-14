"""Shared pytest fixtures for Eyecatcher.

Provides client, representation (DualCPPNRepresentation), random_dual_genome,
minimal_dual, genealogy_db, community_db. DB fixtures use temp paths; no real
data modified.
"""

from unittest.mock import patch

import eyecatcher.data.genealogy_db as genealogy_db_module
import pytest
from eyecatcher.genome import create_random_dual_genome, dual_genome_from_json
from eyecatcher.representation import DualCPPNRepresentation
from eyecatcher.server import app
from eyecatcher.web import community_routes


def minimal_dual_genome_one_hidden_visual(representation):
    """Dual genome with exactly one hidden node in the visual CPPN (deterministic)."""
    vc = representation.config.genome_config
    tc = representation.time_config.genome_config
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
    return dual_genome_from_json(
        data, representation.config, representation.time_config
    )


@pytest.fixture
def client():
    """Flask test client with TESTING enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def representation():
    """DualCPPNRepresentation for mutation, crossover, query tests."""
    return DualCPPNRepresentation()


@pytest.fixture
def minimal_dual(representation):
    """Dual genome with one hidden node in visual CPPN (deterministic)."""
    return minimal_dual_genome_one_hidden_visual(representation)


@pytest.fixture
def random_dual_genome(representation):
    """Random dual genome with genome_id=0 (for tests that need one random genome)."""
    return create_random_dual_genome(
        representation.config, representation.time_config, genome_id=0
    )


@pytest.fixture
def dual_cppn_representation():
    """DualCPPNRepresentation instance for testing representation protocol methods."""
    return DualCPPNRepresentation()


@pytest.fixture
def genealogy_db(tmp_path):
    """Use a temp DB for genealogy so tests don't touch the real one."""
    path = tmp_path / "genealogy.db"
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(path)):
        genealogy_db_module.init_genealogy_db()
        yield path


@pytest.fixture
def community_db(tmp_path):
    """Use a temp DB for community so tests don't touch the real one."""
    path = tmp_path / "community.db"
    with patch.object(community_routes, "DATABASE_PATH", str(path)):
        community_routes._init_community_db()
        yield path
