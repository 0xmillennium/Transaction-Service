from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from src.domain import commands
from src.domain.model import Address
from src.service_layer import messagebus, views, unit_of_work

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transaction", tags=["Transactions"])
security = HTTPBearer()


# Request/Response Models

# Wallet Models
class CreateWalletRequest(BaseModel):
    pass  # No additional fields needed - one wallet per user

class WalletResponse(BaseModel):
    wallet_id: str
    userid: str
    address: str
    is_active: bool
    created_at: str

# Token Management Models
class AddTokenRequest(BaseModel):
    chain_id: str = Field(..., description="Unique identifier for the chain (e.g., '41125')")
    symbol: str = Field(..., description="Token symbol (e.g., 'USDC', 'AVAX')")
    name: str = Field(..., description="Token full name")
    contract_address: Optional[str] = Field( description="Contract address")
    decimals: str = Field("18", description="Token decimals")

class TokenResponse(BaseModel):
    token_id: str
    chain_id: str
    symbol: str
    name: str
    contract_address: Optional[str]
    decimals: str

# Chain Management Models
class AddChainRequest(BaseModel):
    chain_id: str = Field(..., description="Unique identifier for the chain (e.g., 'avax')")
    name: str = Field(..., description="Full name of the chain (e.g., 'Avalanche')")
    symbol: str = Field(..., description="Symbol for the native token (e.g., 'AVAX')")
    rpc_url: str = Field(..., description="RPC URL for interacting with the chain")

class ChainResponse(BaseModel):
    chain_id: str
    name: str
    symbol: str
    rpc_url: str


# Token Approval Models
class ApproveTokenRequest(BaseModel):
    token_id: str = Field(..., description="Token ID to approve")
    spender_address: Address = Field(description="Address to approve spending")
    amount: int = Field(..., description="Amount to approve in wei")

class RevokeApprovalRequest(BaseModel):
    token_id: str = Field(..., description="Token ID to revoke approval for")
    amount: Optional[str] = Field(None, description="Amount to revoke (None means revoke all)")

class ApprovalResponse(BaseModel):
    approval_id: str
    wallet_id: str
    token_id: str
    approved_amount: str
    updated_at: str

class ApprovalHistoryResponse(BaseModel):
    approval_transaction_id: str
    transaction_id: str
    token_id: str
    approval_type: str
    amount: str
    previous_amount: str
    new_amount: str

class ApprovalStatusResponse(BaseModel):
    sufficient: bool
    current_amount: str
    required_amount: str
    error: Optional[str] = None

# Swap Models
class SwapExactNativeToTokenRequest(BaseModel):
    token_out_id: str = Field(..., description="Output token ID")
    amount_in: str = Field(..., description="Exact AVAX amount to swap (in wei)")
    amount_out_min: str = Field(..., description="Minimum tokens to receive")
    slippage_tolerance: str = Field("0.5", description="Slippage tolerance percentage")
    deadline_minutes: int = Field(20, ge=1, le=60, description="Transaction deadline in minutes")

class SwapTokenToExactNativeRequest(BaseModel):
    token_in_id: str = Field(..., description="Input token ID")
    amount_in: str = Field(..., description="Token amount to swap")
    amount_out_min: str = Field(..., description="Minimum AVAX to receive (in wei)")
    slippage_tolerance: str = Field("0.5", description="Slippage tolerance percentage")
    deadline_minutes: int = Field(20, ge=1, le=60, description="Transaction deadline in minutes")

class SwapExactTokenToTokenRequest(BaseModel):
    token_in_id: str = Field(..., description="Input token ID")
    token_out_id: str = Field(..., description="Output token ID")
    amount_in: str = Field(..., description="Exact token amount to swap")
    amount_out_min: str = Field(..., description="Minimum tokens to receive")
    slippage_tolerance: str = Field("0.5", description="Slippage tolerance percentage")
    deadline_minutes: int = Field(20, ge=1, le=60, description="Transaction deadline in minutes")

class SwapTokenToExactTokenRequest(BaseModel):
    token_in_id: str = Field(..., description="Input token ID")
    token_out_id: str = Field(..., description="Output token ID")
    amount_in_max: str = Field(..., description="Maximum tokens to spend")
    amount_out: str = Field(..., description="Exact tokens to receive")
    slippage_tolerance: str = Field("0.5", description="Slippage tolerance percentage")
    deadline_minutes: int = Field(20, ge=1, le=60, description="Transaction deadline in minutes")

class SwapQuoteRequest(BaseModel):
    token_in_id: str = Field(..., description="Input token ID")
    token_out_id: str = Field(..., description="Output token ID")
    amount_in: str = Field(..., description="Input amount")
    slippage_tolerance: str = Field("0.5", description="Slippage tolerance percentage")

class SwapQuoteResponse(BaseModel):
    token_in: Dict[str, Any]
    token_out: Dict[str, Any]
    amount_in: str
    amount_out: str
    minimum_amount_out: str
    price_impact: str
    slippage_tolerance: str

class SwapTransactionResponse(BaseModel):
    swap_transaction_id: str
    transaction_id: str
    swap_type: str
    token_in_id: str
    token_out_id: str
    amount_in: str
    amount_out_expected: str
    amount_out_actual: Optional[str]
    slippage_tolerance: str
    deadline: str
    router_address: str

class TransactionResponse(BaseModel):
    transaction_id: str
    transaction_hash: Optional[str]
    transaction_type: str
    status: str
    gas_limit: Optional[str]
    gas_price: Optional[str]
    gas_used: Optional[str]
    created_at: str
    updated_at: Optional[str]
    confirmed_at: Optional[str]
    error_message: Optional[str]

# Legacy Models (keeping for backward compatibility)
class CreateSwapRequest(BaseModel):
    token_in_id: str
    token_out_id: str
    amount_in: str
    slippage_tolerance: str = Field(default="0.5")
    deadline_minutes: int = Field(default=20, ge=1, le=60)
    network: str = Field(default="avalanche", description="Target blockchain network for the swap")

class CreateSwapResponse(BaseModel):
    transaction_id: str
    swap_id: str
    status: str
    estimated_gas: Dict[str, Any]

class SwapResponse(BaseModel):
    swap_id: str
    transaction_id: str
    token_in_symbol: str
    token_out_symbol: str
    amount_in: str
    amount_out_expected: str
    amount_out_actual: Optional[str]
    slippage_tolerance: str
    deadline: str
    status: str
    transaction_hash: Optional[str]

class SwapDetailResponse(BaseModel):
    swap_id: str
    transaction_id: str
    token_in_id: str
    token_out_id: str
    amount_in: str
    amount_out_expected: str
    amount_out_actual: Optional[str]
    slippage_tolerance: str
    trader_joe_router: str
    deadline: Optional[str]

class TransactionStatusResponse(BaseModel):
    transaction_id: str
    status: str
    transaction_hash: Optional[str]
    created_at: str
    confirmed_at: Optional[str]
    error_message: Optional[str]

class TokenBalanceInfo(BaseModel):
    token_id: str
    symbol: str
    name: str
    balance: str
    contract_address: Optional[str]
    decimals: str

class WalletBalanceSummaryResponse(BaseModel):
    wallet_id: str
    address: str
    network: str
    tokens: List[TokenBalanceInfo]

class WalletBalanceResponse(BaseModel):
    wallet_id: str
    token_id: Optional[str]
    token_symbol: str
    balance: str
    decimals: str


# TraderJoe Swap Models
class TraderJoeSwapRequest(BaseModel):
    strategy: str = Field(..., description="Swap strategy: 'fast', 'cheap', or 'secure'")
    token_from: str = Field(..., description="Token to sell (address or 'NATIVE')")
    token_to: str = Field(..., description="Token to buy (address or 'NATIVE')")
    amount_in: str = Field(..., description="Amount to swap (in wei)")
    max_slippage_percent: float = Field(..., description="Maximum slippage percentage (e.g., 3.0 for 3%)")
    chain_id: str = Field("43114", description="Chain ID (default: Avalanche)")
    router_address: str = Field("0xb4315e873dBcf96Ffd0acd8EA43f689D8c20fB30", description="TraderJoe Router address")
    factory_address: str = Field("0x8e42f2F4101563bF679975178e880FD87d3eFd4e", description="TraderJoe Factory address")

class TraderJoeSwapResponse(BaseModel):
    swap_id: str
    transaction_hash: str
    status: str


async def get_userid(request: Request) -> str:
    return request.app.state.userid if hasattr(request.app.state, "userid") else "a1b2c3d4e5f6789012345678901234ab"


# Dependency to get standby unit of work for read operations
def get_suow(request: Request) -> unit_of_work.AbstractUnitOfWork:
    return request.app.state.suow


# Dependency to get messagebus from app state
def get_messagebus(request: Request) -> messagebus.MessageBus:
    return request.app.state.messagebus


# Wallet Endpoints
@router.post("/wallets")
async def create_wallet(
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Create a new wallet for the authenticated user."""
    try:
        cmd = commands.CreateWalletCommand(
            userid=userid,
        )

        await bus.handle(cmd)

        return "OK"
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/wallet", response_model=WalletResponse)
async def get_user_wallet(
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get the user's wallet (one wallet per user)."""
    try:
        wallet = await views.get_user_wallet_view(userid, suow)
        if not wallet:
            raise HTTPException(status_code=404, detail="User wallet not found")
        return wallet
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Wallet Management Endpoints
@router.post("/wallet/activate")
async def activate_wallet(
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Activate a user's wallet."""
    try:
        cmd = commands.ActivateWalletCommand(
            userid=userid
        )

        await bus.handle(cmd)
        return {"message": f"Wallet activated successfully"}
    except Exception as e:
        logger.error(f"Error activating wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wallet/deactivate")
async def deactivate_wallet(
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Deactivate a user's wallet."""
    try:
        cmd = commands.DeactivateWalletCommand(
            userid=userid
        )

        await bus.handle(cmd)
        return {"message": f"Wallet deactivated successfully"}
    except Exception as e:
        logger.error(f"Error deactivating wallet: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ===== NEW TRADERJOE-SPECIFIC ENDPOINTS =====

# Token Management Endpoints (Admin/System level)
@router.post("/admin/tokens", response_model=Dict[str, str])
async def add_token(
    token_request: AddTokenRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus)
):
    """Add a new supported token for TraderJoe swaps (Admin endpoint)."""
    try:
        cmd = commands.AddTokenCommand(
            chain_id=token_request.chain_id,
            symbol=token_request.symbol,
            name=token_request.name,
            contract_address=token_request.contract_address,
            decimals=token_request.decimals,
        )

        await bus.handle(cmd)
        return {"message": f"Token {token_request.symbol} added successfully"}
    except Exception as e:
        logger.error(f"Error adding token: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Token Query Endpoints
@router.get("/tokens/avalanche", response_model=List[TokenResponse])
async def get_supported_tokens(
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get all supported tokens for TraderJoe swaps on Avalanche."""
    try:
        tokens = await views.get_supported_tokens_view(suow)
        return tokens
    except Exception as e:
        logger.error(f"Error getting supported tokens: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tokens/symbol/{symbol}", response_model=TokenResponse)
async def get_token_by_symbol(
    symbol: str,
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get token by symbol."""
    try:
        token = await views.get_token_by_symbol_view(symbol, suow)
        if not token:
            raise HTTPException(status_code=404, detail=f"Token '{symbol}' not found")
        return token
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting token by symbol: {e}")
        raise HTTPException(status_code=400, detail=str(e))

#Chain Management Endpoints
@router.post("/admin/chains", response_model=Dict[str, str])
async def add_chain(
        chain_request: AddChainRequest,
        bus: messagebus.MessageBus = Depends(get_messagebus)
):
    """Add a new blockchain chain (Admin endpoint)."""
    try:
        cmd = commands.AddChainCommand(
            chain_id=chain_request.chain_id,
            name=chain_request.name,
            symbol=chain_request.symbol,
            rpc_url=chain_request.rpc_url
        )

        await bus.handle(cmd)
        return {"message": f"Chain {chain_request.name} added successfully"}
    except Exception as e:
        logger.error(f"Error adding chain: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/chains/{chain_id}", response_model=ChainResponse)
async def get_chain_by_symbol(
    symbol: str,
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get blockchain by symbol."""
    try:
        chain = await views.get_chain_by_symbol_view(symbol, suow)
        if not chain:
            raise HTTPException(status_code=404, detail=f"Chain '{symbol}' not found")
        return chain
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chain by symbol: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/chains", response_model=List[ChainResponse])
async def get_supported_chains(
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get all supported blockchain chains."""
    try:
        chains = await views.get_supported_chains_view(suow)
        return chains
    except Exception as e:
        logger.error(f"Error getting supported chains: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Token Approval Endpoints
@router.post("/approvals")
async def approve_token(
    approval_request: ApproveTokenRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Manually approve a specific amount for a token."""
    try:
        cmd = commands.ApproveTokenCommand(
            userid=userid,
            token_id=approval_request.token_id,
            spender_address=approval_request.spender_address,
            amount=approval_request.amount
        )

        await bus.handle(cmd)
        return {"message": "Token approval initiated successfully"}
    except Exception as e:
        logger.error(f"Error approving token: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approvals/revoke")
async def revoke_approval(
    revoke_request: RevokeApprovalRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Revoke token approval (set to 0 or reduce by amount)."""
    try:
        cmd = commands.RevokeApprovalCommand(
            userid=userid,
            token_id=revoke_request.token_id,
            amount=revoke_request.amount
        )

        await bus.handle(cmd)
        return {"message": "Token approval revocation initiated successfully"}
    except Exception as e:
        logger.error(f"Error revoking approval: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approvals", response_model=List[ApprovalResponse])
async def get_user_approvals(
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get all current token approvals for the authenticated user."""
    try:
        approvals = await views.get_user_approvals_view(userid, suow)
        return approvals
    except Exception as e:
        logger.error(f"Error getting user approvals: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approvals/history", response_model=List[ApprovalHistoryResponse])
async def get_approval_history(
    token_id: Optional[str] = Query(None, description="Filter by token ID"),
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get approval transaction history for the authenticated user."""
    try:
        history = await views.get_approval_history_view(userid, token_id, suow)
        return history
    except Exception as e:
        logger.error(f"Error getting approval history: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approvals/check", response_model=ApprovalStatusResponse)
async def check_approval_status(
    token_id: str = Query(..., description="Token ID to check"),
    required_amount: str = Query(..., description="Required amount in wei"),
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Check if user has sufficient approval for a token amount."""
    try:
        status = await views.check_approval_status_view(userid, token_id, required_amount, suow)
        return status
    except Exception as e:
        logger.error(f"Error checking approval status: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# TraderJoe Swap Endpoints
@router.post("/swaps/exact-native-to-token")
async def swap_exact_native_to_token(
    swap_request: SwapExactNativeToTokenRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute EXACT_NATIVE_TO_TOKEN swap (AVAX -> Token)."""
    try:
        cmd = commands.SwapExactNativeToTokenCommand(
            userid=userid,
            token_out_id=swap_request.token_out_id,
            amount_in=swap_request.amount_in,
            amount_out_min=swap_request.amount_out_min,
            slippage_tolerance=swap_request.slippage_tolerance,
            deadline_minutes=swap_request.deadline_minutes
        )

        await bus.handle(cmd)
        return {"message": "EXACT_NATIVE_TO_TOKEN swap initiated successfully"}
    except Exception as e:
        logger.error(f"Error executing native to token swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/swaps/token-to-exact-native")
async def swap_token_to_exact_native(
    swap_request: SwapTokenToExactNativeRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute TOKEN_TO_EXACT_NATIVE swap (Token -> AVAX)."""
    try:
        cmd = commands.SwapTokenToExactNativeCommand(
            userid=userid,
            token_in_id=swap_request.token_in_id,
            amount_in=swap_request.amount_in,
            amount_out_min=swap_request.amount_out_min,
            slippage_tolerance=swap_request.slippage_tolerance,
            deadline_minutes=swap_request.deadline_minutes
        )

        await bus.handle(cmd)
        return {"message": "TOKEN_TO_EXACT_NATIVE swap initiated successfully"}
    except Exception as e:
        logger.error(f"Error executing token to native swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/swaps/exact-token-to-token")
async def swap_exact_token_to_token(
    swap_request: SwapExactTokenToTokenRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute EXACT_TOKEN_TO_TOKEN swap."""
    try:
        cmd = commands.SwapExactTokenToTokenCommand(
            userid=userid,
            token_in_id=swap_request.token_in_id,
            token_out_id=swap_request.token_out_id,
            amount_in=swap_request.amount_in,
            amount_out_min=swap_request.amount_out_min,
            slippage_tolerance=swap_request.slippage_tolerance,
            deadline_minutes=swap_request.deadline_minutes
        )

        await bus.handle(cmd)
        return {"message": "EXACT_TOKEN_TO_TOKEN swap initiated successfully"}
    except Exception as e:
        logger.error(f"Error executing token to token swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/swaps/token-to-exact-token")
async def swap_token_to_exact_token(
    swap_request: SwapTokenToExactTokenRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute TOKEN_TO_EXACT_TOKEN swap."""
    try:
        cmd = commands.SwapTokenToExactTokenCommand(
            userid=userid,
            token_in_id=swap_request.token_in_id,
            token_out_id=swap_request.token_out_id,
            amount_in_max=swap_request.amount_in_max,
            amount_out=swap_request.amount_out,
            slippage_tolerance=swap_request.slippage_tolerance,
            deadline_minutes=swap_request.deadline_minutes
        )

        await bus.handle(cmd)
        return {"message": "TOKEN_TO_EXACT_TOKEN swap initiated successfully"}
    except Exception as e:
        logger.error(f"Error executing exact token swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Swap History Endpoints
@router.get("/swaps/history", response_model=List[SwapTransactionResponse])
async def get_user_swap_transaction_history(
    limit: int = Query(default=50, ge=1, le=100),
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get detailed swap transaction history for the authenticated user."""
    try:
        swaps = await views.get_user_swap_history_view(userid, limit, suow)
        return swaps
    except Exception as e:
        logger.error(f"Error getting user swap transaction history: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tokens/{token_id}/swaps", response_model=List[SwapTransactionResponse])
async def get_token_swap_history(
    token_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get swap history for a specific token."""
    try:
        swaps = await views.get_token_swap_history_view(token_id, limit, suow)
        return swaps
    except Exception as e:
        logger.error(f"Error getting token swap history: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/{transaction_id}/status", response_model=TransactionStatusResponse)
async def get_transaction_status(
    transaction_id: str,
    userid: str = Depends(get_userid),
    suow: unit_of_work.AbstractUnitOfWork = Depends(get_suow)
):
    """Get status of a specific transaction."""
    try:
        transaction = await views.get_transaction_status(transaction_id, suow)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Get the full transaction to check ownership
        full_transaction = views.get_transaction_by_id(transaction_id, suow)
        if full_transaction and full_transaction["userid"] != userid:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "transaction_id": transaction["transaction_id"],
            "status": transaction["status"],
            "transaction_hash": transaction["transaction_hash"],
            "created_at": transaction["created_at"],
            "confirmed_at": transaction["confirmed_at"],
            "error_message": transaction["error_message"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transaction status: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# TraderJoe Strategy-Based Swap Endpoints
@router.post("/traderjoe/swap/fast", response_model=TraderJoeSwapResponse)
async def traderjoe_swap_fast(
    swap_request: TraderJoeSwapRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute a fast TraderJoe swap optimized for speed."""
    try:
        cmd = commands.ExecuteSwapCommand(
            userid=userid,
            strategy="fast",
            token_from=swap_request.token_from,
            token_to=swap_request.token_to,
            amount_in=swap_request.amount_in,
            max_slippage_percent=swap_request.max_slippage_percent,
            chain_id=swap_request.chain_id,
            router_address=swap_request.router_address,
            factory_address=swap_request.factory_address
        )

        result = await bus.handle(cmd)
        return TraderJoeSwapResponse(
            swap_id=result.get("swap_id", "unknown"),
            transaction_hash=result.get("transaction_hash", "pending"),
            status="initiated"
        )
    except Exception as e:
        logger.error(f"Error executing fast TraderJoe swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/traderjoe/swap/cheap", response_model=TraderJoeSwapResponse)
async def traderjoe_swap_cheap(
    swap_request: TraderJoeSwapRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute a cheap TraderJoe swap optimized for lowest fees."""
    try:
        cmd = commands.ExecuteSwapCommand(
            userid=userid,
            strategy="cheap",
            token_from=swap_request.token_from,
            token_to=swap_request.token_to,
            amount_in=swap_request.amount_in,
            max_slippage_percent=swap_request.max_slippage_percent,
            chain_id=swap_request.chain_id,
            router_address=swap_request.router_address,
            factory_address=swap_request.factory_address
        )

        result = await bus.handle(cmd)
        return TraderJoeSwapResponse(
            swap_id=result.get("swap_id", "unknown"),
            transaction_hash=result.get("transaction_hash", "pending"),
            status="initiated"
        )
    except Exception as e:
        logger.error(f"Error executing cheap TraderJoe swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/traderjoe/swap/secure", response_model=TraderJoeSwapResponse)
async def traderjoe_swap_secure(
    swap_request: TraderJoeSwapRequest,
    bus: messagebus.MessageBus = Depends(get_messagebus),
    userid: str = Depends(get_userid)
):
    """Execute a secure TraderJoe swap optimized for safety and reliability."""
    try:
        cmd = commands.ExecuteSwapCommand(
            userid=userid,
            strategy="secure",
            token_from=swap_request.token_from,
            token_to=swap_request.token_to,
            amount_in=swap_request.amount_in,
            max_slippage_percent=swap_request.max_slippage_percent,
            chain_id=swap_request.chain_id,
            router_address=swap_request.router_address,
            factory_address=swap_request.factory_address
        )

        result = await bus.handle(cmd)
        return TraderJoeSwapResponse(
            swap_id=result.get("swap_id", "unknown"),
            transaction_hash=result.get("transaction_hash", "pending"),
            status="initiated"
        )
    except Exception as e:
        logger.error(f"Error executing secure TraderJoe swap: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for the transaction service."""
    return {
        "status": "healthy",
        "service": "transaction-service",
        "timestamp": datetime.now(timezone.utc)
    }
