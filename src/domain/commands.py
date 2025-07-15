from pydantic.dataclasses import dataclass
from decimal import Decimal

from src.domain.model import Address


@dataclass(frozen=True)
class Command:
    ...


# Wallet commands
@dataclass(frozen=True)
class CreateWalletCommand(Command):
    userid: str

@dataclass(frozen=True)
class ActivateWalletCommand(Command):
    userid: str

@dataclass(frozen=True)
class DeactivateWalletCommand(Command):
    userid: str

@dataclass(frozen=True)
class AddChainCommand(Command):
    chain_id: str
    name: str
    symbol: str
    rpc_url: str

# Token Management commands
@dataclass(frozen=True)
class AddTokenCommand(Command):
    chain_id: str
    symbol: str
    name: str
    contract_address: str = None  # None for native tokens
    decimals: str = "18"
    is_native: bool = False

@dataclass(frozen=True)
class DeactivateTokenCommand(Command):
    token_id: str

@dataclass(frozen=True)
class RegisterTokenCommand(Command):
    token_id: str
    symbol: str
    name: str
    decimals: int
    contract_address: str
    network: str

# Token Approval commands
@dataclass(frozen=True)
class ApproveTokenCommand(Command):
    userid: str
    token_id: str
    spender_address: Address
    amount: int

@dataclass(frozen=True)
class RevokeApprovalCommand(Command):
    userid: str
    token_id: str
    amount: str = None  # None means revoke all

@dataclass(frozen=True)
class CheckApprovalCommand(Command):
    userid: str
    token_id: str
    required_amount: str

# Transaction commands
@dataclass(frozen=True)
class CreateSwapTransactionCommand(Command):
    userid: str
    token_in_id: str
    token_out_id: str
    amount_in: str
    slippage_tolerance: str
    deadline_minutes: int = 20  # Default 20 minutes from now
    network: str = "avalanche"  # Target network for the swap

@dataclass(frozen=True)
class EstimateGasCommand(Command):
    transaction_id: str
    wallet_address: str

@dataclass(frozen=True)
class BroadcastTransactionCommand(Command):
    transaction_id: str

@dataclass(frozen=True)
class UpdateTransactionStatusCommand(Command):
    transaction_id: str
    transaction_hash: str
    status: str
    block_number: str = None
    gas_used: str = None
    error_message: str = None

# Add the missing ExecuteSwapCommand
@dataclass(frozen=True)
class ExecuteSwapCommand(Command):
    userid: str
    wallet_id: str
    token_in_address: str
    token_out_address: str
    amount_in: Decimal
    slippage_tolerance: Decimal

# Swap commands
@dataclass(frozen=True)
class SwapExactNativeToTokenCommand(Command):
    userid: str
    token_out_id: str
    amount_in: str
    amount_out_min: str
    slippage_tolerance: str
    deadline_minutes: int = 20

@dataclass(frozen=True)
class SwapTokenToExactNativeCommand(Command):
    userid: str
    token_in_id: str
    amount_in: str
    amount_out_min: str
    slippage_tolerance: str
    deadline_minutes: int = 20

@dataclass(frozen=True)
class SwapExactTokenToTokenCommand(Command):
    userid: str
    token_in_id: str
    token_out_id: str
    amount_in: str
    amount_out_min: str
    slippage_tolerance: str
    deadline_minutes: int = 20

@dataclass(frozen=True)
class SwapTokenToExactTokenCommand(Command):
    userid: str
    token_in_id: str
    token_out_id: str
    amount_in_max: str
    amount_out: str
    slippage_tolerance: str
    deadline_minutes: int = 20

@dataclass(frozen=True)
class CreateTransactionCommand(Command):
    wallet_id: str
    to_address: str
    value: str
    gas_limit: str = None
    max_fee_per_gas: str = None
    max_priority_fee_per_gas: str = None

# TraderJoe Swap commands
@dataclass(frozen=True)
class ExecuteSwapCommand(Command):
    userid: str
    strategy: str  # "fast", "cheap", "secure"
    token_from: str  # Token address or "NATIVE"
    token_to: str    # Token address or "NATIVE"
    amount_in: str   # Amount as string to avoid precision issues
    max_slippage_percent: float
    chain_id: str
    router_address: str
    factory_address: str
