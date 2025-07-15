import enum
from datetime import datetime

from eth_account import Account
from eth_account.signers.local import LocalAccount
from sqlalchemy import Column, MetaData, String, Table, Boolean, DateTime, Text, ForeignKey, Index, Numeric, \
    TypeDecorator, Enum, Integer
from sqlalchemy.orm import composite, registry
from sqlalchemy.sql import func

from src import config
from src.domain.model import TransactionStatus, TransactionType, Chain, RPC, Nonce, BlockNumber

metadata = MetaData()
mapper_registry = registry()
fernet = config.get_encyption_key()


class Encryption(TypeDecorator):
    impl = String

    def process_bind_param(self, value: LocalAccount, dialect):
        if value is None:
            return value
        return fernet.encrypt(value.key).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return Account.from_key(fernet.decrypt(value.encode()))


chain_table = Table(
    "chain",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("name", String(50), key="db_name", nullable=False, unique=True),
    Column("symbol", String(10), key="db_symbol", nullable=False, unique=True),
    Column("rpc_url", String(255), key="db_rpc_url", nullable=False, unique=True),
)

# Simplified wallet table (one per user, Avalanche only)
wallet_table = Table(
    "wallet",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("userid", String(32), key="db_userid", nullable=False, unique=True),  # One wallet per user
    Column("address", String(42), key="db_address", nullable=False, unique=True),
    Column("private_key_encrypted", Encryption, key="db_private_key_encrypted", nullable=False),
    Column("is_active", Boolean, key="db_is_active", nullable=False, default=True),
    Column("created_at", DateTime, key="db_created_at", nullable=False, default=func.now()),
    Index("ix_wallet_user_id", "db_userid"),
)

# Token table (TraderJoe Avalanche tokens only)
token_table = Table(
    "token",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("chain_id", String(32), ForeignKey("chain.db_id"), key="db_chain_id", nullable=False),
    Column("symbol", String(20), key="db_symbol", nullable=False, unique=True),
    Column("name", String(100), key="db_name", nullable=False),
    Column("contract_address", String(42), key="db_contract_address", nullable=True),  # Null for native AVAX
    Column("decimals", String(3), key="db_decimals", nullable=False),
    Column("is_native", Boolean, key="db_is_native", nullable=False, default=False),
    Column("is_active", Boolean, key="db_is_active", nullable=False, default=True),
    Index("ix_token_contract_address", "db_contract_address"),
)

# Token approval table (current approval amounts per wallet-token pair)
token_approval_table = Table(
    "token_approval",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("wallet_id", String(32), ForeignKey("wallet.db_id"), key="db_wallet_id", nullable=False),
    Column("token_id", String(32), ForeignKey("token.db_id"), key="db_token_id", nullable=False),
    Column("approved_amount", Numeric(precision=78, scale=0), key="db_approved_amount", nullable=False, default=0),  # Wei amounts
    Column("updated_at", DateTime, key="db_updated_at", nullable=False),
    Index("ix_token_approval_wallet_token", "db_wallet_id", "db_token_id", unique=True),
)

# Transaction table (APPROVE, REVOKE_APPROVAL, SWAP)
transaction_table = Table(
    "transaction",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("chain_id", String(32), ForeignKey("chain.db_id"), key="db_chain_id", nullable=False),
    Column("wallet_id", String(32), ForeignKey("wallet.db_id"), key="db_wallet_id", nullable=False),
    Column("type", Enum(TransactionType, name="type_enum", create_type=True), key="db_type", nullable=False),  # APPROVE, REVOKE_APPROVAL, SWAP
    Column("hash", String(66), key="db_hash", nullable=False),  # Null until confirmed
    Column("status", Enum(TransactionStatus, name="status_enum"), key="db_status", nullable=False, default="PENDING"),  # PENDING, CONFIRMED, FAILED
    Column("gas", Integer, key="db_gas", nullable=False),
    Column("gas_price", Integer, key="db_gas_price", nullable=False),  # In wei
    Column("gas_used", Integer, key="db_gas_used", nullable=True),
    Column("nonce", Integer, key="db_nonce", nullable=False),
    Column("block_number", Integer, key="db_block_number", nullable=True),
    Column("created_at", DateTime, key="db_created_at", nullable=False, default=func.now()),
    Column("updated_at", DateTime, key="db_updated_at", nullable=False, default=func.now(), onupdate=func.now()),
    Index("ix_transaction_wallet", "db_wallet_id"),
    Index("ix_transaction_hash", "db_hash"),
    Index("ix_transaction_status", "db_status"),
    Index("ix_transaction_status_updated_at", "db_status", "db_updated_at")
)

# Approval transaction table (approval/revoke history)
approval_transaction_table = Table(
    "approval_transaction",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("transaction_id", String(32), ForeignKey("transaction.db_id"), key="db_transaction_id", nullable=False),
    Column("token_id", String(32), ForeignKey("token.db_id"), key="db_token_id", nullable=False),
    Column("amount", Numeric(precision=78, scale=0), key="db_amount", nullable=False),  # Approval amount in wei
    Column("previous_amount", Numeric(precision=78, scale=0), key="db_previous_amount", nullable=False, default=0),
    Column("new_amount", Numeric(precision=78, scale=0), key="db_new_amount", nullable=False),
    Index("ix_approval_transaction_id", "db_transaction_id"),
    Index("ix_approval_token_id", "db_token_id"),
)

# Swap transaction table (swap details with all swap types)
swap_transaction_table = Table(
    "swap_transaction",
    metadata,
    Column("id", String(32), key="db_id", primary_key=True),
    Column("transaction_id", String(32), ForeignKey("transaction.db_id"), key="db_transaction_id", nullable=False),
    Column("token_in_id", String(32), ForeignKey("token.db_id"), key="db_token_in_id", nullable=False),
    Column("token_out_id", String(32), ForeignKey("token.db_id"), key="db_token_out_id", nullable=False),
    Column("amount_in", Numeric(precision=78, scale=0), key="db_amount_in", nullable=False),  # Input amount in wei
    Column("amount_out_expected", Numeric(precision=78, scale=0), key="db_amount_out_expected", nullable=False),
    Column("amount_out_actual", Numeric(precision=78, scale=0), key="db_amount_out_actual", nullable=True),  # Actual output after confirmation
    Column("slippage_tolerance", String(10), key="db_slippage_tolerance", nullable=False),  # Percentage as string
    Column("deadline", DateTime, key="db_deadline", nullable=False),
    Column("router_address", String(42), key="db_router_address", nullable=False),  # TraderJoe router contract
    Index("ix_swap_transaction_id", "db_transaction_id"),
    Index("ix_swap_token_in", "db_token_in_id"),
    Index("ix_swap_token_out", "db_token_out_id"),
)


def init_orm_mappers():
    """
    Initializes SQLAlchemy ORM mappers for transaction service domain models.

    Maps the domain models to database tables using composite types
    for value objects. User data is not stored - only user_id references.
    """
    from src.domain.model import (
        ID,
        Wallet,
        Token, Symbol, Name,Address, TokenDecimals,
        Transaction, TransactionHash, TransactionType, TransactionStatus,
        Approval, ApprovalAmount,
        ApprovalTransaction,
        SwapTransaction, Amount, SlippageTolerance, Gas, GasPrice
    )

    # Wallet mapping
    mapper_registry.map_imperatively(
        Wallet,
        wallet_table,
        properties={
            "wallet_id": composite(ID, wallet_table.c.db_id),
            "userid": composite(ID, wallet_table.c.db_userid),
            "address": composite(Address, wallet_table.c.db_address),
            "account": wallet_table.c.db_private_key_encrypted,
            "is_active": wallet_table.c.db_is_active,
            "created_at": wallet_table.c.db_created_at,
        },
    )

    #Chain mapping
    mapper_registry.map_imperatively(
        Chain,
        chain_table,
        properties={
            "chain_id": composite(ID, chain_table.c.db_id),
            "name": composite(Name, chain_table.c.db_name),
            "symbol": composite(Symbol, chain_table.c.db_symbol),
            "rpc_url": composite(RPC, chain_table.c.db_rpc_url),
        }
    )

    # Token mapping
    mapper_registry.map_imperatively(
        Token,
        token_table,
        properties={
            "token_id": composite(ID, token_table.c.db_id),
            "chain_id": composite(ID, token_table.c.db_chain_id),
            "symbol": composite(Symbol, token_table.c.db_symbol),
            "name": composite(Name, token_table.c.db_name),
            "contract_address": composite(Address, token_table.c.db_contract_address),
            "decimals": composite(TokenDecimals, token_table.c.db_decimals),
            "is_native": token_table.c.db_is_native,
            "is_active": token_table.c.db_is_active,
        },
    )

    # Token approval mapping
    mapper_registry.map_imperatively(
        Approval,
        token_approval_table,
        properties={
            "approval_id": composite(ID, token_approval_table.c.db_id),
            "wallet_id": composite(ID, token_approval_table.c.db_wallet_id),
            "token_id": composite(ID, token_approval_table.c.db_token_id),
            "approved_amount": composite(ApprovalAmount, token_approval_table.c.db_approved_amount),
            "updated_at": composite(datetime, token_approval_table.c.db_updated_at),
        },
    )

    # Transaction mapping
    mapper_registry.map_imperatively(
        Transaction,
        transaction_table,
        properties={
            "transaction_id": composite(ID, transaction_table.c.db_id),
            "chain_id": composite(ID, transaction_table.c.db_chain_id),
            "wallet_id": composite(ID, transaction_table.c.db_wallet_id),
            "transaction_hash": composite(TransactionHash, transaction_table.c.db_hash),
            "transaction_type": transaction_table.c.db_type,
            "transaction_status": transaction_table.c.db_status,
            "gas": composite(Gas, transaction_table.c.db_gas),
            "gas_price": composite(GasPrice, transaction_table.c.db_gas_price),
            "gas_used": composite(Gas, transaction_table.c.db_gas_used),
            "nonce": composite(Nonce, transaction_table.c.db_nonce),
            "block_number": composite(BlockNumber, transaction_table.c.db_block_number),
            "created_at": transaction_table.c.db_created_at,
            "updated_at": transaction_table.c.db_updated_at,
        },
    )

    # Approval transaction mapping
    mapper_registry.map_imperatively(
        ApprovalTransaction,
        approval_transaction_table,
        properties={
            "approval_transaction_id": composite(ID, approval_transaction_table.c.db_id),
            "transaction_id": composite(ID, approval_transaction_table.c.db_transaction_id),
            "token_id": composite(ID, approval_transaction_table.c.db_token_id),
            "amount": composite(Amount, approval_transaction_table.c.db_amount),
            "previous_amount": composite(Amount, approval_transaction_table.c.db_previous_amount),
            "new_amount": composite(Amount, approval_transaction_table.c.db_new_amount),
        },
    )

    # Swap transaction mapping
    mapper_registry.map_imperatively(
        SwapTransaction,
        swap_transaction_table,
        properties={
            "swap_transaction_id": composite(ID, swap_transaction_table.c.db_id),
            "transaction_id": composite(ID, swap_transaction_table.c.db_transaction_id),
            "token_in_id": composite(ID, swap_transaction_table.c.db_token_in_id),
            "token_out_id": composite(ID, swap_transaction_table.c.db_token_out_id),
            "amount_in": composite(Amount, swap_transaction_table.c.db_amount_in),
            "amount_out_expected": composite(Amount, swap_transaction_table.c.db_amount_out_expected),
            "amount_out_actual": composite(Amount, swap_transaction_table.c.db_amount_out_actual),
            "slippage_tolerance": composite(SlippageTolerance, swap_transaction_table.c.db_slippage_tolerance),
            "deadline": swap_transaction_table.c.db_deadline,
            "router_address": swap_transaction_table.c.db_router_address,
        },
    )
