from typing import Any, Dict, List, Optional
import logging
from src.domain.model import Wallet, Address, Transaction
from src.adapters.blockchain.base import Protocol

logger = logging.getLogger(__name__)

class SwapExecutor:
    """Handles low-level swap execution operations."""

    def __init__(self, protocol: Protocol):
        self.protocol = protocol

    async def execute_native_for_tokens(
        self,
        amount_out_min: int,
        token_path: List[str],
        pair_bin_steps: List[int],
        versions: List[int],
        deadline: int,
        to_address: Address,
        sender: Wallet,
        latest_tx: Optional[Transaction],
        native_amount: int
    ) -> Dict[str, Any]:
        """Execute native to tokens swap."""
        await self.protocol.ensure_chain()

        gas_price = await self.protocol.chain.eth.gas_price
        gas_price = int(gas_price * 1.1)

        path = (pair_bin_steps, versions, token_path)

        tx = await self.protocol.contract.functions.swapExactNATIVEForTokens(
            amount_out_min, path, to_address.value, deadline
        ).build_transaction({
            'from': sender.address.value,
            'nonce': latest_tx.nonce.value + 1 if latest_tx else 0,
            'chainId': int(self.protocol.chain_id.value),
            'gasPrice': gas_price,
            'value': native_amount
        })

        try:
            tx['gas'] = await self.protocol.chain.eth.estimate_gas(tx)
            signed_tx = sender.account.sign_transaction(tx)
            tx_hash = await self.protocol.chain.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx['txHash'] = f"0x{tx_hash.hex()}"

            logger.info(f"Native to tokens swap executed: {tx['txHash']}")
            return tx
        except Exception as e:
            logger.error(f"Failed native to tokens swap: {str(e)}")
            from src.core.exceptions.exceptions import BlockchainTransactionError
            raise BlockchainTransactionError.from_error(tx.get('txHash', 'unknown'), str(e))

    async def execute_tokens_for_native(
        self,
        amount_in: int,
        amount_out_min: int,
        token_path: List[str],
        pair_bin_steps: List[int],
        versions: List[int],
        deadline: int,
        to_address: Address,
        sender: Wallet,
        latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute tokens to native swap."""
        path = (pair_bin_steps, versions, token_path)

        return await self.protocol._build_and_send_transaction(
            'swapExactTokensForNATIVE',
            sender,
            latest_tx.nonce.value + 1 if latest_tx else 0,
            amount_in,
            amount_out_min,
            path,
            to_address.value,
            deadline
        )

    async def execute_tokens_for_tokens(
        self,
        amount_in: int,
        amount_out_min: int,
        token_path: List[str],
        pair_bin_steps: List[int],
        versions: List[int],
        deadline: int,
        to_address: Address,
        sender: Wallet,
        latest_tx: Optional[Transaction]
    ) -> Dict[str, Any]:
        """Execute tokens to tokens swap."""
        path = (pair_bin_steps, versions, token_path)

        return await self.protocol._build_and_send_transaction(
            'swapExactTokensForTokens',
            sender,
            latest_tx.nonce.value + 1 if latest_tx else 0,
            amount_in,
            amount_out_min,
            path,
            to_address.value,
            deadline
        )
