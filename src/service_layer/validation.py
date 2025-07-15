"""
Validation services for the transaction domain.

This module provides validation logic that can be reused across handlers,
following DRY principle and keeping validation logic centralized.
"""

import re
import logging
import decimal
from typing import Optional, Union
from decimal import Decimal
from src.domain.model import Wallet, Token, Transaction, Swap, Name, TokenDecimals
from src.core.exceptions.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_ethereum_address(address: str) -> None:
    """Validate Ethereum address format."""
    if not address or not isinstance(address, str):
        raise ValidationError(
            loc=["address"],
            msg="Address is required and must be a string"
        )

    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        raise ValidationError(
            loc=["address"],
            msg="Invalid Ethereum address format"
        )


def validate_transaction_amount(amount: Union[Decimal, int, float]) -> None:
    """Validate transaction amount is positive."""
    if amount is None:
        raise ValidationError(
            loc=["amount"],
            msg="Amount cannot be None"
        )

    try:
        decimal_amount = Decimal(str(amount))
    except (ValueError, TypeError, decimal.InvalidOperation):
        raise ValidationError(
            loc=["amount"],
            msg="Amount must be a valid number"
        )

    if decimal_amount <= 0:
        raise ValidationError(
            loc=["amount"],
            msg="Amount must be greater than zero"
        )


def validate_swap_parameters(
    token_in: str,
    token_out: str,
    amount_in: Union[Decimal, int, float],
    slippage_tolerance: Union[Decimal, int, float]
) -> None:
    """Validate swap parameters."""
    validate_ethereum_address(token_in)
    validate_ethereum_address(token_out)
    validate_transaction_amount(amount_in)

    if token_in == token_out:
        raise ValidationError(
            loc=["token_in", "token_out"],
            msg="Cannot swap token with itself"
        )

    if slippage_tolerance is None:
        raise ValidationError(
            loc=["slippage_tolerance"],
            msg="Slippage tolerance cannot be None"
        )

    try:
        decimal_slippage = Decimal(str(slippage_tolerance))
    except (ValueError, TypeError, decimal.InvalidOperation):
        raise ValidationError(
            loc=["slippage_tolerance"],
            msg="Slippage tolerance must be a valid number"
        )

    if decimal_slippage <= 0 or decimal_slippage > 50:
        raise ValidationError(
            loc=["slippage_tolerance"],
            msg="Slippage tolerance must be between 0 and 50 percent"
        )


def validate_wallet_network(network: str) -> None:
    """Validate wallet network is supported."""
    if not network or not isinstance(network, str):
        raise ValidationError(
            loc=["network"],
            msg="Network is required and must be a string"
        )

    supported_networks = ["avalanche", "ethereum", "polygon"]
    if network not in supported_networks:
        raise ValidationError(
            loc=["network"],
            msg=f"Network must be one of: {', '.join(supported_networks)}"
        )


def validate_gas_parameters(gas_limit: int, gas_price: int) -> None:
    """Validate gas parameters are within acceptable ranges."""
    if not isinstance(gas_limit, int) or gas_limit < 21000 or gas_limit > 10000000:
        raise ValidationError(
            loc=["gas_limit"],
            msg="Gas limit must be between 21,000 and 10,000,000"
        )

    if not isinstance(gas_price, int) or gas_price < 1000000000 or gas_price > 1000000000000:
        raise ValidationError(
            loc=["gas_price"],
            msg="Gas price must be between 1 Gwei and 1,000 Gwei"
        )


class TransactionValidationService:
    """
    Centralized validation service for transaction-related operations.

    Follows Single Responsibility Principle by handling only validation logic.
    Implements DRY by providing reusable validation methods.
    """

    @staticmethod
    def validate_wallet_ownership(wallet: Optional[Wallet], userid: str, wallet_id: str) -> Wallet:
        """
        Validate wallet exists and belongs to user.

        Args:
            wallet: Wallet entity or None
            userid: Expected owner user ID
            wallet_id: Wallet ID for error messages

        Returns:
            Wallet: Validated wallet entity

        Raises:
            ValueError: If wallet doesn't exist or doesn't belong to user
        """
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")

        if wallet.userid.value != userid:
            raise ValueError("Wallet does not belong to user")

        return wallet

    @staticmethod
    def validate_tokens_exist(token_in: Optional[Token], token_out: Optional[Token]) -> tuple[Token, Token]:
        """
        Validate both tokens exist.

        Args:
            token_in: Input token or None
            token_out: Output token or None

        Returns:
            tuple[Token, Token]: Validated token entities

        Raises:
            ValueError: If either token doesn't exist
        """
        if not token_in or not token_out:
            raise ValueError("Invalid token(s)")

        return token_in, token_out

    @staticmethod
    def validate_transaction_exists(transaction: Optional[Transaction], transaction_id: str) -> Transaction:
        """
        Validate transaction exists.

        Args:
            transaction: Transaction entity or None
            transaction_id: Transaction ID for error messages

        Returns:
            Transaction: Validated transaction entity

        Raises:
            ValueError: If transaction doesn't exist
        """
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")

        return transaction

    @staticmethod
    def validate_swap_exists(swap: Optional[Swap], transaction_id: str) -> Swap:
        """
        Validate swap exists for transaction.

        Args:
            swap: Swap entity or None
            transaction_id: Transaction ID for error messages

        Returns:
            Swap: Validated swap entity

        Raises:
            ValueError: If swap doesn't exist
        """
        if not swap:
            raise ValueError(f"No swap found for transaction {transaction_id}")

        return swap


class TokenValidationService:
    """
    Validation service for token-related operations.

    Follows Single Responsibility Principle.
    """

    @staticmethod
    def validate_token_not_exists(existing_token: Optional[Token], symbol: str) -> None:
        """
        Validate token doesn't already exist.

        Args:
            existing_token: Existing token or None
            symbol: Token symbol
            network: Network name

        Raises:
            ValueError: If token already exists
        """
        if existing_token:
            raise ValueError(f"Token {symbol} already exists!")
