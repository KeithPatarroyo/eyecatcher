"""Shared pytest fixtures for Eyecatcher tests."""

import pytest
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
