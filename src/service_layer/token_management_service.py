"""
Token Management Service for TraderJoe operations.

This service handles adding, updating, and managing supported tokens
on the Avalanche network for TraderJoe swaps.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.model import Token
from src.service_layer.unit_of_work import AbstractUnitOfWork
from src.service_layer.validation import TokenValidationService

logger = logging.getLogger(__name__)


class TokenManagementService:
    """
    Service for managing supported tokens in the TraderJoe transaction service.

    Follows Single Responsibility Principle by handling only token management operations.
    """

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def add_token(
        self,
        chain_id: str,
        symbol: str,
        name: str,
        decimals: str = "18",
        contract_address: Optional[str] = None,
    ) -> str:
        """
        Add a new supported token for TraderJoe swaps.

        Args:
            chain_id: Chain ID (e.g., "avax")
            symbol: Token symbol (e.g., "USDC", "AVAX")
            name: Token full name
            decimals: Token decimals (default 18)
            contract_address: Contract address (None for native tokens)
        Returns:
            str: Token ID of the created token

        Raises:
            ValueError: If token already exists or validation fails
        """
        async with self.uow:
            # Validate token doesn't already exist
            existing_token = await self.uow.repo.get_token_by_symbol(symbol)
            TokenValidationService.validate_token_not_exists(existing_token, symbol)

            # Validate contract address for non-native tokens
            if not contract_address:
                raise ValueError("Contract address is required for non-native tokens")

            # Create token using appropriate factory method
            token = Token.create(
                token_id=uuid4().hex,
                chain_id=chain_id,
                symbol=symbol,
                name=name,
                contract_address= contract_address,
                decimals=decimals,
            )

            self.uow.repo.add_token(token)
            logger.info(f"Token {symbol} added successfully with ID {token.token_id}")
            return token.token_id

    async def get_supported_tokens(self) -> list[Dict[str, Any]]:
        """
        Get all supported tokens supported for TraderJoe swaps.

        Returns:
            List of supported tokens on Avalanche network
        """
        async with self.uow:
            tokens = await self.uow.repo.get_supported_tokens()
            return [
                {
                    "token_id": token.token_id.value,
                    "chain_id": token.chain_id.value,
                    "symbol": token.symbol.value,
                    "name": token.name.value,
                    "contract_address": token.contract_address.value if token.contract_address.value else None,
                    "decimals": token.decimals.value,
                }
                for token in tokens
            ]

    async def get_token_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get token by symbol on Avalanche network.

        Args:
            symbol: Token symbol to search for

        Returns:
            Token if found, None otherwise
        """
        async with self.uow:
            token = await self.uow.repo.get_token_by_symbol(symbol)
            return {
                "token_id": token.token_id.value,
                "chain_id": token.chain_id.value,
                "symbol": token.symbol.value,
                "name": token.name.value,
                "contract_address": token.contract_address.value if token.contract_address.value else None,
                "decimals": token.decimals.value,
            }

    async def get_token_by_contract(self, contract_address: str) -> Optional[Token]:
        """
        Get token by contract address.

        Args:
            contract_address: Contract address to search for

        Returns:
            Token if found, None otherwise
        """
        async with self.uow:
            return await self.uow.repo.get_token_by_contract(contract_address)
