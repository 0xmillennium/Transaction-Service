from typing import List
import logging
from .strategies import SwapStrategy
from .utils import BinStepOptimizer, PathFinder
from ..traderjoe_factory import TraderJoeFactoryProtocol

logger = logging.getLogger(__name__)

class PathBuilder:
    """Handles route optimization and pathfinding for token swaps."""

    def __init__(self, factory: TraderJoeFactoryProtocol):
        self.factory = factory
        self.bin_optimizer = BinStepOptimizer(factory)
        self.path_finder = PathFinder(factory)

    async def build_optimal_path(
        self,
        token_from: str,
        token_to: str,
        strategy: SwapStrategy,
        wnative_address: str
    ) -> List[str]:
        """Build optimal token path based on strategy."""
        # Try direct path first for all strategies
        direct_path = await self.path_finder.find_direct_path(token_from, token_to)
        if direct_path:
            return direct_path

        # Try intermediary path
        intermediary_path = await self.path_finder.find_intermediary_path(
            token_from, token_to, wnative_address, strategy.value
        )
        if intermediary_path:
            return intermediary_path

        # Fallback path
        return await self.path_finder.find_fallback_path(token_from, token_to, wnative_address)

    async def get_optimal_bin_steps(self, token_path: List[str], strategy: SwapStrategy) -> List[int]:
        """Get optimal bin steps for a token path based on strategy."""
        return await self.bin_optimizer.get_optimal_bin_steps(token_path, strategy.value)
