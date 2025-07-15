from typing import Any, Dict, List, Optional
import logging

from src.domain.model import Wallet, Address, Transaction, ID, RPC
from src.adapters.blockchain.base import Protocol
from ..traderjoe_factory import TraderJoeFactoryProtocol
from .strategies import SwapStrategy, StrategyConfig
from .path_builder import PathBuilder
from .swap_executor import SwapExecutor

logger = logging.getLogger(__name__)

class TraderJoeProtocol(Protocol):
    """TraderJoe V2.2 Router Protocol - Clean, simplified main interface."""

    def __init__(self, contract_address: Address, chain_id: ID, rpc_url: RPC, factory_address: Address):
        super().__init__(contract_address, chain_id, rpc_url)
        self.factory = TraderJoeFactoryProtocol(factory_address, chain_id, rpc_url)
        self.path_builder = PathBuilder(self.factory)
        self.swap_executor = SwapExecutor(self)

    @property
    def abi(self) -> List[Dict[str, Any]]:
        """TraderJoe V2.2 Router ABI - essential methods only."""
        return [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {
                        "components": [
                            {"internalType": "uint256[]", "name": "pairBinSteps", "type": "uint256[]"},
                            {"internalType": "enum ILBRouter.Version[]", "name": "versions", "type": "uint8[]"},
                            {"internalType": "contract IERC20[]", "name": "tokenPath", "type": "address[]"}
                        ],
                        "internalType": "struct ILBRouter.Path",
                        "name": "path",
                        "type": "tuple"
                    },
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForTokens",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                    {
                        "components": [
                            {"internalType": "uint256[]", "name": "pairBinSteps", "type": "uint256[]"},
                            {"internalType": "enum ILBRouter.Version[]", "name": "versions", "type": "uint8[]"},
                            {"internalType": "contract IERC20[]", "name": "tokenPath", "type": "address[]"}
                        ],
                        "internalType": "struct ILBRouter.Path",
                        "name": "path",
                        "type": "tuple"
                    },
                    {"internalType": "address", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactNATIVEForTokens",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint256", "name": "amountOutMinNATIVE", "type": "uint256"},
                    {
                        "components": [
                            {"internalType": "uint256[]", "name": "pairBinSteps", "type": "uint256[]"},
                            {"internalType": "enum ILBRouter.Version[]", "name": "versions", "type": "uint8[]"},
                            {"internalType": "contract IERC20[]", "name": "tokenPath", "type": "address[]"}
                        ],
                        "internalType": "struct ILBRouter.Path",
                        "name": "path",
                        "type": "tuple"
                    },
                    {"internalType": "address payable", "name": "to", "type": "address"},
                    {"internalType": "uint256", "name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForNATIVE",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getWNATIVE",
                "outputs": [{"internalType": "contract IWNATIVE", "name": "wnative", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

    @property
    def protocol_type(self) -> str:
        return "TraderJoe"

    # Customer-Friendly Strategy Methods
    async def swap_fast(
        self, token_from: str, token_to: str, amount_in: int, max_slippage_percent: float,
        to_address: Address, sender: Wallet, latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute a fast swap optimized for speed."""
        return await self._execute_strategy_swap(
            SwapStrategy.FAST, token_from, token_to, amount_in,
            max_slippage_percent, to_address, sender, latest_tx
        )

    async def swap_cheap(
        self, token_from: str, token_to: str, amount_in: int, max_slippage_percent: float,
        to_address: Address, sender: Wallet, latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute a cost-efficient swap optimized for lowest fees."""
        return await self._execute_strategy_swap(
            SwapStrategy.CHEAP, token_from, token_to, amount_in,
            max_slippage_percent, to_address, sender, latest_tx
        )

    async def swap_secure(
        self, token_from: str, token_to: str, amount_in: int, max_slippage_percent: float,
        to_address: Address, sender: Wallet, latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute a secure swap optimized for reliability and safety."""
        return await self._execute_strategy_swap(
            SwapStrategy.SECURE, token_from, token_to, amount_in,
            max_slippage_percent, to_address, sender, latest_tx
        )

    async def _execute_strategy_swap(
        self, strategy: SwapStrategy, token_from: str, token_to: str, amount_in: int,
        max_slippage_percent: float, to_address: Address, sender: Wallet, latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute swap based on strategy - consolidated logic."""
        amount_out_min = int(amount_in * (1 - max_slippage_percent / 100))
        wnative_address = await self.get_wnative_address()

        # Convert "NATIVE" to WNATIVE address
        actual_token_from = wnative_address if token_from == "NATIVE" else token_from
        actual_token_to = wnative_address if token_to == "NATIVE" else token_to

        # Build path and get optimal parameters
        token_path = await self.path_builder.build_optimal_path(
            actual_token_from, actual_token_to, strategy, wnative_address
        )
        pair_bin_steps = await self.path_builder.get_optimal_bin_steps(token_path, strategy)
        versions = [1] * (len(token_path) - 1)
        deadline = StrategyConfig.get_deadline(strategy)

        # Execute appropriate swap method
        if token_from == "NATIVE" and token_to != "NATIVE":
            return await self.swap_executor.execute_native_for_tokens(
                amount_out_min, token_path, pair_bin_steps, versions,
                deadline, to_address, sender, latest_tx, amount_in
            )
        elif token_from != "NATIVE" and token_to == "NATIVE":
            return await self.swap_executor.execute_tokens_for_native(
                amount_in, amount_out_min, token_path, pair_bin_steps,
                versions, deadline, to_address, sender, latest_tx
            )
        else:
            return await self.swap_executor.execute_tokens_for_tokens(
                amount_in, amount_out_min, token_path, pair_bin_steps,
                versions, deadline, to_address, sender, latest_tx
            )

    async def get_wnative_address(self) -> str:
        """Get the wrapped native token address."""
        await self.ensure_chain()
        wnative_address = await self.contract.functions.getWNATIVE().call()
        logger.info(f"WNATIVE address retrieved: {wnative_address}")
        return wnative_address
