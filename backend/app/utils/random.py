"""
Seedable random number generator for HideX.

All randomness in simulations must be:
- Seedable for reproducibility
- Deterministic given the same seed
- Documented for transparency
"""

import random
from typing import Optional, List, TypeVar

T = TypeVar('T')


class SeededRandom:
    """
    Seedable random number generator.
    
    Ensures deterministic simulations:
    - Same seed produces same sequence
    - Useful for testing and reproducibility
    - Required for explainable risk scoring
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize with optional seed.
        
        If seed is None, uses system randomness (non-deterministic).
        """
        self._seed = seed
        self._rng = random.Random(seed)
    
    @property
    def seed(self) -> Optional[int]:
        """Get the seed value."""
        return self._seed
    
    def reseed(self, seed: Optional[int] = None) -> None:
        """Reset with a new seed."""
        self._seed = seed
        self._rng = random.Random(seed)
    
    def random(self) -> float:
        """Get random float in [0.0, 1.0)."""
        return self._rng.random()
    
    def randint(self, a: int, b: int) -> int:
        """Get random integer in [a, b]."""
        return self._rng.randint(a, b)
    
    def uniform(self, a: float, b: float) -> float:
        """Get random float in [a, b]."""
        return self._rng.uniform(a, b)
    
    def choice(self, seq: List[T]) -> T:
        """Choose random element from sequence."""
        return self._rng.choice(seq)
    
    def shuffle(self, seq: List[T]) -> None:
        """Shuffle sequence in place."""
        self._rng.shuffle(seq)
    
    def sample(self, population: List[T], k: int) -> List[T]:
        """Return k unique elements from population."""
        return self._rng.sample(population, k)
    
    def gauss(self, mu: float, sigma: float) -> float:
        """Gaussian distribution with mean mu and std sigma."""
        return self._rng.gauss(mu, sigma)
    
    def random_delay(
        self,
        min_seconds: int,
        max_seconds: int,
        jitter_percent: float = 0.1
    ) -> int:
        """
        Generate random delay with jitter.
        
        Used for timing randomization in transaction planning.
        """
        base = self.randint(min_seconds, max_seconds)
        jitter = int(base * jitter_percent * (self.random() - 0.5) * 2)
        return max(min_seconds, base + jitter)
    
    def random_amount_variation(
        self,
        amount: int,
        variation_percent: float = 0.05
    ) -> int:
        """
        Add random variation to amount.
        
        Used to avoid exact amount matching heuristics.
        Variation is within specified percentage.
        """
        variation = int(amount * variation_percent * (self.random() - 0.5) * 2)
        return amount + variation
