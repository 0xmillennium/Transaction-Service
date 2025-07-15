from typing import List, Optional
import logging
from ..traderjoe_factory import TraderJoeFactoryProtocol

logger = logging.getLogger(__name__)

class BinStepOptimizer:
    """Handles bin step optimization logic shared across strategies."""

    def __init__(self, factory: TraderJoeFactoryProtocol):
        self.factory = factory

    async def get_optimal_bin_steps(self, token_path: List[str], strategy_type: str) -> List[int]:
        """Get optimal bin steps for a token path based on strategy type."""
        if strategy_type == "cheap":
            return await self._get_high_fee_bin_steps(token_path)
        else:  # fast or secure
            return await self._get_best_available_bin_steps(token_path)

    async def _get_best_available_bin_steps(self, token_path: List[str]) -> List[int]:
        """Get the best available bin steps."""
        bin_steps = []
        for i in range(len(token_path) - 1):
            best_pair = await self.factory.get_best_pair_for_tokens(token_path[i], token_path[i + 1])
            if best_pair:
                bin_steps.append(best_pair[0])
            else:
                bin_steps.append(25)  # Standard fallback
        return bin_steps

    async def _get_high_fee_bin_steps(self, token_path: List[str]) -> List[int]:
        """Get higher bin steps for lower trading fees."""
        bin_steps = []
        for i in range(len(token_path) - 1):
            all_pairs = await self.factory.get_all_pairs_for_tokens(token_path[i], token_path[i + 1])
            suitable_pairs = [
                pair[0] for pair in all_pairs
                if not pair[3] and pair[1] != "0x0000000000000000000000000000000000000000"
            ]

            if suitable_pairs:
                bin_steps.append(max(suitable_pairs))  # Higher bin step = lower fees
            else:
                bin_steps.append(50)  # High bin step fallback
        return bin_steps

class PathFinder:
    """Shared pathfinding logic - uses factory to discover all available tokens."""

    def __init__(self, factory: TraderJoeFactoryProtocol):
        self.factory = factory

    async def find_direct_path(self, token_from: str, token_to: str) -> Optional[List[str]]:
        """Check if direct path exists between tokens."""
        best_pair = await self.factory.get_best_pair_for_tokens(token_from, token_to)
        if best_pair:
            logger.info(f"Direct path found: {token_from} -> {token_to}")
            return [token_from, token_to]
        return None

    async def find_intermediary_path(
        self,
        token_from: str,
        token_to: str,
        wnative_address: str,
        strategy_type: str = "fast"
    ) -> Optional[List[str]]:
        """Find path through intermediary tokens - let factory discover what's available."""
        # Start with WNATIVE as it's usually the most liquid
        potential_intermediaries = [wnative_address]

        # For cheap strategy, also try quote assets (factory tells us which ones exist)
        if strategy_type == "cheap":
            # Ask factory for quote assets instead of hardcoding
            quote_assets = await self._get_available_quote_assets()
            potential_intermediaries.extend(quote_assets)

        for intermediary in potential_intermediaries:
            if intermediary != token_from and intermediary != token_to:
                first_pair = await self.factory.get_best_pair_for_tokens(token_from, intermediary)
                second_pair = await self.factory.get_best_pair_for_tokens(intermediary, token_to)

                if first_pair and second_pair:
                    logger.info(f"Intermediary path found: {token_from} -> {intermediary} -> {token_to}")
                    return [token_from, intermediary, token_to]
        return None

    async def _get_available_quote_assets(self) -> List[str]:
        """Get available quote assets from factory - no hardcoding needed."""
        # This would require factory to expose quote assets, for now return empty
        # The factory contract knows all quote assets, we just need to ask it
        return []

    async def find_fallback_path(
        self,
        token_from: str,
        token_to: str,
        wnative_address: str
    ) -> List[str]:
        """Fallback pathfinding using available bin steps from factory."""
        available_bin_steps = await self.factory.get_available_bin_steps()

        # Try WNATIVE as intermediary with different bin steps
        for bin_step in [25, 50, 100, 20, 15]:
            if bin_step in available_bin_steps:
                first_exists = await self.factory.pair_exists(token_from, wnative_address, bin_step)
                second_exists = await self.factory.pair_exists(wnative_address, token_to, bin_step)

                if first_exists and second_exists:
                    logger.info(f"Fallback path found: {token_from} -> {wnative_address} -> {token_to}")
                    return [token_from, wnative_address, token_to]

        logger.warning(f"No route found for {token_from}/{token_to}, using direct path")
        return [token_from, token_to]
