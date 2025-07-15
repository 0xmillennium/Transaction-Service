from typing import Any, Dict, List, Optional, Tuple
import logging

from src.adapters.blockchain.base import Protocol

logger = logging.getLogger(__name__)

class TraderJoeFactoryProtocol(Protocol):
    """TraderJoe V2.2 Factory Protocol Implementation for pair information and management."""

    @property
    def abi(self) -> List[Dict[str, Any]]:
        """TraderJoe V2.2 Factory ABI focused on pair information."""
        return [
            {
                "inputs": [
                    {"internalType": "contract IERC20", "name": "tokenA", "type": "address"},
                    {"internalType": "contract IERC20", "name": "tokenB", "type": "address"},
                    {"internalType": "uint256", "name": "binStep", "type": "uint256"}
                ],
                "name": "getLBPairInformation",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint16", "name": "binStep", "type": "uint16"},
                            {"internalType": "contract ILBPair", "name": "LBPair", "type": "address"},
                            {"internalType": "bool", "name": "createdByOwner", "type": "bool"},
                            {"internalType": "bool", "name": "ignoredForRouting", "type": "bool"}
                        ],
                        "internalType": "struct ILBFactory.LBPairInformation",
                        "name": "lbPairInformation",
                        "type": "tuple"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "contract IERC20", "name": "tokenX", "type": "address"},
                    {"internalType": "contract IERC20", "name": "tokenY", "type": "address"}
                ],
                "name": "getAllLBPairs",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint16", "name": "binStep", "type": "uint16"},
                            {"internalType": "contract ILBPair", "name": "LBPair", "type": "address"},
                            {"internalType": "bool", "name": "createdByOwner", "type": "bool"},
                            {"internalType": "bool", "name": "ignoredForRouting", "type": "bool"}
                        ],
                        "internalType": "struct ILBFactory.LBPairInformation[]",
                        "name": "lbPairsAvailable",
                        "type": "tuple[]"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getAllBinSteps",
                "outputs": [
                    {"internalType": "uint256[]", "name": "binStepWithPreset", "type": "uint256[]"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getOpenBinSteps",
                "outputs": [
                    {"internalType": "uint256[]", "name": "openBinStep", "type": "uint256[]"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "binStep", "type": "uint256"}
                ],
                "name": "getPreset",
                "outputs": [
                    {"internalType": "uint256", "name": "baseFactor", "type": "uint256"},
                    {"internalType": "uint256", "name": "filterPeriod", "type": "uint256"},
                    {"internalType": "uint256", "name": "decayPeriod", "type": "uint256"},
                    {"internalType": "uint256", "name": "reductionFactor", "type": "uint256"},
                    {"internalType": "uint256", "name": "variableFeeControl", "type": "uint256"},
                    {"internalType": "uint256", "name": "protocolShare", "type": "uint256"},
                    {"internalType": "uint256", "name": "maxVolatilityAccumulator", "type": "uint256"},
                    {"internalType": "bool", "name": "isOpen", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "contract IERC20", "name": "token", "type": "address"}
                ],
                "name": "isQuoteAsset",
                "outputs": [
                    {"internalType": "bool", "name": "isQuote", "type": "bool"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getNumberOfLBPairs",
                "outputs": [
                    {"internalType": "uint256", "name": "lbPairNumber", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    @property
    def protocol_type(self) -> str:
        return "TraderJoeFactory"

    async def get_pair_information(
        self,
        token_a: str,
        token_b: str,
        bin_step: int = 25
    ) -> Tuple[int, str, bool, bool]:
        """Get information about a specific LB pair.

        Args:
            token_a (str): First token address
            token_b (str): Second token address
            bin_step (int): Bin step for the pair (default: 25)

        Returns:
            Tuple[int, str, bool, bool]: (binStep, pairAddress, createdByOwner, ignoredForRouting)
        """
        await self.ensure_chain()

        pair_info = await self.contract.functions.getLBPairInformation(
            token_a, token_b, bin_step
        ).call()

        logger.info(f"Pair info retrieved for {token_a}/{token_b} with bin step {bin_step}")
        return pair_info

    async def pair_exists(self, token_a: str, token_b: str, bin_step: int = 25) -> bool:
        """Check if a trading pair exists between two tokens.

        Args:
            token_a (str): First token address
            token_b (str): Second token address
            bin_step (int): Bin step for the pair (default: 25)

        Returns:
            bool: True if pair exists and is not ignored for routing
        """
        try:
            pair_info = await self.get_pair_information(token_a, token_b, bin_step)

            # Check if pair exists (non-zero address) and is not ignored for routing
            pair_exists = (pair_info[1] != "0x0000000000000000000000000000000000000000" and
                          not pair_info[3])  # not ignoredForRouting

            logger.info(f"Pair existence check for {token_a}/{token_b}: {pair_exists}")
            return pair_exists

        except Exception as e:
            logger.warning(f"Could not check pair existence for {token_a}/{token_b}: {str(e)}")
            return False

    async def get_all_pairs_for_tokens(self, token_a: str, token_b: str) -> List[Tuple[int, str, bool, bool]]:
        """Get all available pairs between two tokens.

        Args:
            token_a (str): First token address
            token_b (str): Second token address

        Returns:
            List[Tuple[int, str, bool, bool]]: List of (binStep, pairAddress, createdByOwner, ignoredForRouting)
        """
        await self.ensure_chain()

        all_pairs = await self.contract.functions.getAllLBPairs(token_a, token_b).call()
        logger.info(f"Retrieved {len(all_pairs)} pairs for {token_a}/{token_b}")

        return all_pairs

    async def get_best_pair_for_tokens(self, token_a: str, token_b: str) -> Optional[Tuple[int, str]]:
        """Get the best available pair between two tokens (lowest bin step, not ignored).

        Args:
            token_a (str): First token address
            token_b (str): Second token address

        Returns:
            Optional[Tuple[int, str]]: (binStep, pairAddress) or None if no suitable pair found
        """
        try:
            all_pairs = await self.get_all_pairs_for_tokens(token_a, token_b)

            # Filter out ignored pairs and sort by bin step (lower is better for most cases)
            suitable_pairs = [
                (pair[0], pair[1]) for pair in all_pairs
                if not pair[3] and pair[1] != "0x0000000000000000000000000000000000000000"
            ]

            if not suitable_pairs:
                return None

            # Return the pair with the lowest bin step
            best_pair = min(suitable_pairs, key=lambda x: x[0])
            logger.info(f"Best pair for {token_a}/{token_b}: bin step {best_pair[0]}")

            return best_pair

        except Exception as e:
            logger.warning(f"Could not find best pair for {token_a}/{token_b}: {str(e)}")
            return None

    async def get_available_bin_steps(self) -> List[int]:
        """Get all available bin steps with presets.

        Returns:
            List[int]: List of available bin steps
        """
        await self.ensure_chain()

        bin_steps = await self.contract.functions.getAllBinSteps().call()
        logger.info(f"Available bin steps: {bin_steps}")

        return bin_steps

    async def get_open_bin_steps(self) -> List[int]:
        """Get bin steps that are open for public use.

        Returns:
            List[int]: List of open bin steps
        """
        await self.ensure_chain()

        open_bin_steps = await self.contract.functions.getOpenBinSteps().call()
        logger.info(f"Open bin steps: {open_bin_steps}")

        return open_bin_steps

    async def is_quote_asset(self, token: str) -> bool:
        """Check if a token is a whitelisted quote asset.

        Args:
            token (str): Token address to check

        Returns:
            bool: True if token is a quote asset
        """
        await self.ensure_chain()

        is_quote = await self.contract.functions.isQuoteAsset(token).call()
        logger.info(f"Quote asset check for {token}: {is_quote}")

        return is_quote

    async def get_preset_info(self, bin_step: int) -> Optional[Dict[str, Any]]:
        """Get preset information for a specific bin step.

        Args:
            bin_step (int): Bin step to get preset for

        Returns:
            Optional[Dict[str, Any]]: Preset information or None if not found
        """
        try:
            await self.ensure_chain()

            preset_info = await self.contract.functions.getPreset(bin_step).call()

            preset_dict = {
                'baseFactor': preset_info[0],
                'filterPeriod': preset_info[1],
                'decayPeriod': preset_info[2],
                'reductionFactor': preset_info[3],
                'variableFeeControl': preset_info[4],
                'protocolShare': preset_info[5],
                'maxVolatilityAccumulator': preset_info[6],
                'isOpen': preset_info[7]
            }

            logger.info(f"Preset info for bin step {bin_step}: {preset_dict}")
            return preset_dict

        except Exception as e:
            logger.warning(f"Could not get preset info for bin step {bin_step}: {str(e)}")
            return None
