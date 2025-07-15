import logging
from datetime import datetime
from uuid import uuid4

from eth_account import Account

from src.adapters.blockchain.utils import create_protocol, track_transaction
from src.domain import commands
from src.domain.model import Wallet, Chain, Token, Transaction, TransactionStatus, TransactionType, ID, GasPrice, Gas, \
    Nonce, GasUsed, BlockNumber, TransactionHash
from src.service_layer import unit_of_work

# Import event classes for handler mappings
from src.core.events.events import (
    WalletCreated, WalletActivated, WalletDeactivated,
    TransactionCreated, TransactionConfirmed, TransactionFailed,
    TokenAdded, ChainAdded,
)

logger = logging.getLogger(__name__)


# Wallet Management Handlers - Refactored to use WalletService
async def create_wallet_handler(
        cmd: commands.CreateWalletCommand,
        puow: unit_of_work.AbstractUnitOfWork,
):
    """Create a new wallet for a user using WalletService."""
    async with puow:
        # Check if user already has a wallet
        existing_wallet = await puow.repo.get_wallet_by_userid(cmd.userid)
        if existing_wallet:
            raise ValueError(f"User {cmd.userid} already has a wallet. Only one wallet per user is allowed.")

        # Create wallet on blockchain
        acct = Account.create()

        # Create wallet domain entity
        wallet = Wallet.create(
            wallet_id=uuid4().hex,
            userid=cmd.userid,
            address=acct.address,
            account=acct,
            created_at=datetime.now()
        )

        puow.repo.add_wallet(wallet)
        logger.info(f"Wallet created for user {cmd.userid}: {acct.address}")


async def activate_wallet_handler(
        cmd: commands.ActivateWalletCommand,
        puow: unit_of_work.AbstractUnitOfWork,
):
    """Activate a user's wallet using WalletService."""
    async with puow:
        wallet = await puow.repo.get_wallet_by_userid(cmd.userid)
        if not wallet:
            raise ValueError(f"Wallet not found")

        wallet.activate()
        logger.info(f"Wallet {wallet.wallet_id} activated for user {wallet.userid}")


async def deactivate_wallet_handler(
        cmd: commands.DeactivateWalletCommand,
        puow: unit_of_work.AbstractUnitOfWork,
):
    """Deactivate a user's wallet using WalletService."""
    async with puow:
        wallet = await puow.repo.get_wallet_by_userid(cmd.userid)
        if not wallet:
            raise ValueError(f"Wallet not found")

        wallet.deactivate()
        logger.info(f"Wallet {wallet.wallet_id} deactivated for user {wallet.userid}")



async def add_chain_handler(
        cmd: commands.AddChainCommand,
        puow: unit_of_work.AbstractUnitOfWork
):
    """Add a new supported token for TraderJoe swaps."""
    async with puow:
        # Validate chain doesn't already exist
        existing_chain = await puow.repo.get_chain(cmd.chain_id)
        if existing_chain:
            raise ValueError(f"Chain {cmd.chain_id} already exists")

        # Create and save new chain
        new_chain = Chain.create(
            chain_id=cmd.chain_id,
            name=cmd.name,
            symbol=cmd.symbol,
            rpc_url=cmd.rpc_url,
        )
        puow.repo.add_chain(new_chain)


async def add_token_handler(
        cmd: commands.AddTokenCommand,
        puow: unit_of_work.AbstractUnitOfWork
):
    """Add a new supported token for TraderJoe swaps."""
    async with puow:
        # Validate token doesn't already exist
        existing_token = await puow.repo.get_token_by_symbol(cmd.symbol)
        if existing_token:
            raise ValueError(f"Token {cmd.symbol} already exists")

        # Create token using appropriate factory method
        token = Token.create(
            token_id=uuid4().hex,
            chain_id=cmd.chain_id,
            symbol=cmd.symbol,
            name=cmd.name,
            contract_address=cmd.contract_address,
            decimals=cmd.decimals,
        )

        puow.repo.add_token(token)
        logger.info(f"Token {cmd.symbol} added successfully with ID {token.token_id}")
        return token.token_id


# Token Approval Handlers
async def approve_token_handler(
        cmd: commands.ApproveTokenCommand,
        puow: unit_of_work.AbstractUnitOfWork,
):
    async with puow:
        wallet = await puow.repo.get_wallet_by_userid(cmd.userid)
        if not wallet:
            raise ValueError(f"Wallet not found for user {cmd.userid}")
        if not wallet.is_active:
            raise ValueError(f"Wallet {wallet.wallet_id} is not active")
        token = await puow.repo.get_token(cmd.token_id)
        if not token:
            raise ValueError(f"Token {cmd.token_id} not found")
        chain = await puow.repo.get_chain(token.chain_id)
        erc20_protocol = await create_protocol(token.contract_address, chain.chain_id, chain.rpc_url)
        latest_tx = await puow.repo.get_last_confirmed_transaction(chain.chain_id, wallet.wallet_id)
        tx = await erc20_protocol.approve(cmd.spender_address, cmd.amount, wallet, latest_tx=latest_tx)
        approval_tx = Transaction.create(
            transaction_id=ID(uuid4().hex),
            wallet_id=wallet.wallet_id,
            chain_id=token.chain_id,
            transaction_type=TransactionType.GIVE_APPROVAL,
            transaction_hash=TransactionHash(tx['txHash']),
            transaction_status=TransactionStatus.PENDING,
            gas_price=GasPrice(tx['gasPrice']),
            gas=Gas(tx['gas']),
            nonce=Nonce(tx['nonce'])
        )
        puow.repo.add_transaction(approval_tx)
        logger.info(f"Approval transaction created: {approval_tx.transaction_id.value} for token {token.name.value} on chain {chain.name.value}")


# TraderJoe Swap Handler
async def execute_traderjoe_swap_handler(
        cmd: commands.ExecuteSwapCommand,
        puow: unit_of_work.AbstractUnitOfWork,
):
    """Execute a TraderJoe swap using the specified strategy."""
    async with puow:
        # Get user's wallet
        wallet = await puow.repo.get_wallet_by_userid(cmd.userid)
        if not wallet:
            raise ValueError(f"Wallet not found for user {cmd.userid}")

        if not wallet.is_active:
            raise ValueError(f"Wallet is not active for user {cmd.userid}")

        # Get latest transaction for nonce calculation
        latest_tx = await puow.repo.get_latest_transaction_by_wallet_id(wallet.wallet_id)

        # Create TraderJoe protocol instance
        from src.adapters.blockchain.protocols.traderjoe import TraderJoeProtocol
        from src.domain.model import Address, ID, RPC

        trader_joe = TraderJoeProtocol(
            contract_address=Address(cmd.router_address),
            chain_id=ID(cmd.chain_id),
            rpc_url=RPC(f"https://api.avax.network/ext/bc/C/rpc"),  # This should come from config
            factory_address=Address(cmd.factory_address)
        )

        # Execute swap based on strategy
        if cmd.strategy == "fast":
            result = await trader_joe.swap_fast(
                token_from=cmd.token_from,
                token_to=cmd.token_to,
                amount_in=int(cmd.amount_in),
                max_slippage_percent=cmd.max_slippage_percent,
                to_address=wallet.address,
                sender=wallet,
                latest_tx=latest_tx
            )
        elif cmd.strategy == "cheap":
            result = await trader_joe.swap_cheap(
                token_from=cmd.token_from,
                token_to=cmd.token_to,
                amount_in=int(cmd.amount_in),
                max_slippage_percent=cmd.max_slippage_percent,
                to_address=wallet.address,
                sender=wallet,
                latest_tx=latest_tx
            )
        elif cmd.strategy == "secure":
            result = await trader_joe.swap_secure(
                token_from=cmd.token_from,
                token_to=cmd.token_to,
                amount_in=int(cmd.amount_in),
                max_slippage_percent=cmd.max_slippage_percent,
                to_address=wallet.address,
                sender=wallet,
                latest_tx=latest_tx
            )
        else:
            raise ValueError(f"Invalid strategy: {cmd.strategy}")

        # Create transaction record
        transaction = Transaction.create(
            transaction_id=ID(uuid4().hex),
            wallet_id=wallet.wallet_id,
            chain_id=ID(cmd.chain_id),
            transaction_type=TransactionType("TRADERJOE_SWAP"),
            transaction_hash=TransactionHash(result['txHash']),
            transaction_status=TransactionStatus("PENDING"),
            gas=Gas(str(result['gas'])),
            gas_price=GasPrice(str(result['gasPrice'])),
            nonce=Nonce(str(result['nonce']))
        )

        puow.repo.add_transaction(transaction)
        logger.info(f"TraderJoe {cmd.strategy} swap transaction created: {transaction.transaction_id.value}")


# ===== EVENT HANDLERS =====
# Internal Event Handlers - These handle business logic within the service

async def handle_transaction_created(event: TransactionCreated, puow: unit_of_work.AbstractUnitOfWork):
    async with puow:
        tx = await puow.repo.get_transaction(event.transaction_id)
        if not tx:
            raise ValueError(f"Transaction not found for id {event.transaction_id}")
        if tx.transaction_status != TransactionStatus.PENDING:
            logger.info(f"Transaction {event.transaction_id} already processed")
        else:
            chain = await puow.repo.get_chain(tx.chain_id)
            if not chain:
                raise ValueError(f"Chain {tx.chain_id} not found")
            try:
                tx_receipt = await track_transaction(chain.rpc_url, tx.transaction_hash)
                if tx_receipt['status'] == 1:
                    tx.confirm(BlockNumber(tx_receipt['blockNumber']), GasUsed(tx_receipt['gasUsed']))
                else:
                    tx.fail("Transaction reverted on blockchain")
            except Exception as e:
                tx.fail(f"Error occurred while tracking transaction: {e}")


# External Event Handlers - Generalized for DRY principle
async def publish_event_to_external_services(event, pub):
    """
    Generalized event publisher for external services.

    This single handler can publish any event type to external services,
    following DRY principle by eliminating repetitive publishing code.

    Args:
        event: Any domain event to be published
        pub: Event publisher instance
    """
    event_type = type(event).__name__
    event_id = getattr(event, 'wallet_id', None) or getattr(event, 'transaction_id', None) or getattr(event, 'swap_id', None)

    logger.info(f"Publishing {event_type} event for {event_id}")
    await pub.publish_event(event)


# Event handler mappings - each event can have multiple handlers
EVENT_HANDLERS = {
    # Wallet events - publish to external services for notifications
    WalletCreated: [publish_event_to_external_services],
    WalletActivated: [publish_event_to_external_services],
    WalletDeactivated: [publish_event_to_external_services],

    # Token events - publish to external services for notifications
    TokenAdded: [publish_event_to_external_services],  # External: notify user of new token

    # Chain events - publish to external services for notifications
    ChainAdded: [publish_event_to_external_services],  # External: notify user of new chain

    # Transaction events - both internal processing and external publishing
    TransactionCreated: [
        handle_transaction_created,
        publish_event_to_external_services # External: notify other services
    ],
    TransactionConfirmed: [
        publish_event_to_external_services # External: notify user of success
    ],
    TransactionFailed: [
        publish_event_to_external_services # External: notify user of failure
    ],
}

# Command handler mappings - each command has exactly one handler
COMMAND_HANDLERS = {
    commands.CreateWalletCommand: create_wallet_handler,
    commands.ActivateWalletCommand: activate_wallet_handler,
    commands.DeactivateWalletCommand: deactivate_wallet_handler,

    # Token Management Commands
    commands.AddTokenCommand: add_token_handler,

    #Chain Management Commands
    commands.AddChainCommand: add_chain_handler,

    # Token Approval Commands
    commands.ApproveTokenCommand: approve_token_handler,

    # TraderJoe Commands
    commands.ExecuteSwapCommand: execute_traderjoe_swap_handler,
}
