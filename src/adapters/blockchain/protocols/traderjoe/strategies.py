from enum import Enum

class SwapStrategy(Enum):
    """Swap strategy types based on customer priorities."""
    FAST = "fast"
    CHEAP = "cheap"
    SECURE = "secure"

class StrategyConfig:
    """Configuration for different swap strategies."""

    @staticmethod
    def get_deadline(strategy: SwapStrategy) -> int:
        """Get deadline in seconds based on strategy."""
        import time
        base_time = int(time.time())

        return base_time + (1200 if strategy == SwapStrategy.FAST else 1800)
