"""
Helper services for blockchain operations.

This module provides reusable blockchain-related functionality,
following DRY and Single Responsibility principles.
"""

import logging
from typing import Optional, Tuple, List, Union, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from src.domain.model import Token, Chain, ID
from src.core.exceptions.exceptions import BlockchainError
from src.service_layer.unit_of_work import AbstractUnitOfWork

logger = logging.getLogger(__name__)


class BlockchainService:
    """
    Service for blockchain-related operations.

    Encapsulates blockchain interaction logic to reduce complexity in handlers.
    Follows Single Responsibility Principle.
    """

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def add_chain(
        self,
        chain_id: str,
        name: str,
        symbol: str,
        rpc_url: str
    ):
        """
        Add a new blockchain chain to the system.

        Args:
            chain_id: Unique identifier for the chain (e.g., "avax")
            name: Full name of the chain (e.g., "Avalanche")
            symbol: Symbol for the native token (e.g., "AVAX")
            rpc_url: RPC URL for interacting with the chain

        Returns:
            None
        """
        async with self.uow:
            # Validate chain doesn't already exist
            existing_chain = await self.uow.repo.get_chain(chain_id)
            if existing_chain:
                raise ValueError(f"Chain {chain_id} already exists")

            # Create and save new chain
            new_chain = Chain.create(
                chain_id=chain_id,
                name=name,
                symbol=symbol,
                rpc_url=rpc_url,
            )
            self.uow.repo.add_chain(new_chain)

    async def get_chain(self, chain_id: Union[ID, str]) -> Dict[str, Any]:
        """
        Get a blockchain chain by its ID.

        Args:
            chain_id: Unique identifier for the chain (e.g., "41155")

        Returns:
            Optional[Chain]: Chain object if found, None otherwise
        """
        async with self.uow:
            chain = await self.uow.repo.get_chain(chain_id)
            return {
                    "chain_id": chain.chain_id,
                    "name": chain.name,
                    "symbol": chain.symbol,
                    "rpc_url": chain.rpc_url
                }

    async def get_chain_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get a blockchain chain by its symbol.

        Args:
            symbol: Symbol of the chain (e.g., "AVAX")

        Returns:
            Optional[Chain]: Chain object if found, None otherwise
        """
        async with self.uow:
            chain = await self.uow.repo.get_chain_by_symbol(symbol)
            return {
                "chain_id": chain.chain_id.value,
                "name": chain.name.value,
                "symbol": chain.symbol.value,
                "rpc_url": chain.rpc_url.value
            }

    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """
        Get all supported blockchain chains.

        Returns:
            List[Chain]: List of supported chains
        """
        async with self.uow:
            chains = await self.uow.repo.get_supported_chains()
            return [
                {
                    "chain_id": chain.chain_id.value,
                    "name": chain.name.value,
                    "symbol": chain.symbol.value,
                    "rpc_url": chain.rpc_url.value
                } for chain in chains
            ]
