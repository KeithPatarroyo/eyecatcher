"""Tests for genealogy data layer (no Flask)."""

from unittest.mock import patch

import eyecatcher.data.genealogy_db as genealogy_db_module
import pytest


@pytest.fixture
def db_path(tmp_path):
    """Temp DB path; patch module and init."""
    path = tmp_path / "genealogy.db"
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(path)):
        genealogy_db_module.init_genealogy_db()
        yield path


def _genome_payload(key=0):
    """Minimal dual genome JSON for DB tests."""
    return {
        "key": key,
        "visual": {"key": key, "fitness": None, "nodes": {}, "connections": {}},
        "time_signal": {"key": key, "fitness": None, "nodes": {}, "connections": {}},
    }


def test_init_creates_tables(db_path):
    """init_genealogy_db creates populations and individuals tables."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        # Already inited by fixture; call again is idempotent
        genealogy_db_module.init_genealogy_db()
        stats = genealogy_db_module.get_stats()
    assert stats["total_populations"] == 0
    assert stats["total_individuals"] == 0


def test_save_population_returns_ids(db_path):
    """save_population returns population_id and individual_ids."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        result = genealogy_db_module.save_population(
            genomes=[_genome_payload(0), _genome_payload(1)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
    assert "error" not in result
    assert result["population_id"] == 1
    assert result["individual_ids"] == [1, 2]
    assert result["generation_num"] == 0


def test_save_population_parent_not_found(db_path):
    """save_population with invalid parent_id returns error dict."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        result = genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=999,
            generation_num=1,
        )
    assert result.get("error") == "parent_not_found"


def test_save_population_generation_mismatch(db_path):
    """save_population with wrong generation_num returns error dict."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        result = genealogy_db_module.save_population(
            genomes=[_genome_payload(1)],
            parent_id=1,
            generation_num=5,
            branch_name="main",
        )
    assert result.get("error") == "generation_mismatch"
    assert result.get("parent_generation_num") == 0


def test_get_population_roundtrip(db_path):
    """After save_population, get_population returns same data."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(7)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
            description="test",
        )
        pop = genealogy_db_module.get_population(1)
    assert pop is not None
    assert pop["population_id"] == 1
    assert pop["generation_num"] == 0
    assert pop["branch_name"] == "main"
    assert pop["description"] == "test"
    assert len(pop["genomes"]) == 1
    assert pop["genomes"][0]["key"] == 7
    assert "clicks" in pop["genomes"][0]


def test_get_population_not_found(db_path):
    """get_population returns None for missing id."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        assert genealogy_db_module.get_population(99999) is None


def test_get_tree_nodes_and_branches(db_path):
    """get_tree_nodes and get_branches return expected shape after save."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        nodes = genealogy_db_module.get_tree_nodes()
        branches = genealogy_db_module.get_branches()
    assert len(nodes) == 1
    assert nodes[0]["id"] == 1
    assert nodes[0]["branch_name"] == "main"
    assert len(branches) == 1
    assert branches[0]["name"] == "main"
    assert branches[0]["latest_generation"] == 0
    assert branches[0]["node_count"] == 1


def test_get_stats(db_path):
    """get_stats returns aggregates."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0), _genome_payload(1)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        stats = genealogy_db_module.get_stats()
    assert stats["total_populations"] == 1
    assert stats["total_individuals"] == 2
    assert stats["total_branches"] == 1
    assert stats["max_generation"] == 0


def test_export_sizes(db_path):
    """export_sizes returns full and per-branch estimated bytes."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        sizes = genealogy_db_module.export_sizes()
    assert "full" in sizes
    assert sizes["full"]["populations"] == 1
    assert sizes["full"]["individuals"] == 1
    assert sizes["full"]["estimated_bytes"] >= 0
    assert "branches" in sizes
    assert len(sizes["branches"]) == 1


def test_export_genealogy_data_full_and_branch(db_path):
    """export_genealogy_data(branch_name=None) and with branch_name."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        full = genealogy_db_module.export_genealogy_data(branch_name=None)
        main_branch = genealogy_db_module.export_genealogy_data(branch_name="main")
        missing = genealogy_db_module.export_genealogy_data(branch_name="missing")
    assert full is not None
    assert full["branch_name"] is None
    assert len(full["populations"]) == 1
    assert len(full["individuals"]) == 1
    assert "exported_at" in full
    assert full["version"] == 1
    assert main_branch is not None
    assert main_branch["branch_name"] == "main"
    assert missing is None


def test_get_population_thumbnail(db_path):
    """get_population_thumbnail returns fittest individual or None."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        assert genealogy_db_module.get_population_thumbnail(1) is None
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
            fitness_data=[0.5],
        )
        thumb = genealogy_db_module.get_population_thumbnail(1)
    assert thumb is not None
    assert "genome" in thumb
    assert "fitness" in thumb
    assert thumb["fitness"] == 0.5


def test_reset_genealogy(db_path):
    """reset_genealogy clears all data."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        genealogy_db_module.reset_genealogy()
        assert genealogy_db_module.get_tree_nodes() == []
        assert genealogy_db_module.get_stats()["total_populations"] == 0


def test_save_breeding_result(db_path):
    """save_breeding_result inserts population and individuals."""
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        genealogy_db_module.save_population(
            genomes=[_genome_payload(0)],
            parent_id=None,
            generation_num=0,
            branch_name="main",
        )
        new_id = genealogy_db_module.save_breeding_result(
            parent_population_id=1,
            generation_num=1,
            branch_name="main",
            children=[_genome_payload(1), _genome_payload(2)],
        )
    assert new_id == 2
    with patch.object(genealogy_db_module, "GENEALOGY_DB_PATH", str(db_path)):
        pop = genealogy_db_module.get_population(2)
    assert pop is not None
    assert pop["generation_num"] == 1
    assert pop["parent_id"] == 1
    assert len(pop["genomes"]) == 2
