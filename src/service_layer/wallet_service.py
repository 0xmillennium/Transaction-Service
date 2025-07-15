"""
Wallet Management Service for handling wallet operations.

This service encapsulates all wallet-related business logic and blockchain interactions.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from uuid import uuid4

from eth_account import Account

from src.domain.model import Wallet
from src.service_layer.unit_of_work import AbstractUnitOfWork
logger = logging.getLogger(__name__)


class WalletService:
    """
    Service for managing user wallets in the TraderJoe transaction service.

    Follows Single Responsibility Principle by handling only wallet management operations.
    """

    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def create_wallet(self, userid: str):
        """
        Create a new wallet for a user. Each user can have only ONE wallet.

        Args:
            userid: User ID to create wallet for

        Raises:
            ValueError: If user already has a wallet
        """
        async with self.uow:
            # Check if user already has a wallet
            existing_wallet = await self.uow.repo.get_wallet_by_userid(userid)
            if existing_wallet:
                raise ValueError(f"User {userid} already has a wallet. Only one wallet per user is allowed.")

            # Create wallet on blockchain
            acct = Account.create()

            # Create wallet domain entity
            wallet = Wallet.create(
                wallet_id=uuid4().hex,
                userid=userid,
                address=acct.address,
                account=acct,
                created_at=datetime.now()
            )

            self.uow.repo.add_wallet(wallet)
            await self.uow.commit()

            logger.info(f"Wallet created for user {userid}: {acct.address}")

    async def activate_wallet(self, userid: str) -> None:
        """
        Activate a user's wallet.

        Args:
            userid: User ID for ownership validation

        Raises:
            ValueError: If wallet doesn't exist or doesn't belong to user
        """
        async with self.uow:
            wallet = await self.uow.repo.get_wallet_by_userid(userid)
            if not wallet:
                raise ValueError(f"Wallet not found")

            wallet.activate()
            logger.info(f"Wallet {wallet.wallet_id} activated for user {wallet.userid}")

    async def deactivate_wallet(self, userid: str) -> None:
        """
        Deactivate a user's wallet.

        Args:
            userid: User ID for ownership validation

        Raises:
            ValueError: If wallet doesn't exist or doesn't belong to user
        """
        async with self.uow:
            wallet = await self.uow.repo.get_wallet_by_userid(userid)
            if not wallet:
                raise ValueError(f"Wallet not found")

            wallet.deactivate()
            logger.info(f"Wallet {wallet.wallet_id} deactivated for user {wallet.userid}")

    async def get_user_wallet(self, userid: str) -> Optional[Dict[str, Any]]:
        """
        Get the user's wallet (one wallet per user).

        Args:
            userid: User ID to get wallet for

        Returns:
            User's wallet if exists, None otherwise
        """
        async with self.uow:
            wallet = await self.uow.repo.get_wallet_by_userid(userid)
            if not wallet:
                return None
            return {
        "wallet_id": wallet.wallet_id.value,
        "userid": wallet.userid.value,
        "address": wallet.address.value,
        "is_active": wallet.is_active,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None
    }

    async def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """
        Get wallet by ID.

        Args:
            wallet_id: Wallet ID to retrieve

        Returns:
            Wallet if exists, None otherwise
        """
        async with self.uow:
            return await self.uow.repo.get_wallet(wallet_id)

    async def get_wallet_by_address(self, address: str) -> Optional[Wallet]:
        """
        Get wallet by address.

        Args:
            address: Wallet address to retrieve

        Returns:
            Wallet if exists, None otherwise
        """
        async with self.uow:
            return await self.uow.repo.get_wallet_by_address(address)
