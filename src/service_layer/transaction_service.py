"""
Transaction Service for handling complex transaction workflows.

This service manages the complete transaction lifecycle including gas estimation,
broadcasting, and status tracking.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.model import Transaction, Swap, Token, Wallet
from src.service_layer.unit_of_work import AbstractUnitOfWork
from src.service_layer.blockchain_service import BlockchainService
from src.adapters.blockchain.abstract import AbstractBlockchainAdapter

logger = logging.getLogger(__name__)


class TransactionService:
    """
    Service for managing transaction operations and workflows.

    Handles the complete transaction lifecycle from creation to confirmation.
    """

    def __init__(self, uow: AbstractUnitOfWork, blockchain_adapter: AbstractBlockchainAdapter):
        self.uow = uow
        self.blockchain_adapter = blockchain_adapter
        self.blockchain_service = BlockchainService(blockchain_adapter)

    async def create_swap_transaction(
        self,
        userid: str,
        token_in_id: str,
        token_out_id: str,
        amount_in: str,
        slippage_tolerance: str,
        deadline_minutes: int = 20,
        network: str = "avalanche"
    ) -> str:
        """
        Create a new swap transaction using the user's wallet.

        Args:
            userid: User ID creating the transaction
            token_in_id: Input token ID
            token_out_id: Output token ID
            amount_in: Amount to swap
            slippage_tolerance: Slippage tolerance percentage
            deadline_minutes: Transaction deadline in minutes
            network: Network to execute on

        Returns:
            str: Transaction ID

        Raises:
            ValueError: If validation fails
        """
        with self.uow:
            # Get user's wallet
            wallet = self.uow.repo.get_user_wallet(userid)
            if not wallet:
                raise ValueError(f"User {userid} does not have a wallet. Please create a wallet first.")

            if not wallet.is_active:
                raise ValueError("User's wallet is deactivated. Please activate the wallet first.")

            # Validate tokens exist
            token_in = self.uow.repo.get_token(token_in_id)
            token_out = self.uow.repo.get_token(token_out_id)

            if not token_in or not token_out:
                raise ValueError("Invalid token(s)")

            # Validate tokens are on the correct network
            if token_in.network != network or token_out.network != network:
                raise ValueError(f"Tokens must be on the {network} network for this swap")

            # Get swap quote
            token_in_address, token_out_address = self.blockchain_service.get_token_addresses(
                token_in, token_out
            )

            quote = await self.blockchain_service.get_swap_quote_with_addresses(
                token_in_address, token_out_address, amount_in, slippage_tolerance
            )

            # Create transaction and swap entities
            deadline = self.blockchain_service.calculate_deadline(deadline_minutes)
            transaction, swap = self._create_transaction_and_swap_entities(
                userid, wallet.wallet_id.value, token_in_id, token_out_id,
                amount_in, str(quote.amount_out), slippage_tolerance, deadline, network
            )

            # Estimate gas
            transaction_data = await self.blockchain_service.build_transaction_data(
                wallet.address.value,
                token_in_address,
                token_out_address,
                int(amount_in),
                quote.minimum_amount_out,
                int(deadline.timestamp())
            )

            await self.blockchain_service.estimate_and_set_gas(transaction, transaction_data)

            # Save entities
            self.uow.repo.add_transaction(transaction)
            self.uow.repo.add_swap(swap)
            self.uow.commit()

            logger.info(f"Swap transaction created for user {userid}: {transaction.transaction_id.value}")
            return transaction.transaction_id.value

    async def estimate_gas(self, transaction_id: str) -> None:
        """
        Estimate gas for a pending transaction.

        Args:
            transaction_id: Transaction ID to estimate gas for

        Raises:
            ValueError: If transaction or related entities not found
        """
        with self.uow:
            transaction = self.uow.repo.get_transaction(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")

            swap = self.uow.repo.get_swap_by_transaction(transaction_id)
            if not swap:
                raise ValueError(f"No swap found for transaction {transaction_id}")

            # Get required entities
            wallet = self.uow.repo.get_wallet(transaction.wallet_id.value)
            token_in = self.uow.repo.get_token(swap.token_in_id.value)
            token_out = self.uow.repo.get_token(swap.token_out_id.value)

            if not wallet or not token_in or not token_out:
                raise ValueError("Required entities not found")

            # Build transaction data and estimate gas
            token_in_address, token_out_address = self.blockchain_service.get_token_addresses(token_in, token_out)

            transaction_data = await self.blockchain_service.build_transaction_data(
                wallet.address.value,
                token_in_address,
                token_out_address,
                int(swap.amount_in.value),
                int(swap.amount_out_expected.value),
                int(swap.deadline.timestamp())
            )

            await self.blockchain_service.estimate_and_set_gas(transaction, transaction_data)
            self.uow.commit()

            logger.info(f"Gas estimated for transaction {transaction_id}")

    async def broadcast_transaction(self, transaction_id: str) -> str:
        """
        Broadcast a transaction to the blockchain.

        Args:
            transaction_id: Transaction ID to broadcast

        Returns:
            str: Transaction hash

        Raises:
            ValueError: If transaction or related entities not found
        """
        with self.uow:
            # Validate and get entities
            transaction = self.uow.repo.get_transaction(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")

            wallet = self.uow.repo.get_wallet(transaction.wallet_id.value)
            if not wallet:
                raise ValueError("Wallet not found for transaction")

            swap = self.uow.repo.get_swap_by_transaction(transaction_id)
            if not swap:
                raise ValueError(f"No swap found for transaction {transaction_id}")

            # Get tokens and build transaction
            token_in = self.uow.repo.get_token(swap.token_in_id.value)
            token_out = self.uow.repo.get_token(swap.token_out_id.value)

            if not token_in or not token_out:
                raise ValueError("Required tokens not found")

            token_in_address, token_out_address = self.blockchain_service.get_token_addresses(token_in, token_out)

            transaction_data = await self.blockchain_service.build_transaction_data(
                wallet.address.value,
                token_in_address,
                token_out_address,
                int(swap.amount_in.value),
                int(swap.amount_out_expected.value),
                int(swap.deadline.timestamp())
            )

            # Add gas information and send transaction
            transaction_data = self.blockchain_service.add_gas_to_transaction_data(
                transaction_data, transaction
            )

            tx_hash = await self.blockchain_adapter.send_transaction(
                from_address=wallet.address.value,
                private_key=wallet.private_key_encrypted.value,
                transaction_data=transaction_data
            )

            # Update transaction status using domain method
            transaction.broadcast(tx_hash, "0")
            self.uow.commit()

            logger.info(f"Transaction {transaction_id} broadcasted with hash {tx_hash}")
            return tx_hash

    async def update_transaction_status(
        self,
        transaction_id: str,
        transaction_hash: str,
        status: str,
        block_number: Optional[str] = None,
        gas_used: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update transaction status from external sources.

        Args:
            transaction_id: Transaction ID to update
            transaction_hash: Transaction hash
            status: New status
            block_number: Block number (for confirmed transactions)
            gas_used: Gas used (for confirmed transactions)
            error_message: Error message (for failed transactions)
        """
        with self.uow:
            transaction = self.uow.repo.get_transaction(transaction_id)
            if not transaction:
                raise ValueError(f"Transaction {transaction_id} not found")

            if status == "CONFIRMED" and block_number and gas_used:
                transaction.confirm(block_number, gas_used)
            elif status == "FAILED" and error_message:
                transaction.fail(error_message)

            self.uow.commit()
            logger.info(f"Transaction {transaction_id} status updated to {status}")

    def _create_transaction_and_swap_entities(
        self,
        userid: str,
        wallet_id: str,
        token_in_id: str,
        token_out_id: str,
        amount_in: str,
        amount_out_expected: str,
        slippage_tolerance: str,
        deadline: datetime,
        network: str
    ) -> tuple[Transaction, Swap]:
        """
        Create transaction and swap entities.

        Internal helper method to create related entities.
        """
        transaction = Transaction.create(
            transaction_id=uuid4().hex,
            userid=userid,
            wallet_id=wallet_id,
            transaction_type="SWAP",
            network=network
        )

        swap = Swap.create(
            swap_id=uuid4().hex,
            transaction_id=transaction.transaction_id.value,
            token_in_id=token_in_id,
            token_out_id=token_out_id,
            amount_in=amount_in,
            amount_out_expected=amount_out_expected,
            slippage_tolerance=slippage_tolerance,
            trader_joe_router="0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
            deadline=deadline
        )

        return transaction, swap
