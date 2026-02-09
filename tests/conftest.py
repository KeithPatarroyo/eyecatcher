"""Shared pytest fixtures for Eyecatcher tests."""

from unittest.mock import patch

import pytest
from eyecatcher import community_routes, genealogy_routes
from eyecatcher.cppn_engine import CPPNEngine
from eyecatcher.server import app


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
