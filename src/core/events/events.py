from pydantic import EmailStr, Field
from pydantic.dataclasses import dataclass
from uuid import UUID, uuid4
from datetime import datetime, timezone
from src.core.correlation.context import get_correlation_id


@dataclass(kw_only=True)
class Event:
    source_service: str = "transaction"  # Changed from "user" to "transaction"
    event_id: UUID = Field(default_factory=uuid4)
    correlation_id: str = Field(default_factory=get_correlation_id)
    timestamp: float = Field(default_factory=lambda: datetime.now(tz=timezone.utc).timestamp())


@dataclass(kw_only=True)
class IncomingEvent(Event):
    ...


@dataclass(kw_only=True)
class OutgoingEvent(Event):
    ...

# Wallet events
@dataclass(kw_only=True)
class WalletCreated(OutgoingEvent):
    wallet_id: str
    userid: str
    address: str
    event_type: str = "transaction.wallet.created"

@dataclass(kw_only=True)
class WalletActivated(OutgoingEvent):
    wallet_id: str
    userid: str
    event_type: str = "transaction.wallet.activated"

@dataclass(kw_only=True)
class WalletDeactivated(OutgoingEvent):
    wallet_id: str
    userid: str
    event_type: str = "transaction.wallet.deactivated"

# Transaction events
@dataclass(kw_only=True)
class TransactionCreated(OutgoingEvent):
    transaction_id: str
    wallet_id: str
    transaction_type: str
    transaction_hash: str
    event_type: str = "transaction.transaction.created"

@dataclass(kw_only=True)
class TransactionConfirmed(OutgoingEvent):
    transaction_id: str
    transaction_hash: str
    block_number: int
    gas_used: int
    event_type: str = "transaction.transaction.confirmed"

@dataclass(kw_only=True)
class TransactionFailed(OutgoingEvent):
    transaction_id: str
    error_message: str
    event_type: str = "transaction.transaction.failed"

@dataclass(kw_only=True)
class ChainAdded(OutgoingEvent):
    chain_id: str
    name: str
    symbol: str
    rpc_url: str
    event_type: str = "transaction.chain.added"

# Token events
@dataclass(kw_only=True)
class TokenAdded(OutgoingEvent):
    token_id: str
    chain_id: str
    symbol: str
    name: str
    contract_address: str
    decimals: str
    event_type: str = "transaction.token.added"

