from typing import Any, Dict, List, Optional
import logging

from src.domain.model import Wallet, Address, Transaction
from src.adapters.blockchain.base import Protocol

logger = logging.getLogger(__name__)

class ERC20Protocol(Protocol):
    """ERC20 Token Protocol Implementation."""

    @property
    def abi(self) -> List[Dict[str, Any]]:
        return [
            {"inputs": [], "name": "name", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transfer", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"name": "from", "type": "address"}, {"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "transferFrom", "outputs": [{"type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
        ]


    @property
    def protocol_type(self) -> str:
        return "ERC20"

    async def get_balance(self, address: Address) -> int:
        """Get token balance for an address.

        Args:
            address (Address): The address to check balance for

        Returns:
            int: The token balance for the address
        """
        await self.ensure_chain()
        balance = await self.contract.functions.balanceOf(address.value).call()
        logger.info(f"Token balance retrieved for address: {address.value}")
        return balance

    async def get_allowance(self, owner: str, spender: str) -> int:
        """Get allowance amount for spender from owner.

        Args:
            owner (str): The address that owns the tokens
            spender (str): The address being granted approval

        Returns:
            int: The amount of tokens the spender is allowed to spend
        """
        await self.ensure_chain()
        allowance = await self.contract.functions.allowance(owner, spender).call()
        logger.info(f"Allowance retrieved for owner: {owner}, spender: {spender}")
        return allowance


    async def approve(self, spender: Address, amount: int, sender: Wallet, latest_tx: Optional[Transaction]) -> dict[str, Any]:
        """Approve spender to spend tokens."""
        return await self._build_and_send_transaction(
            'approve',
            sender,
            latest_tx.nonce.value + 1 if latest_tx else 0,
            spender.value,
            amount
        )

    async def get_decimals(self) -> int:
        """Get token decimals.

        Returns:
            int: The number of decimals for the token
        """
        await self.ensure_chain()
        decimals = await self.contract.functions.decimals().call()
        logger.info(f"Token decimals retrieved: {decimals}")
        return decimals

    async def get_name(self) -> str:
        """Get a token name.

        Returns:
            str: The name of the token
        """
        await self.ensure_chain()
        name = await self.contract.functions.name().call()
        logger.info(f"Token name retrieved: {name}")
        return name

    async def get_symbol(self) -> str:
        """Get token symbol.

        Returns:
            str: The symbol of the token
        """
        await self.ensure_chain()
        symbol = await self.contract.functions.symbol().call()
        logger.info(f"Token symbol retrieved: {symbol}")
        return symbol

    async def get_total_supply(self) -> int:
        """Get the total supply of the token.

        Returns:
            int: The total supply of the token
        """
        await self.ensure_chain()
        supply = await self.contract.functions.totalSupply().call()
        logger.info(f"Token total supply retrieved: {supply}")
        return supply

    async def transfer(self, to: Address, amount: int, sender: Wallet, nonce: int) -> dict[str, Any]:
        """Transfer tokens to an address."""
        return await self._build_and_send_transaction(
            'transfer',
            sender,
            nonce,
            to.value,
            amount
        )

    async def transfer_from(self, from_address: Address, to: Address, amount: int, sender: Wallet, nonce: int) -> dict[str, Any]:
        """Transfer tokens from one address to another using allowance."""
        return await self._build_and_send_transaction(
            'transferFrom',
            sender,
            nonce,
            from_address.value,
            to.value,
            amount
        )
