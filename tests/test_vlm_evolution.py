"""
Tests for VLM-based evolution system.
Tests core functionality without requiring CLIP model.
"""
import numpy as np
import pytest
import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asal_metrics import (
    calc_open_endedness_score,
    calc_illumination_score,
    calc_interestingness_score,
    select_top_k,
)
from cppn_engine import CPPNEngine, create_random_dual_genome
from rollout import (
    render_video_rollout,
    rollout_population,
    RolloutResult,
)


class TestASALMetrics:
    """Tests for ASAL metrics."""

    def test_open_endedness_identical_frames(self):
        """Identical frames should have high (bad) open-endedness score."""
        # All identical embeddings -> high similarity -> high score
        T, D = 10, 512
        z = np.ones((T, D)) / np.sqrt(D)  # Unit vectors
        score = calc_open_endedness_score(z)

        # Should be close to 1 (high similarity to previous frames)
        assert score > 0.9

    def test_open_endedness_diverse_frames(self):
        """Diverse frames should have low (good) open-endedness score."""
        # Orthogonal embeddings -> zero similarity -> low score
        T, D = 10, 512
        z = np.eye(T, D)  # Orthogonal vectors
        # Normalize
        z = z / np.linalg.norm(z, axis=-1, keepdims=True)
        score = calc_open_endedness_score(z)

        # Should be close to 0 (low similarity to previous frames)
        assert score < 0.1

    def test_open_endedness_shape(self):
        """Test that open-endedness works with different shapes."""
        for T in [5, 10, 20]:
            z = np.random.randn(T, 512)
            z = z / np.linalg.norm(z, axis=-1, keepdims=True)
            score = calc_open_endedness_score(z)
            assert 0 <= score <= 1

    def test_illumination_score_identical(self):
        """Identical individuals should have high illumination score."""
        N, D = 5, 512
        zs = np.ones((N, D)) / np.sqrt(D)
        score = calc_illumination_score(zs)
        assert score > 0.9

    def test_illumination_score_diverse(self):
        """Diverse individuals should have low illumination score."""
        N, D = 5, 512
        zs = np.eye(N, D)
        zs = zs / np.linalg.norm(zs, axis=-1, keepdims=True)
        score = calc_illumination_score(zs)
        assert score < 0.1

    def test_interestingness_score(self):
        """Test combined interestingness score."""
        T, D = 10, 512
        z = np.random.randn(T, D)
        z = z / np.linalg.norm(z, axis=-1, keepdims=True)
        score = calc_interestingness_score(z)
        assert isinstance(score, float)


class TestSelectTopK:
    """Tests for selection function."""

    def test_select_top_k_deterministic(self):
        """Test deterministic selection (temperature=0)."""
        scores = np.array([0.5, 0.1, 0.3, 0.9, 0.2])  # Lower is better
        selected = select_top_k(scores, k=3, temperature=0.0, lower_is_better=True)

        # Should select indices 1, 4, 2 (scores 0.1, 0.2, 0.3)
        assert len(selected) == 3
        assert 1 in selected  # Score 0.1 (best)
        assert 4 in selected  # Score 0.2
        assert 2 in selected  # Score 0.3

    def test_select_top_k_stochastic(self):
        """Test stochastic selection (temperature > 0)."""
        scores = np.array([0.5, 0.1, 0.3, 0.9, 0.2])
        np.random.seed(42)
        selected = select_top_k(scores, k=3, temperature=0.5, lower_is_better=True)

        # Should still generally select from top candidates
        assert len(selected) == 3
        # Best candidate (index 1) should still likely be selected
        # but we can't guarantee due to randomness

    def test_select_top_k_higher_is_better(self):
        """Test selection when higher scores are better."""
        scores = np.array([0.5, 0.1, 0.3, 0.9, 0.2])
        selected = select_top_k(scores, k=3, temperature=0.0, lower_is_better=False)

        # Should select indices 3, 0, 2 (scores 0.9, 0.5, 0.3)
        assert len(selected) == 3
        assert 3 in selected  # Score 0.9 (best)


class TestRollout:
    """Tests for video rollout functionality."""

    def test_render_video_rollout(self):
        """Test rendering video rollout for a genome."""
        engine = CPPNEngine()
        engine.create_population()
        genome = create_random_dual_genome(engine, 0)

        frames = render_video_rollout(
            engine,
            genome,
            num_frames=5,
            resolution=64,
        )

        assert frames.shape == (5, 64, 64, 3)
        assert frames.dtype == np.uint8
        assert frames.min() >= 0
        assert frames.max() <= 255

    def test_rollout_population(self):
        """Test rolling out an entire population (without embedder)."""
        engine = CPPNEngine()
        engine.create_population()

        population = [create_random_dual_genome(engine, i) for i in range(3)]

        results = rollout_population(
            engine,
            population,
            embedder=None,  # No CLIP
            num_frames=5,
            resolution=64,
        )

        assert len(results) == 3
        for result in results:
            assert isinstance(result, RolloutResult)
            assert result.frames.shape == (5, 64, 64, 3)
            assert result.embeddings is None  # No embedder


class TestVLMEvolutionComponents:
    """Tests for VLM evolution components (without CLIP)."""

    def test_evolution_config(self):
        """Test EvolutionConfig defaults."""
        from vlm_evolution import EvolutionConfig

        config = EvolutionConfig()
        assert config.population_size == 12
        assert config.num_generations == 20
        assert config.top_k == 3

    def test_initialize_population(self):
        """Test population initialization."""
        from vlm_evolution import VLMEvolution, EvolutionConfig

        config = EvolutionConfig(population_size=5)
        evolution = VLMEvolution(config)
        evolution.initialize_population()

        assert len(evolution.population) == 5
        assert evolution.generation == 0

    def test_breed_next_generation(self):
        """Test breeding without CLIP (using mock scores)."""
        from vlm_evolution import VLMEvolution, EvolutionConfig

        config = EvolutionConfig(population_size=5, top_k=2)
        evolution = VLMEvolution(config)
        evolution.initialize_population()

        # Mock selection
        selected_indices = np.array([0, 1])

        new_pop = evolution.breed_next_generation(selected_indices)

        assert len(new_pop) == 5


class TestMockCLIPEvolution:
    """Test full evolution with a mock CLIP embedder."""

    class MockEmbedder:
        """Mock embedder that returns random embeddings."""

        def embed_images(self, images):
            n = len(images)
            embeddings = np.random.randn(n, 512)
            embeddings = embeddings / np.linalg.norm(embeddings, axis=-1, keepdims=True)
            return embeddings

    def test_evolution_with_mock_embedder(self):
        """Test evolution loop with mock embedder."""
        from vlm_evolution import VLMEvolution, EvolutionConfig

        with tempfile.TemporaryDirectory() as tmpdir:
            config = EvolutionConfig(
                population_size=4,
                num_generations=2,
                top_k=2,
                num_frames=4,
                resolution=32,
                output_dir=tmpdir,
            )

            evolution = VLMEvolution(config)
            evolution._embedder = self.MockEmbedder()
            evolution.initialize_population()

            # Run one generation
            result = evolution.run_generation()

            assert result.generation == 0
            assert len(result.scores) == 4
            assert len(result.selected_indices) == 2
            assert evolution.generation == 1

            # Run another
            result2 = evolution.run_generation()
            assert result2.generation == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
