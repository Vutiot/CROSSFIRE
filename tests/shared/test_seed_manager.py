"""Tests for SeedManager determinism and correctness."""

import io

from loguru import logger

from crossfire.shared.seed_manager import SeedManager


class TestSeedManagerDeterminism:
    def test_same_seed_same_component_same_result(self):
        sm1 = SeedManager(42)
        sm2 = SeedManager(42)
        assert sm1.get_seed("generator", 0) == sm2.get_seed("generator", 0)

    def test_determinism_across_many_instantiations(self):
        seeds = [SeedManager(42).get_seed("pipeline", 3) for _ in range(100)]
        assert len(set(seeds)) == 1

    def test_different_components_different_seeds(self):
        sm = SeedManager(42)
        components = ["generator", "pipeline", "evaluation", "injector", "distractor"]
        seeds = [sm.get_seed(c) for c in components]
        assert len(set(seeds)) == len(components), "Component seeds must not collide"

    def test_different_indices_different_seeds(self):
        sm = SeedManager(42)
        seeds = [sm.get_seed("generator", i) for i in range(10)]
        assert len(set(seeds)) == 10, "Different indices must produce different seeds"

    def test_different_master_seeds_different_results(self):
        sm1 = SeedManager(42)
        sm2 = SeedManager(99)
        assert sm1.get_seed("generator", 0) != sm2.get_seed("generator", 0)


class TestSeedManagerEdgeCases:
    def test_index_defaults_to_zero(self):
        sm = SeedManager(42)
        assert sm.get_seed("generator") == sm.get_seed("generator", 0)

    def test_seed_within_32bit_range(self):
        sm = SeedManager(42)
        for component in ["generator", "pipeline", "evaluation"]:
            for i in range(20):
                seed = sm.get_seed(component, i)
                assert 0 <= seed < 2**32, f"Seed {seed} out of 32-bit range"

    def test_master_seed_stored(self):
        sm = SeedManager(12345)
        assert sm.master_seed == 12345


class TestSeedManagerLogging:
    def test_info_log_at_initialization(self):
        sink = io.StringIO()
        handler_id = logger.add(sink, format="{message}", level="INFO")
        try:
            SeedManager(42)
            output = sink.getvalue()
            assert "SeedManager initialized with master_seed=42" in output
        finally:
            logger.remove(handler_id)


class TestSeedManagerImport:
    def test_importable(self):
        from crossfire.shared.seed_manager import SeedManager as SM
        assert SM is SeedManager
