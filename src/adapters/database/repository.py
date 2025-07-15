from abc import ABC, abstractmethod
from typing import Set, Union, List
from sqlalchemy.ext.asyncio import async_session
from sqlalchemy import select
from src.domain.model import (
    ID,
    Wallet,
    Token, Symbol, Address,
    Transaction, TransactionHash,
    Swap,
    Approval, ApprovalAmount,
    ApprovalTransaction, ApprovalType,
    SwapTransaction, SwapType, Chain, TransactionStatus
)


class AbstractRepository(ABC):
    """
    Abstract repository for transaction service entities.

    Handles wallets, tokens, transactions, swaps, token approvals,
    approval transactions, and swap transactions.
    User data is not stored - only userid references.
    """

    def __init__(self):
        self.seen = set()  # type: Set[Union[Wallet, Token, Transaction, Swap, Approval, ApprovalTransaction, SwapTransaction, Chain]]

    # Wallet methods
    def add_wallet(self, wallet: Wallet):
        """Adds a wallet to the repository and marks it as seen."""
        self._add_wallet(wallet)
        self.seen.add(wallet)

    async def get_wallet(self, wallet_id: Union[ID, str]) -> Wallet | None:
        """Retrieves a wallet by its ID and marks it as seen if found."""
        wallet = await self._get_wallet(wallet_id)
        if wallet:
            self.seen.add(wallet)
        return wallet

    async def get_wallet_by_address(self, address: Union[Address, str]) -> Wallet | None:
        """Retrieves a wallet by its address and marks it as seen if found."""
        wallet = await self._get_wallet_by_address(address)
        if wallet:
            self.seen.add(wallet)
        return wallet

    async def get_wallet_by_userid(self, userid: Union[ID, str]) -> Wallet | None:
        """Retrieves the single wallet for a user (one wallet per user constraint)."""
        wallet = await self._get_wallet_by_userid(userid)
        if wallet:
            self.seen.add(wallet)
        return wallet

    def add_chain(self, chain: Chain):
        """Adds a token to the repository and marks it as seen."""
        self._add_chain(chain)
        self.seen.add(chain)

    async def get_chain(self, chain_id: Union[ID, str]) -> Chain | None:
        """Retrieves a token by its ID and marks it as seen if found."""
        chain = await self._get_chain(chain_id)
        if chain:
            self.seen.add(chain)
        return chain

    async def get_chain_by_symbol(self, symbol: Union[Symbol, str]) -> Chain | None:
        """Retrieves a token by its symbol and network."""
        token = await self._get_chain_by_symbol(symbol)
        if token:
            self.seen.add(token)
        return token

    async def get_supported_chains(self) -> List[Chain]:
        chains = await self._get_supported_chains()
        for chain in chains:
            self.seen.add(chain)
        return chains
    # Token methods
    def add_token(self, token: Token):
        """Adds a token to the repository and marks it as seen."""
        self._add_token(token)
        self.seen.add(token)

    async def get_token(self, token_id: Union[ID, str]) -> Token | None:
        """Retrieves a token by its ID and marks it as seen if found."""
        token = await self._get_token(token_id)
        if token:
            self.seen.add(token)
        return token

    async def get_token_by_symbol(self, symbol: Union[Symbol, str]) -> Token | None:
        """Retrieves a token by its symbol and network."""
        token = await self._get_token_by_symbol(symbol)
        if token:
            self.seen.add(token)
        return token

    async def get_token_by_contract(self, contract_address: Union[Address, str]) -> Token | None:
        """Retrieves a token by its contract address."""
        token = await self._get_token_by_contract(contract_address)
        if token:
            self.seen.add(token)
        return token

    async def get_supported_tokens(self,) -> List[Token]:
        """Retrieves all supported tokens for a network."""
        tokens = await self._get_supported_tokens()
        for token in tokens:
            self.seen.add(token)
        return tokens

    # Transaction methods
    def add_transaction(self, transaction: Transaction):
        """Adds a transaction to the repository and marks it as seen."""
        self._add_transaction(transaction)
        self.seen.add(transaction)

    async def get_transaction(self, transaction_id: Union[ID, str]) -> Transaction | None:
        """Retrieves a transaction by its ID and marks it as seen if found."""
        transaction = await self._get_transaction(transaction_id)
        if transaction:
            self.seen.add(transaction)
        return transaction

    async def get_transaction_by_hash(self, transaction_hash: Union[TransactionHash, str]) -> Transaction | None:
        """Retrieves a transaction by its hash and marks it as seen if found."""
        transaction = await self._get_transaction_by_hash(transaction_hash)
        if transaction:
            self.seen.add(transaction)
        return transaction

    async def get_user_transactions(self, userid: Union[ID, str], limit: int = 50) -> List[Transaction]:
        """Retrieves transactions for a user and marks them as seen."""
        transactions = await self._get_user_transactions(userid, limit)
        for transaction in transactions:
            self.seen.add(transaction)
        return transactions

    async def get_pending_transactions(self) -> List[Transaction]:
        """Retrieves all pending transactions for monitoring."""
        transactions = await self._get_pending_transactions()
        for transaction in transactions:
            self.seen.add(transaction)
        return transactions

    # Swap methods
    def add_swap(self, swap: Swap):
        """Adds a swap to the repository and marks it as seen."""
        self._add_swap(swap)
        self.seen.add(swap)

    async def get_swap(self, swap_id: Union[ID, str]) -> Swap | None:
        """Retrieves a swap by its ID and marks it as seen if found."""
        swap = await self._get_swap(swap_id)
        if swap:
            self.seen.add(swap)
        return swap

    async def get_swap_by_transaction_id(self, transaction_id: Union[ID, str]) -> Swap | None:
        """Retrieves a swap by its transaction ID and marks it as seen if found."""
        swap = await self._get_swap_by_transaction_id(transaction_id)
        if swap:
            self.seen.add(swap)
        return swap

    # Token Approval methods
    def add_token_approval(self, token_approval: Approval):
        """Adds a token approval to the repository and marks it as seen."""
        self._add_token_approval(token_approval)
        self.seen.add(token_approval)

    async def get_token_approval(self, approval_id: Union[ID, str]) -> Approval | None:
        """Retrieves a token approval by its ID and marks it as seen if found."""
        approval = await self._get_token_approval(approval_id)
        if approval:
            self.seen.add(approval)
        return approval


    # Approval Transaction methods
    def add_approval_transaction(self, approval_transaction: ApprovalTransaction):
        """Adds an approval transaction to the repository and marks it as seen."""
        self._add_approval_transaction(approval_transaction)
        self.seen.add(approval_transaction)

    async def get_approval_transaction(self, approval_transaction_id: Union[ID, str]) -> ApprovalTransaction | None:
        """Retrieves an approval transaction by its ID and marks it as seen if found."""
        approval_tx = await self._get_approval_transaction(approval_transaction_id)
        if approval_tx:
            self.seen.add(approval_tx)
        return approval_tx

    async def get_last_confirmed_transaction(self, chain_id: Union[ID, str], wallet_id: Union[ID,str]) -> Transaction:
        nonce = await self._get_last_confirmed_transaction(chain_id, wallet_id)
        return nonce


    # Abstract methods for implementation
    @abstractmethod
    def _add_wallet(self, wallet: Wallet):
        raise NotImplementedError

    @abstractmethod
    async def _get_wallet(self, wallet_id: Union[ID, str]) -> Wallet | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_wallet_by_address(self, address: Union[Address, str]) -> Wallet | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_wallet_by_userid(self, userid: Union[ID, str]) -> Wallet | None:
        raise NotImplementedError

    @abstractmethod
    def _add_chain(self, chain: Chain):
        raise NotImplementedError

    @abstractmethod
    async def _get_chain(self, chain_id: Union[ID, str]) -> Chain | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_chain_by_symbol(self, symbol: Union[Symbol, str]) -> Chain | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_supported_chains(self) -> List[Chain]:
        raise NotImplementedError

    @abstractmethod
    def _add_token(self, token: Token):
        raise NotImplementedError

    @abstractmethod
    async def _get_token(self, token_id: Union[ID, str]) -> Token | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_token_by_symbol(self, symbol: Union[Symbol, str]) -> Token | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_token_by_contract(self, contract_address: Union[Address, str]) -> Token | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_supported_tokens(self) -> List[Token]:
        raise NotImplementedError

    @abstractmethod
    def _add_transaction(self, transaction: Transaction):
        raise NotImplementedError

    @abstractmethod
    async def _get_transaction(self, transaction_id: Union[ID, str]) -> Transaction | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_transaction_by_hash(self, transaction_hash: Union[TransactionHash, str]) -> Transaction | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_user_transactions(self, userid: Union[ID, str], limit: int) -> List[Transaction]:
        raise NotImplementedError

    @abstractmethod
    async def _get_pending_transactions(self) -> List[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def _add_swap(self, swap: Swap):
        raise NotImplementedError

    @abstractmethod
    def _get_swap(self, swap_id: Union[ID, str]) -> Swap | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_swap_by_transaction_id(self, transaction_id: Union[ID, str]) -> Swap | None:
        raise NotImplementedError

    @abstractmethod
    def _add_token_approval(self, token_approval: Approval):
        raise NotImplementedError

    @abstractmethod
    async def _get_token_approval(self, approval_id: Union[ID, str]) -> Approval | None:
        raise NotImplementedError

    @abstractmethod
    def _add_approval_transaction(self, approval_transaction: ApprovalTransaction):
        raise NotImplementedError

    @abstractmethod
    async def _get_approval_transaction(self, approval_transaction_id: Union[ID, str]) -> ApprovalTransaction | None:
        raise NotImplementedError

    @abstractmethod
    async def _get_last_confirmed_transaction(self, chain_id: Union[ID, str], wallet_id: Union[ID, str]) -> Transaction:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    """
    SQLAlchemy implementation of the transaction service repository.

    Provides concrete implementations for all transaction-related operations
    including the new token approval and swap transaction repositories.
    """

    def __init__(self, session: async_session):
        super().__init__()
        self.session = session

    # Wallet implementations
    def _add_wallet(self, wallet: Wallet):
        self.session.add(wallet)

    async def _get_wallet(self, wallet_id: Union[ID, str]) -> Wallet | None:
        wallet_id = wallet_id if isinstance(wallet_id, ID) else ID(wallet_id)
        stmt = select(Wallet).where(Wallet.wallet_id == wallet_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_wallet_by_address(self, address: Union[Address, str]) -> Wallet | None:
        address = address if isinstance(address, Address) else Address(address)
        stmt = select(Wallet).where(Wallet.address == address)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_wallet_by_userid(self, userid: Union[ID, str]) -> Wallet | None:
        userid = userid if isinstance(userid, ID) else ID(userid)
        stmt = select(Wallet).where(Wallet.userid == userid)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _add_chain(self, chain: Chain):
        self.session.add(chain)

    async def _get_chain(self, chain_id: Union[ID, str]) -> Chain | None:
        chain_id = chain_id if isinstance(chain_id, ID) else ID(chain_id)
        stmt = select(Chain).where(Chain.chain_id == chain_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_chain_by_symbol(self, symbol: Union[Symbol, str]) -> Chain | None:
        symbol = symbol if isinstance(symbol, Symbol) else Symbol(symbol)
        stmt = select(Chain).where(Chain.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_supported_chains(self) -> List[Chain]:
        stmt = select(Chain)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Token implementations
    def _add_token(self, token: Token):
        self.session.add(token)

    async def _get_token(self, token_id: Union[ID, str]) -> Token | None:
        token_id = token_id if isinstance(token_id, ID) else ID(token_id)
        stmt = select(Token).where(Token.token_id == token_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_token_by_symbol(self, symbol: Union[Symbol, str]) -> Token | None:
        symbol = symbol if isinstance(symbol, Symbol) else Symbol(symbol)
        stmt = select(Token).where(Token.symbol == symbol)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_token_by_contract(self, contract_address: Union[Address, str]) -> Token | None:
        contract_address = contract_address if isinstance(contract_address, Address) else Address(contract_address)
        stmt = select(Token).where(Token.contract_address == contract_address)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_supported_tokens(self) -> List[Token]:
        stmt = select(Token)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Transaction implementations
    def _add_transaction(self, transaction: Transaction):
        self.session.add(transaction)

    async def _get_transaction(self, transaction_id: Union[ID, str]) -> Transaction | None:
        transaction_id = transaction_id if isinstance(transaction_id, ID) else ID(transaction_id)
        stmt = select(Transaction).where(Transaction.transaction_id == transaction_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_transaction_by_hash(self, transaction_hash: Union[TransactionHash, str]) -> Transaction | None:
        transaction_hash = transaction_hash if isinstance(transaction_hash, TransactionHash) else TransactionHash(
            transaction_hash)
        stmt = select(Transaction).where(Transaction.transaction_hash == transaction_hash)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_user_transactions(self, userid: Union[ID, str], limit: int) -> List[Transaction]:
        userid = userid if isinstance(userid, ID) else ID(userid)
        stmt = (
            select(Transaction)
            .where(Transaction.userid == userid)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_pending_transactions(self) -> List[Transaction]:
        stmt = select(Transaction).where(Transaction.status == TransactionStatus.PENDING)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Swap implementations
    def _add_swap(self, swap: Swap):
        self.session.add(swap)

    async def _get_swap(self, swap_id: Union[ID, str]) -> Swap | None:
        swap_id = swap_id if isinstance(swap_id, ID) else ID(swap_id)
        stmt = select(Swap).where(Swap.swap_id == swap_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_swap_by_transaction_id(self, transaction_id: Union[ID, str]) -> Swap | None:
        transaction_id = transaction_id if isinstance(transaction_id, ID) else ID(transaction_id)
        stmt = select(Swap).where(Swap.transaction_id == transaction_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # Token Approval implementations
    def _add_token_approval(self, token_approval: Approval):
        self.session.add(token_approval)

    async def _get_token_approval(self, approval_id: Union[ID, str]) -> Approval | None:
        approval_id = approval_id if isinstance(approval_id, ID) else ID(approval_id)
        stmt = select(Approval).where(Approval.approval_id == approval_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # Approval Transaction implementations
    def _add_approval_transaction(self, approval_transaction: ApprovalTransaction):
        self.session.add(approval_transaction)

    async def _get_approval_transaction(self, approval_transaction_id: Union[ID, str]) -> ApprovalTransaction | None:
        approval_transaction_id = approval_transaction_id if isinstance(approval_transaction_id, ID) else ID(approval_transaction_id)
        stmt = select(ApprovalTransaction).where(ApprovalTransaction.approval_transaction_id == approval_transaction_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _get_last_confirmed_transaction(self, chain_id: Union[ID, str], wallet_id: Union[ID, str]) -> Transaction:
        chain_id = chain_id if isinstance(chain_id, ID) else ID(chain_id)
        wallet_id = wallet_id if isinstance(wallet_id, ID) else ID(wallet_id)
        stmt = select(Transaction).where(
            Transaction.chain_id == chain_id,
            Transaction.wallet_id == wallet_id,
            Transaction.transaction_status == TransactionStatus.CONFIRMED
        ).order_by(Transaction.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()
