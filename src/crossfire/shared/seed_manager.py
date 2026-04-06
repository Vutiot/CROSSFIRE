"""Centralized seed management for deterministic, reproducible execution."""

import hashlib

from loguru import logger


class SeedManager:
    """Derives deterministic per-component seeds from a single master seed.

    Every component obtains its seed from SeedManager — never from
    random.seed() directly. Uses hashlib for cross-session determinism.
    """

    def __init__(self, master_seed: int):
        self.master_seed = master_seed
        logger.info(f"SeedManager initialized with master_seed={master_seed}")

    def get_seed(self, component: str, index: int = 0) -> int:
        """Return a deterministic seed derived from master_seed, component name, and index."""
        key = f"{self.master_seed}:{component}:{index}"
        return int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
