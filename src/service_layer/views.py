from typing import List, Dict, Any, Optional
from src.service_layer import unit_of_work
from datetime import datetime
import time
from pydantic.dataclasses import dataclass
from src.adapters.message_broker.connection_manager import AbstractConnectionManager, ConnectionMetrics, HealthMetrics
from src.service_layer.blockchain_service import BlockchainService
from src.service_layer.token_management_service import TokenManagementService
from src.service_layer.wallet_service import WalletService

@dataclass
class AlertsResponse:
    timestamp: datetime
    critical_alerts: List[str]
    warning_alerts: List[str]
    info_alerts: List[str]

async def get_user_wallets(userid: str, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all wallets for a user (should return only one wallet per user)."""
    with suow:
        wallets = suow.repo.get_user_wallets(userid)
        return [
            {
                "wallet_id": wallet.wallet_id.value,
                "userid": wallet.userid.value,
                "address": wallet.address.value,
                "is_active": wallet.is_active,
                "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                # Removed network field - wallet works across all networks
            }
            for wallet in wallets
        ]


async def get_supported_tokens(network: str, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all supported tokens for a network."""
    with suow:
        tokens = suow.repo.get_active_tokens(network)
        return [
            {
                "token_id": token.token_id.value,
                "symbol": token.symbol.value,
                "name": token.name.value,
                "contract_address": token.contract_address.value,
                "decimals": token.decimals.value,
                "network": token.network,
                "is_native": token.is_native
            }
            for token in tokens
        ]


async def get_user_transactions(userid: str, limit: int, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get transaction history for a user."""
    with suow:
        transactions = suow.repo.get_user_transactions(userid, limit)
        return [
            {
                "transaction_id": tx.transaction_id.value,
                "transaction_hash": tx.transaction_hash.value if tx.transaction_hash else None,
                "transaction_type": tx.transaction_type.value,
                "status": tx.status.value,
                "network": tx.network,
                "gas_limit": tx.gas_limit,
                "gas_price": tx.gas_price,
                "gas_used": tx.gas_used,
                "created_at": tx.created_at,
                "updated_at": tx.updated_at,
                "confirmed_at": tx.confirmed_at,
                "error_message": tx.error_message
            }
            for tx in transactions
        ]


async def get_transaction_status(transaction_id: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get status of a specific transaction."""
    with suow:
        transaction = suow.repo.get_transaction(transaction_id)
        if not transaction:
            return None

        return {
            "transaction_id": transaction.transaction_id.value,
            "transaction_hash": transaction.transaction_hash.value if transaction.transaction_hash else None,
            "transaction_type": transaction.transaction_type.value,
            "status": transaction.status.value,
            "network": transaction.network,
            "gas_limit": transaction.gas_limit,
            "gas_price": transaction.gas_price,
            "gas_used": transaction.gas_used,
            "created_at": transaction.created_at,
            "updated_at": transaction.updated_at,
            "confirmed_at": transaction.confirmed_at,
            "error_message": transaction.error_message
        }


async def get_user_swap_history(userid: str, limit: int, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get swap history for a user."""
    with suow:
        transactions = suow.repo.get_user_transactions(userid, limit)
        swap_transactions = [tx for tx in transactions if tx.transaction_type.value == "SWAP"]

        swaps = []
        for tx in swap_transactions:
            swap = suow.repo.get_swap_by_transaction(tx.transaction_id.value)
            if swap:
                # Get token details
                token_in = suow.repo.get_token(swap.token_in_id.value)
                token_out = suow.repo.get_token(swap.token_out_id.value)

                swaps.append({
                    "swap_id": swap.swap_id.value,
                    "transaction_id": swap.transaction_id.value,
                    "token_in_symbol": token_in.symbol.value if token_in else "UNKNOWN",
                    "token_out_symbol": token_out.symbol.value if token_out else "UNKNOWN",
                    "amount_in": swap.amount_in.value,
                    "amount_out_expected": swap.amount_out_expected.value,
                    "amount_out_actual": swap.amount_out_actual.value if swap.amount_out_actual else None,
                    "slippage_tolerance": swap.slippage_tolerance.value,
                    "deadline": swap.deadline,
                    "status": tx.status.value,
                    "transaction_hash": tx.transaction_hash.value if tx.transaction_hash else None
                })

        return swaps


async def get_wallet_balance(wallet_id: str, token_id: Optional[str], suow: unit_of_work.AbstractUnitOfWork) -> Dict[str, Any]:
    """Get balance for a specific wallet and token."""
    with suow:
        wallet = suow.repo.get_wallet(wallet_id)
        if not wallet:
            raise ValueError("Wallet not found")

        if token_id:
            token = suow.repo.get_token(token_id)
            if not token:
                raise ValueError("Token not found")

            return {
                "wallet_id": wallet_id,
                "token_id": token_id,
                "token_symbol": token.symbol.value,
                "balance": "0",  # This would be fetched from blockchain adapter
                "decimals": token.decimals.value
            }
        else:
            # Native token balance
            return {
                "wallet_id": wallet_id,
                "token_id": None,
                "token_symbol": "AVAX",
                "balance": "0",  # This would be fetched from blockchain adapter
                "decimals": "18"
            }


def get_wallet_by_id(wallet_id: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get wallet by ID."""
    with suow:
        wallet = suow.repo.get_wallet(wallet_id)
        if not wallet:
            return None

        return {
            "wallet_id": wallet.wallet_id.value,
            "userid": wallet.userid.value,
            "address": wallet.address.value,
            "is_active": wallet.is_active,
            "created_at": wallet.created_at.isoformat() if wallet.created_at else None
            # Removed network field - wallet works across all networks
        }


def get_wallets_by_user(userid: str, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all wallets for a user."""
    with suow:
        wallets = suow.repo.get_wallets_by_user(userid)
        return [
            {
                "wallet_id": wallet.wallet_id.value,
                "userid": wallet.userid.value,
                "address": wallet.address.value,
                "is_active": wallet.is_active,
                "created_at": wallet.created_at.isoformat() if wallet.created_at else None
                # Removed network field - wallet works across all networks
            }
            for wallet in wallets
        ]


def get_transaction_by_id(transaction_id: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get transaction by ID."""
    with suow:
        transaction = suow.repo.get_transaction(transaction_id)
        if not transaction:
            return None

        return {
            "transaction_id": transaction.transaction_id.value,
            "userid": transaction.userid.value,
            "wallet_id": transaction.wallet_id.value,
            "transaction_type": transaction.transaction_type.value,
            "status": transaction.status.value,
            "transaction_hash": transaction.transaction_hash.value if transaction.transaction_hash else None,
            "gas_limit": transaction.gas_limit,
            "gas_price": transaction.gas_price,
            "gas_used": transaction.gas_used,
            "network": transaction.network,
            "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
            "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
            "confirmed_at": transaction.confirmed_at.isoformat() if transaction.confirmed_at else None,
            "error_message": transaction.error_message
        }


def get_transactions_by_user(userid: str, suow: unit_of_work.AbstractUnitOfWork, limit: int = 50) -> List[Dict[str, Any]]:
    """Get transactions for a user with pagination."""
    with suow:
        transactions = suow.repo.get_user_transactions(userid, limit)
        return [
            {
                "transaction_id": tx.transaction_id.value,
                "userid": tx.userid.value,
                "wallet_id": tx.wallet_id.value,
                "transaction_type": tx.transaction_type.value,
                "status": tx.status.value,
                "transaction_hash": tx.transaction_hash.value if tx.transaction_hash else None,
                "gas_limit": tx.gas_limit,
                "gas_price": tx.gas_price,
                "network": tx.network,
                "created_at": tx.created_at.isoformat() if tx.created_at else None
            }
            for tx in transactions
        ]


def get_swap_by_id(swap_id: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get swap by ID."""
    with suow:
        swap = suow.repo.get_swap(swap_id)
        if not swap:
            return None

        return {
            "swap_id": swap.swap_id.value,
            "transaction_id": swap.transaction_id.value,
            "token_in_id": swap.token_in_id.value,
            "token_out_id": swap.token_out_id.value,
            "amount_in": swap.amount_in.value,
            "amount_out_expected": swap.amount_out_expected.value,
            "amount_out_actual": swap.amount_out_actual.value if swap.amount_out_actual else None,
            "slippage_tolerance": swap.slippage_tolerance.value,
            "trader_joe_router": swap.trader_joe_router,
            "deadline": swap.deadline.isoformat() if swap.deadline else None
        }


def get_swaps_by_user(userid: str, suow: unit_of_work.AbstractUnitOfWork, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get swaps for a user with pagination."""
    with suow:
        swaps = suow.repo.get_swaps_by_user(userid, limit=limit, offset=offset)
        return [
            {
                "swap_id": swap.swap_id.value,
                "userid": swap.userid.value,
                "transaction_id": swap.transaction_id.value,
                "token_in_address": swap.token_in_address.value,
                "token_out_address": swap.token_out_address.value,
                "amount_in": str(swap.amount_in),
                "amount_out": str(swap.amount_out),
                "slippage_tolerance": str(swap.slippage_tolerance),
                "created_at": swap.created_at.isoformat() if swap.created_at else None
            }
            for swap in swaps
        ]


def get_wallet_balance_summary(wallet_id: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get wallet balance summary including all tokens across all networks."""
    with suow:
        wallet = suow.repo.get_wallet(wallet_id)
        if not wallet:
            return None

        # Get all active tokens for all networks since wallet works across networks
        # For now, we'll default to avalanche but this could be parameterized
        active_tokens = suow.repo.get_active_tokens("avalanche")  # Could be parameterized

        return {
            "wallet_id": wallet.wallet_id.value,
            "address": wallet.address.value,
            "network": "multi-chain",  # Indicate this wallet works across networks
            "tokens": [
                {
                    "token_id": token.token_id.value,
                    "symbol": token.symbol.value,
                    "name": token.name.value,
                    "balance": "0",  # This would be fetched from blockchain adapter
                    "contract_address": token.contract_address.value if token.contract_address else None,
                    "decimals": token.decimals.value
                }
                for token in active_tokens
            ]
        }


def get_transaction_history_summary(userid: str, suow: unit_of_work.AbstractUnitOfWork) -> Dict[str, Any]:
    """Get transaction history summary with counts and recent transactions."""
    with suow:
        transactions = suow.repo.get_user_transactions(userid, limit=100)

        # Count by status
        status_counts = {}
        for tx in transactions:
            status = tx.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Get recent transactions (last 10)
        recent_transactions = transactions[:10]

        return {
            "userid": userid,
            "total_transactions": len(transactions),
            "status_counts": status_counts,
            "recent_transactions": [
                {
                    "transaction_id": tx.transaction_id.value,
                    "transaction_type": tx.transaction_type.value,
                    "status": tx.status.value,
                    "transaction_hash": tx.transaction_hash.value if tx.transaction_hash else None,
                    "created_at": tx.created_at.isoformat() if tx.created_at else None
                }
                for tx in recent_transactions
            ]
        }


async def get_health_status(conn: AbstractConnectionManager) -> HealthMetrics:
    """Get comprehensive health check status"""
    return await conn.health_check()


async def get_metrics(conn: AbstractConnectionManager) -> ConnectionMetrics:
    """Get detailed metrics for monitoring"""
    return conn.get_metrics()


async def get_prometheus_metrics(conn: AbstractConnectionManager) -> str:
    """Generate Prometheus-compatible metrics"""
    status = await conn.health_check()

    return f"""
    # HELP rabbitmq_connections_total Total number of connections created
    # TYPE rabbitmq_connections_total counter
    rabbitmq_connections_total {status.metrics.total_connections_created}

    # HELP rabbitmq_channels_total Total number of channels created
    # TYPE rabbitmq_channels_total counter
    rabbitmq_channels_total {status.metrics.total_channels_created}

    # HELP rabbitmq_connections_active Current number of active connections
    # TYPE rabbitmq_connections_active gauge
    rabbitmq_connections_active {status.metrics.active_connections}

    # HELP rabbitmq_channels_active Current number of active channels
    # TYPE rabbitmq_channels_active gauge
    rabbitmq_channels_active {status.metrics.active_channels}

    # HELP rabbitmq_connection_errors_total Total number of connection errors
    # TYPE rabbitmq_connection_errors_total counter
    rabbitmq_connection_errors_total {status.metrics.connection_errors}

    # HELP rabbitmq_channel_errors_total Total number of channel errors
    # TYPE rabbitmq_channel_errors_total counter  
    rabbitmq_channel_errors_total {status.metrics.channel_errors}

    # HELP rabbitmq_messages_published_total Total number of messages published
    # TYPE rabbitmq_messages_published_total counter
    rabbitmq_messages_published_total {status.metrics.total_messages_published}

    # HELP rabbitmq_messages_consumed_total Total number of messages consumed
    # TYPE rabbitmq_messages_consumed_total counter
    rabbitmq_messages_consumed_total {status.metrics.total_messages_consumed}

    # HELP rabbitmq_last_error_timestamp_seconds Timestamp of last error
    # TYPE rabbitmq_last_error_timestamp_seconds gauge
    rabbitmq_last_error_timestamp_seconds {status.metrics.last_error_time or 0}

    # HELP rabbitmq_last_error_message message of last error
    # TYPE rabbitmq_last_error_message gauge
    rabbitmq_last_error_message {status.metrics.last_error_message or ""}

    # HELP rabbitmq_connection_pool_utilization Connection pool utilization ratio
    # TYPE rabbitmq_connection_pool_utilization gauge
    rabbitmq_connection_pool_utilization {status.metrics.connection_pool_utilization:.4f}

    # HELP rabbitmq_channel_pool_utilization Channel pool utilization ratio
    # TYPE rabbitmq_channel_pool_utilization gauge
    rabbitmq_channel_pool_utilization {status.metrics.channel_pool_utilization:.4f}

    # HELP rabbitmq_circuit_breaker_open Circuit breaker status (1 = open, 0 = closed)
    # TYPE rabbitmq_circuit_breaker_open gauge
    rabbitmq_circuit_breaker_open {status.circuit_breaker_open}

    # HELP rabbitmq_circuit_breaker_failures Circuit breaker failure count
    # TYPE rabbitmq_circuit_breaker_failures gauge
    rabbitmq_circuit_breaker_failures {status.circuit_breaker_failures}

    # HELP rabbitmq_circuit_breaker_last_failure Circuit breaker last failure timestamp
    # TYPE rabbitmq_circuit_breaker_last_failure gauge
    rabbitmq_circuit_breaker_last_failure {status.circuit_breaker_last_failure}

    # HELP rabbitmq_errors Circuit breaker last failure timestamp
    # TYPE rabbitmq_errors gauge
    rabbitmq_errors {status.errors}
"""


async def get_alerts(conn: AbstractConnectionManager) -> AlertsResponse:
    """Get current alerts based on system status"""
    status = await conn.health_check()
    current_time = time.time()

    critical_alerts = []
    warning_alerts = []
    info_alerts = []

    # Critical alerts
    if status.circuit_breaker_open:
        critical_alerts.append("Circuit breaker is OPEN - RabbitMQ connections are failing")

    if status.metrics.active_connections == 0:
        critical_alerts.append("No active connections available")

    if status.metrics.connection_pool_utilization > 0.8:
        warning_alerts.append(f"Connection pool utilization high: {status.metrics.connection_pool_utilization:.1%}")

        if status.metrics.channel_pool_utilization > 0.8:
            warning_alerts.append(f"Channel pool utilization high: {status.metrics.channel_pool_utilization:.1%}")

    if status.metrics.last_error_time and (current_time - status.metrics.last_error_time) < 300:
        warning_alerts.append(f"Recent error: {status.metrics.last_error_message}")

    if status.circuit_breaker_failures > 0:
        warning_alerts.append(
            f"Circuit breaker has {status.circuit_breaker_failures} failures"
        )

    # Info alerts
    if status.metrics.connection_pool_utilization > 0.5:
        info_alerts.append(f"Connection pool utilization: {status.metrics.connection_pool_utilization:.1%}")

    if status.dedicated_channels > 5:
        info_alerts.append(f"High number of dedicated channels: {status.dedicated_channels}")

    return AlertsResponse(
        timestamp=datetime.now(),
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        info_alerts=info_alerts
    )

# Views for read-only operations using standby database (suow)
async def get_user_approvals_view(userid: str, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all current token approvals for a user."""
    with suow:
        approvals = suow.repo.get_user_approvals(userid)
        return [
            {
                "approval_id": approval.approval_id.value,
                "wallet_id": approval.wallet_id.value,
                "token_id": approval.token_id.value,
                "approved_amount": approval.approved_amount.value,
                "updated_at": approval.updated_at.isoformat() if approval.updated_at else None
            }
            for approval in approvals
        ]

async def get_approval_history_view(userid: str, token_id: str = None, suow: unit_of_work.AbstractUnitOfWork = None) -> List[Dict[str, Any]]:
    """Get approval transaction history for a user."""
    with suow:
        wallet = suow.repo.get_user_wallet(userid)
        if not wallet:
            return []

        approval_history = suow.repo.get_approval_history(token_id, wallet.wallet_id.value)
        return [
            {
                "approval_transaction_id": approval_tx.approval_transaction_id.value,
                "transaction_id": approval_tx.transaction_id.value,
                "token_id": approval_tx.token_id.value,
                "approval_type": approval_tx.approval_type.value,
                "amount": approval_tx.amount.value,
                "previous_amount": approval_tx.previous_amount.value,
                "new_amount": approval_tx.new_amount.value
            }
            for approval_tx in approval_history
        ]

async def get_user_swap_history_view(userid: str, limit: int, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get swap transaction history for a user."""
    with suow:
        swap_txs = suow.repo.get_user_swap_history(userid, limit)
        return [
            {
                "swap_transaction_id": swap_tx.swap_transaction_id.value,
                "transaction_id": swap_tx.transaction_id.value,
                "swap_type": swap_tx.swap_type.value,
                "token_in_id": swap_tx.token_in_id.value,
                "token_out_id": swap_tx.token_out_id.value,
                "amount_in": swap_tx.amount_in.value,
                "amount_out_expected": swap_tx.amount_out_expected.value,
                "amount_out_actual": swap_tx.amount_out_actual.value if swap_tx.amount_out_actual else None,
                "slippage_tolerance": swap_tx.slippage_tolerance.value,
                "deadline": swap_tx.deadline.isoformat() if swap_tx.deadline else None,
                "router_address": swap_tx.router_address.value
            }
            for swap_tx in swap_txs
        ]

async def get_token_swap_history_view(token_id: str, limit: int, suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get swap history for a specific token."""
    with suow:
        swap_txs = suow.repo.get_token_swap_history(token_id, limit)
        return [
            {
                "swap_transaction_id": swap_tx.swap_transaction_id.value,
                "transaction_id": swap_tx.transaction_id.value,
                "swap_type": swap_tx.swap_type.value,
                "token_in_id": swap_tx.token_in_id.value,
                "token_out_id": swap_tx.token_out_id.value,
                "amount_in": swap_tx.amount_in.value,
                "amount_out_expected": swap_tx.amount_out_expected.value,
                "amount_out_actual": swap_tx.amount_out_actual.value if swap_tx.amount_out_actual else None,
                "slippage_tolerance": swap_tx.slippage_tolerance.value,
                "deadline": swap_tx.deadline.isoformat() if swap_tx.deadline else None,
                "router_address": swap_tx.router_address.value
            }
            for swap_tx in swap_txs
        ]

async def get_supported_tokens_view(suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all supported tokens for TraderJoe swaps."""
    token_service = TokenManagementService(suow)
    return await token_service.get_supported_tokens()

async def get_token_by_symbol_view(symbol: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get token by symbol."""
    token_service = TokenManagementService(suow)
    return await token_service.get_token_by_symbol(symbol)

async def get_supported_chains_view(suow: unit_of_work.AbstractUnitOfWork) -> List[Dict[str, Any]]:
    """Get all supported chains."""
    chain_service = BlockchainService(suow)
    return await chain_service.get_supported_chains()

async def get_chain_by_symbol_view(symbol: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get chain by symbol."""
    chain_service = BlockchainService(suow)
    return await chain_service.get_chain_by_symbol(symbol)

async def get_user_wallet_view(userid: str, suow: unit_of_work.AbstractUnitOfWork) -> Optional[Dict[str, Any]]:
    """Get user's wallet."""
    wallet_service = WalletService(suow)  # No blockchain adapter needed for read operations
    return await wallet_service.get_user_wallet(userid)

async def check_approval_status_view(
    userid: str,
    token_id: str,
    required_amount: str,
    suow: unit_of_work.AbstractUnitOfWork
) -> Dict[str, Any]:
    """Check if user has sufficient approval for a token amount."""
    with suow:
        wallet = suow.repo.get_user_wallet(userid)
        if not wallet:
            return {"sufficient": False, "error": "User wallet not found"}

        approval = suow.repo.get_token_approval_by_wallet_token(wallet.wallet_id, token_id)
        if not approval:
            return {
                "sufficient": False,
                "current_amount": "0",
                "required_amount": required_amount
            }

        is_sufficient = approval.has_sufficient_approval(required_amount)
        return {
            "sufficient": is_sufficient,
            "current_amount": approval.approved_amount.value,
            "required_amount": required_amount
        }
