import enum
from datetime import datetime, timezone
from typing import Annotated, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from pydantic.dataclasses import dataclass
from pydantic import Field
from src.core.events import events
from sqlalchemy.orm import reconstructor


def normalize_fullname(fullname: str) -> str:
    return " ".join(name.capitalize() for name in fullname.split())

class TransactionType(enum.Enum):
    GIVE_APPROVAL = "GIVE_APPROVAL"
    REVOKE_APPROVAL = "REVOKE_APPROVAL"
    SWAP_NATIVE_TO_TOKEN = "SWAP_NATIVE_TO_TOKEN"
    SWAP_TOKEN_TO_NATIVE = "SWAP_TOKEN_TO_NATIVE"
    SWAP_TOKEN_TO_TOKEN = "SWAP_TOKEN_TO_TOKEN"

class TransactionStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"

@dataclass(frozen=True)
class BaseValueObject:
    ...

@dataclass(frozen=True)
class Account(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^0x[a-fA-F0-9]{40}$")  # Ethereum address format
    ]

@dataclass(frozen=True)
class RPC(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^https://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$")  # Basic URL validation
    ]

@dataclass(frozen=True)
class EncryptedPrivateKey(BaseValueObject):
    value: str  # Encrypted private key as string

# Token value objects
@dataclass(frozen=True)
class ID(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[0-9a-f]{5,32}$")
    ]

@dataclass(frozen=True)
class Symbol(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[A-Z]{1,20}$")
    ]

@dataclass(frozen=True)
class Name(BaseValueObject):
    value: Annotated[
        str,
        Field(min_length=1, max_length=100)
    ]

@dataclass(frozen=True)
class Address(BaseValueObject):
    value: Annotated[
        Optional[str],
        Field(pattern=r"^0x[a-fA-F0-9]{40}$")  # Null for native tokens
    ] = None

@dataclass(frozen=True)
class TokenDecimals(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[0-9]{1,3}$")  # Usually 18 for most tokens
    ]

@dataclass(frozen=True)
class TransactionHash(BaseValueObject):
    value: Annotated[
        Optional[str],
        Field(pattern=r"^0x[a-fA-F0-9]{64}$")
    ] = None

@dataclass(frozen=True)
class BlockNumber(BaseValueObject):
    value: Annotated[
        Optional[int],
        Field(ge=0)
    ]

@dataclass(frozen=True)
class Nonce(BaseValueObject):
    value: Annotated[
        int,
        Field(ge=0)
    ]

@dataclass(frozen=True)
class Gas(BaseValueObject):
    value: Annotated[
        Optional[int],
        Field(ge=0)
    ]

@dataclass(frozen=True)
class GasUsed(BaseValueObject):
    value: Annotated[
        Optional[int],
        Field(ge=0)
    ]

@dataclass(frozen=True)
class GasPrice(BaseValueObject):
    value: Annotated[
        int,
        Field(ge=0)  # In wei
    ]

# Swap value objects
@dataclass(frozen=True)
class SwapID(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[0-9a-f]{32}$")
    ]

@dataclass(frozen=True)
class Amount(BaseValueObject):
    value: Annotated[
        int,
        Field(ge=0)
    ]

@dataclass(frozen=True)
class SlippageTolerance(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^[0-9]{1,2}(\.[0-9]{1,2})?$")  # Percentage like "0.5" or "5"
    ]


@dataclass(frozen=True)
class ApprovalAmount(BaseValueObject):
    value: Annotated[
        int,
        Field(ge=0)  # Large number as string to handle wei amounts
    ]

@dataclass(frozen=True)
class ApprovalType(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^(GIVE_APPROVAL|REMOVE_APPROVAL)$")
    ]

@dataclass(frozen=True)
class SwapType(BaseValueObject):
    value: Annotated[
        str,
        Field(pattern=r"^(EXACT_NATIVE_TO_TOKEN|TOKEN_TO_EXACT_NATIVE|EXACT_TOKEN_TO_TOKEN|TOKEN_TO_EXACT_TOKEN|NATIVE_TO_EXACT_TOKEN|TOKEN_TO_EXACT_NATIVE)$")
    ]


class Wallet:
    """
    Represents a user's single blockchain wallet in the transaction service.

    Each user has exactly ONE wallet that works across ALL blockchains and protocols.
    The same private key/address pair is used for all networks and transactions.
    Only stores transaction-related wallet data - user info comes from user service.
    """

    def __init__(self,
                 wallet_id: ID,
                 userid: ID,
                 address: Address,
                 account: LocalAccount,
                 created_at: datetime,
                 is_active: bool = True,
                 ):
        self.wallet_id = wallet_id
        self.userid = userid
        self.address = address
        self.account = account
        self.created_at = created_at
        self.is_active = is_active
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               wallet_id: str,
               userid: str,
               address: str,
               account: LocalAccount,
               created_at: datetime):
        """Factory method to create a new wallet for a user."""
        wallet = cls(
            ID(wallet_id),
            ID(userid),
            Address(address),
            account,
            created_at
        )

        wallet.events.append(
            events.WalletCreated(
                wallet_id=wallet.wallet_id.value,
                userid=wallet.userid.value,
                address=wallet.address.value
            )
        )
        return wallet

    def activate(self):
        """Activate the wallet and emit event."""
        if not self.is_active:
            self.is_active = True
            self.events.append(
                events.WalletActivated(
                    wallet_id=self.wallet_id.value,
                    userid=self.userid.value
                )
            )

    def deactivate(self):
        """Deactivate the wallet and emit event."""
        if self.is_active:
            self.is_active = False
            self.events.append(
                events.WalletDeactivated(
                    wallet_id=self.wallet_id.value,
                    userid=self.userid.value
                )
            )

class Chain:
    """
    Represents a blockchain network supported by the transaction service.

    Contains basic chain information like ID, name, and native token.
    """

    def __init__(self,
                 chain_id: ID,
                 name: Name,
                 symbol: Symbol,
                 rpc_url: RPC):
        self.chain_id = chain_id
        self.name = name
        self.symbol = symbol
        self.rpc_url = rpc_url
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               chain_id: str,
               name: str,
               symbol: str,
               rpc_url: str):
        """Factory method to create a new blockchain network."""
        chain = cls(
            ID(chain_id),
            Name(name),
            Symbol(symbol),
            RPC(rpc_url)
        )

        chain.events.append(
            events.ChainAdded(
                chain_id=chain.chain_id.value,
                name=chain.name.value,
                symbol=chain.symbol.value,
                rpc_url=chain.rpc_url.value
            )
        )
        return chain

class Token:
    """
    Represents a blockchain token (native or ERC-20) supported by the transaction service.
    """

    def __init__(self,
                 token_id: ID,
                 chain_id: ID,
                 symbol: Symbol,
                 name: Name,
                 contract_address: Address,
                 decimals: TokenDecimals,
                 ):
        self.token_id = token_id
        self.chain_id = chain_id
        self.symbol = symbol
        self.name = name
        self.contract_address = contract_address
        self.decimals = decimals
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
                     token_id: str,
                     chain_id: str,
                     symbol: str,
                     name: str,
                     contract_address: str,
                     decimals: str,
                     ):
        """Factory method to create an ERC-20 token."""
        token = cls(
            ID(token_id),
            ID(chain_id),
            Symbol(symbol),
            Name(name),
            Address(contract_address),
            TokenDecimals(decimals),
        )
        token.events.append(
            events.TokenAdded(
                token_id=token.token_id.value,
                chain_id=token.chain_id.value,
                symbol=token.symbol.value,
                name=token.name.value,
                contract_address=token.contract_address.value,
                decimals=token.decimals.value
            )
        )
        return token


class Transaction:
    """
    Represents a blockchain transaction aggregate root.

    Encapsulates transaction state and lifecycle management.
    References user by ID only - user data comes from user service.
    """

    def __init__(self,
                 transaction_id: ID,
                 wallet_id: ID,
                 chain_id: ID,
                 transaction_type: TransactionType,
                 transaction_hash: TransactionHash,
                 transaction_status: TransactionStatus,
                 gas: Gas,
                 gas_price: GasPrice,
                 nonce: Nonce,
                 created_at: datetime,
                 updated_at: datetime,
                 gas_used: Optional[GasUsed] = None,
                 block_number: Optional[BlockNumber] = None,
    ):
        self.transaction_id = transaction_id
        self.wallet_id = wallet_id
        self.chain_id = chain_id
        self.transaction_type = transaction_type
        self.transaction_hash = transaction_hash
        self.transaction_status = transaction_status
        self.gas = gas
        self.gas_price = gas_price
        self.nonce = nonce
        self.created_at = created_at
        self.updated_at = updated_at
        self.gas_used = gas_used
        self.block_number = block_number
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(
            cls,
            transaction_id: ID,
            wallet_id: ID,
            chain_id: ID,
            transaction_type: TransactionType,
            transaction_hash: TransactionHash,
            transaction_status: TransactionStatus,
            gas: Gas,
            gas_price: GasPrice,
            nonce: Nonce,
    ):
        """Factory method to create a new transaction."""
        transaction = cls(
            transaction_id,
            wallet_id,
            chain_id,
            transaction_type,
            transaction_hash,
            transaction_status,
            gas,
            gas_price,
            nonce,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        transaction.events.append(
            events.TransactionCreated(
                transaction_id=transaction.transaction_id.value,
                wallet_id=transaction.wallet_id.value,
                transaction_type=transaction.transaction_type.value,
                transaction_hash=transaction.transaction_hash.value,
            )
        )
        return transaction

    def confirm(self, block_number: BlockNumber, gas_used: GasUsed):
        """Mark transaction as confirmed on the blockchain."""
        self.transaction_status = TransactionStatus.CONFIRMED
        self.block_number = block_number
        self.gas_used = gas_used
        self.updated_at = datetime.now()

        self.events.append(
            events.TransactionConfirmed(
                transaction_id=self.transaction_id.value,
                transaction_hash=self.transaction_hash.value,
                block_number=self.block_number.value,
                gas_used=self.gas_used.value
            )
        )

    def fail(self, error_message: str):
        """Mark transaction as failed."""
        self.transaction_status = TransactionStatus.FAILED
        self.updated_at = datetime.now()

        self.events.append(
            events.TransactionFailed(
                transaction_id=self.transaction_id.value,
                error_message=error_message
            )
        )


class Swap:
    """
    Represents a token swap operation.

    Contains swap-specific data and validation logic.
    """

    def __init__(self,
                 swap_id: SwapID,
                 transaction_id: ID,
                 token_in_id: ID,
                 token_out_id: ID,
                 amount_in: Amount,
                 amount_out_expected: Amount,
                 slippage_tolerance: SlippageTolerance,
                 trader_joe_router: Address,
                 deadline: datetime,
                 amount_out_actual: Optional[Amount] = None):
        self.swap_id = swap_id
        self.transaction_id = transaction_id
        self.token_in_id = token_in_id
        self.token_out_id = token_out_id
        self.amount_in = amount_in
        self.amount_out_expected = amount_out_expected
        self.amount_out_actual = amount_out_actual
        self.slippage_tolerance = slippage_tolerance
        self.trader_joe_router = trader_joe_router
        self.deadline = deadline
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               swap_id: str,
               transaction_id: str,
               token_in_id: str,
               token_out_id: str,
               amount_in: str,
               amount_out_expected: str,
               slippage_tolerance: str,
               trader_joe_router: str,
               deadline: datetime):
        """Factory method to create a new swap."""
        swap = cls(
            SwapID(swap_id),
            ID(transaction_id),
            ID(token_in_id),
            ID(token_out_id),
            Amount(amount_in),
            Amount(amount_out_expected),
            SlippageTolerance(slippage_tolerance),
            Address(trader_joe_router),
            deadline
        )

        swap.events.append(
            events.SwapCreated(
                swap_id=swap.swap_id.value,
                transaction_id=swap.transaction_id.value,
                token_in_id=swap.token_in_id.value,
                token_out_id=swap.token_out_id.value,
                amount_in=swap.amount_in.value,
                amount_out_expected=swap.amount_out_expected.value
            )
        )
        return swap

    def complete(self, amount_out_actual: str):
        """Mark swap as completed with actual output amount."""
        self.amount_out_actual = Amount(amount_out_actual)

        self.events.append(
            events.SwapCompleted(
                swap_id=self.swap_id.value,
                transaction_id=self.transaction_id.value,
                amount_out_actual=self.amount_out_actual.value
            )
        )


class Approval:
    """
    Represents the current approval amount for a specific token-wallet pair.

    This aggregate tracks how much of a token a wallet has approved for spending
    by smart contracts (like TraderJoe router). Used for quick approval checks
    without needing RPC calls.
    """

    def __init__(self,
                 approval_id: ID,
                 wallet_id: ID,
                 token_id: ID,
                 approved_amount: ApprovalAmount,
                 updated_at: Optional[datetime] = None):
        self.approval_id = approval_id
        self.wallet_id = wallet_id
        self.token_id = token_id
        self.approved_amount = approved_amount
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
               approval_id: str,
               wallet_id: str,
               token_id: str,
               approved_amount: str = "0"):
        """Factory method to create a new token approval."""
        approval = cls(
            ID(approval_id),
            ID(wallet_id),
            ID(token_id),
            ApprovalAmount(approved_amount)
        )

        approval.events.append(
            events.TokenApprovalCreated(
                approval_id=approval.approval_id.value,
                wallet_id=approval.wallet_id.value,
                token_id=approval.token_id.value,
                approved_amount=approval.approved_amount.value
            )
        )
        return approval

    def update_amount(self, new_amount: str):
        """Update the approved amount."""
        old_amount = self.approved_amount.value
        self.approved_amount = ApprovalAmount(new_amount)
        self.updated_at = datetime.now(timezone.utc)

        self.events.append(
            events.TokenApprovalUpdated(
                approval_id=self.approval_id.value,
                wallet_id=self.wallet_id.value,
                token_id=self.token_id.value,
                previous_amount=old_amount,
                new_amount=self.approved_amount.value
            )
        )

    def has_sufficient_approval(self, required_amount: str) -> bool:
        """Check if the current approval is sufficient for the required amount."""
        return int(self.approved_amount.value) >= int(required_amount)


class ApprovalTransaction:
    """
    Represents a token approval or revoke approval transaction.

    Tracks the history of approval changes for audit and debugging purposes.
    """

    def __init__(self,
                 approval_transaction_id: ID,
                 transaction_id: ID,
                 token_id: ID,
                 amount: Amount,
                 previous_amount: Amount,
                 new_amount: Amount):
        self.approval_transaction_id = approval_transaction_id
        self.transaction_id = transaction_id
        self.token_id = token_id
        self.amount = amount
        self.previous_amount = previous_amount
        self.new_amount = new_amount
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
                        approval_transaction_id: str,
                        transaction_id: str,
                        token_id: str,
                        amount: str,
                        previous_amount: str = "0"):
        """Factory method to create an approval transaction."""
        new_amount = str(int(previous_amount) + int(amount))
        tx = cls(
            ID(approval_transaction_id),
            ID(transaction_id),
            ID(token_id),
            Amount(amount),
            Amount(previous_amount),
            Amount(new_amount)
        )

        tx.events.append(
            events.ApprovalTransactionCreated(
                approval_transaction_id=tx.approval_transaction_id.value,
                transaction_id=tx.transaction_id.value,
                token_id=tx.token_id.value,
                amount=tx.amount.value,
                previous_amount=tx.previous_amount.value,
                new_amount=tx.new_amount.value
            )
        )
        return tx


class SwapTransaction:
    """
    Represents a token swap transaction with all TraderJoe swap types.

    Contains detailed information about the swap including amounts, tokens,
    slippage tolerance, and router information.
    """

    def __init__(self,
                 swap_transaction_id: ID,
                 transaction_id: ID,
                 token_in_id: ID,
                 token_out_id: ID,
                 amount_in: Amount,
                 amount_out_expected: Amount,
                 slippage_tolerance: SlippageTolerance,
                 deadline: datetime,
                 router_address: Address,
                 amount_out_actual: Optional[Amount] = None):
        self.swap_transaction_id = swap_transaction_id
        self.transaction_id = transaction_id
        self.token_in_id = token_in_id
        self.token_out_id = token_out_id
        self.amount_in = amount_in
        self.amount_out_expected = amount_out_expected
        self.amount_out_actual = amount_out_actual
        self.slippage_tolerance = slippage_tolerance
        self.deadline = deadline
        self.router_address = router_address
        self.events = []

    @reconstructor
    def init_on_load(self):
        self.events = []

    @classmethod
    def create(cls,
                                     swap_transaction_id: str,
                                     transaction_id: str,
                                     token_out_id: str,
                                     amount_in: str,
                                     amount_out_expected: str,
                                     slippage_tolerance: str,
                                     deadline: datetime,
                                     router_address: str,
                                     native_token_id: str):
        """Factory method for exact native to token swap."""
        swap_tx = cls(
            ID(swap_transaction_id),
            ID(transaction_id),
            ID(native_token_id),  # AVAX
            ID(token_out_id),
            Amount(amount_in),
            Amount(amount_out_expected),
            SlippageTolerance(slippage_tolerance),
            deadline,
            Address(router_address)
        )

        swap_tx.events.append(
            events.SwapTransactionCreated(
                swap_transaction_id=swap_tx.swap_transaction_id.value,
                transaction_id=swap_tx.transaction_id.value,
                swap_type=swap_tx.swap_type.value,
                token_in_id=swap_tx.token_in_id.value,
                token_out_id=swap_tx.token_out_id.value,
                amount_in=swap_tx.amount_in.value,
                amount_out_expected=swap_tx.amount_out_expected.value
            )
        )
        return swap_tx

    def complete(self, amount_out_actual: str):
        """Mark the swap as completed with actual output amount."""
        self.amount_out_actual = Amount(amount_out_actual)

        self.events.append(
            events.SwapTransactionCompleted(
                swap_transaction_id=self.swap_transaction_id.value,
                transaction_id=self.transaction_id.value,
                amount_out_actual=self.amount_out_actual.value
            )
        )


if __name__ == "__main__":
    print("Transaction Service Domain Model")
