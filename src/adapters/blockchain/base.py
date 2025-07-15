import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from web3 import AsyncWeb3, AsyncHTTPProvider

from src.domain.model import Address, RPC, ID, Wallet
from src.core.exceptions.exceptions import BlockchainTransactionError

logger = logging.getLogger(__name__)

class Protocol(ABC):
    """Abstract base class for protocol implementations."""

    def __init__(self, contract_address: Address, chain_id: ID, rpc_url: RPC):
        self.contract_address = contract_address
        self.chain_id = chain_id
        self.chain = AsyncWeb3(AsyncHTTPProvider(rpc_url.value))
        self.contract = self.chain.eth.contract(address=self.contract_address.value, abi=self.abi)

    @property
    @abstractmethod
    def abi(self) -> List[Dict[str, Any]]:
        """Return the ABI for the protocol."""
        pass

    @property
    @abstractmethod
    def protocol_type(self) -> str:
        """Return the protocol type identifier."""
        pass

    async def ensure_chain(self) -> bool:
        """Ensure protocol is bound to a chain and connected."""
        return await self.chain.is_connected()

    async def _build_and_send_transaction(
        self,
        function_name: str,
        sender: Wallet,
        nonce: int,
        *args
    ) -> dict[str, Any]:
        """Helper method to build and send transactions for nonpayable functions.

        Args:
            function_name (str): Name of the contract function to call
            sender (Wallet): The wallet initiating the transaction
            nonce (int): Transaction nonce
            *args: Arguments to pass to the contract function

        Returns:
            dict[str, Any]: Transaction details including hash

        Raises:
            BlockchainTransactionError: If the transaction fails
        """
        await self.ensure_chain()

        # Get the current gas price with safety multiplier
        gas_price = await self.chain.eth.gas_price
        gas_price = int(gas_price * 1.1)  # 10% buffer

        # Build the transaction
        contract_function = getattr(self.contract.functions, function_name)
        tx = await contract_function(*args).build_transaction(
            {
                'from': sender.address.value,
                'nonce': nonce,
                'chainId': int(self.chain_id.value),
                'gasPrice': gas_price,
            }
        )

        try:
            # Estimate gas
            tx['gas'] = await self.chain.eth.estimate_gas(tx)
            logger.info(f"Gas estimation successful for {function_name} transaction: {tx['gas']} units")

            # Sign and send transaction
            signed_tx = sender.account.sign_transaction(tx)
            tx_hash =await self.chain.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx['txHash'] = f"0x{tx_hash.hex()}"

            logger.info(f"{function_name} transaction sent with hash: {tx['txHash']}")
            return tx

        except Exception as e:
            logger.error(f"Failed to process {function_name} transaction: {str(e)}")
            raise BlockchainTransactionError.from_error(tx.get('txHash', 'unknown'), str(e))
