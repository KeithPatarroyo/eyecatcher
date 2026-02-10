"""Tests for genome JSON serialization round-trip."""

import pytest
from eyecatcher.evolution import (
    create_random_dual_genome,
    dual_genome_from_json,
    dual_genome_to_json,
    extract_network_data,
)


def test_dual_genome_round_trip(cppn_engine):
    """Serializing a dual genome and deserializing yields equivalent structure."""
    dual = create_random_dual_genome(
        cppn_engine.config, cppn_engine.time_config, genome_id=7
    )
    data = dual_genome_to_json(dual)
    assert "key" in data
    assert data["key"] == 7
    assert "visual" in data
    assert "time_signal" in data
    assert "nodes" in data["visual"]
    assert "connections" in data["visual"]

    restored = dual_genome_from_json(data, cppn_engine.config, cppn_engine.time_config)
    assert restored.key == dual.key
    assert len(restored.visual.nodes) == len(dual.visual.nodes)
    assert len(restored.visual.connections) == len(dual.visual.connections)
    assert len(restored.time_signal.nodes) == len(dual.time_signal.nodes)


@pytest.mark.slow
def test_dual_genome_round_trip_query_consistency(cppn_engine, random_dual_genome):
    """After round-trip, querying the CPPN gives identical output (fidelity)."""
    data = dual_genome_to_json(random_dual_genome)
    restored = dual_genome_from_json(data, cppn_engine.config, cppn_engine.time_config)

    inputs = {"x": 0.5, "y": 0.5, "raw_time": 0.3}
    r0, g0, b0 = cppn_engine.query_dual_cppn(random_dual_genome, inputs)
    r1, g1, b1 = cppn_engine.query_dual_cppn(restored, inputs)
    assert isinstance(r0, (int, float)) and isinstance(r1, (int, float))
    assert 0 <= r0 <= 255 and 0 <= r1 <= 255
    assert 0 <= g0 <= 255 and 0 <= g1 <= 255
    assert 0 <= b0 <= 255 and 0 <= b1 <= 255
    # Round-trip must preserve behavior: same inputs -> same outputs
    assert r0 == r1 and g0 == g1 and b0 == b1


def test_extract_network_data_shape(cppn_engine, minimal_dual):
    """extract_network_data returns nodes/conns with id, label, type, network."""
    config = cppn_engine.config
    time_config = cppn_engine.time_config

    visual_nodes, visual_conns = extract_network_data(
        minimal_dual.visual, "visual", config
    )
    time_nodes, time_conns = extract_network_data(
        minimal_dual.time_signal, "time", time_config
    )

    required_node_keys = {"id", "label", "type", "network"}
    required_conn_keys = {"source", "target", "weight", "network"}

    for node in visual_nodes:
        assert required_node_keys.issubset(node.keys()), node
        assert node["network"] == "visual"
    for conn in visual_conns:
        assert required_conn_keys.issubset(conn.keys()), conn
        assert conn["network"] == "visual"

    for node in time_nodes:
        assert required_node_keys.issubset(node.keys()), node
        assert node["network"] == "time"
    for conn in time_conns:
        assert required_conn_keys.issubset(conn.keys()), conn
        assert conn["network"] == "time"
