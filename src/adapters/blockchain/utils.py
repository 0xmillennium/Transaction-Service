from typing import Union, Optional

from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.types import TxReceipt
from web3.exceptions import TimeExhausted
import asyncio
import logging
from src.adapters.blockchain.protocols.erc20 import ERC20Protocol
from src.domain.model import Address, ID, RPC, TransactionHash
from src.core.exceptions.exceptions import BlockchainTransactionError

logger = logging.getLogger(__name__)


async def create_protocol(contract_address: Address, chain_id: ID, rpc_url: RPC) -> ERC20Protocol:
    return ERC20Protocol(contract_address, chain_id, rpc_url)


async def track_transaction(rpc_url: RPC, tx_hash: TransactionHash, timeout: int = 120) -> TxReceipt:
    """Track a blockchain transaction until it's mined and return the receipt.

    Args:
        rpc_url: The RPC URL of the blockchain node
        tx_hash: The transaction hash to track
        timeout: Maximum time to wait for receipt in seconds (default: 120)

    Returns:
        TxReceipt: The transaction receipt after successful mining

    Raises:
        BlockchainTransactionError: If transaction fails or times out
    """
    w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url.value))
    try:
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash.value, timeout=timeout)

        if receipt['status'] == 1:
            logger.info(f"Transaction {tx_hash} successfully mined in block {receipt['blockNumber']}")
        else:
            logger.error(f"Transaction {tx_hash} failed in block {receipt['blockNumber']}")
        return receipt

    except TimeExhausted as e:
        logger.error(f"Failed to get receipt for transaction {tx_hash}: {str(e)}")
        raise BlockchainTransactionError.from_error(
            tx_hash=tx_hash.value,
            error_message=f"Transaction failed: {str(e)}"
        )
