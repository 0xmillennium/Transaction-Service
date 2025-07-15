# Transaction Service

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-latest-336791.svg)](https://www.postgresql.org/)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.12-FF6600.svg)](https://www.rabbitmq.com/)
[![Docker](https://img.shields.io/badge/docker-containerized-2496ED.svg)](https://www.docker.com/)

A blockchain transaction microservice implementing automated token swapping on Avalanche via TraderJoe V2.2 DEX protocol. Built using Domain-Driven Design, event sourcing, and hexagonal architecture patterns.

## What This Service Actually Does

This microservice serves as a **blockchain transaction abstraction layer** that:

1. **Manages Ethereum-compatible wallets** with encrypted private key storage
2. **Executes automated token swaps** on TraderJoe DEX using V2.2 liquidity pools
3. **Handles complex DeFi operations** like token approvals, gas optimization, and slippage protection
4. **Provides transaction lifecycle management** from creation to blockchain confirmation
5. **Implements event-driven architecture** for real-time transaction monitoring

### Core Technical Implementation

#### TraderJoe V2.2 Protocol Integration
The service directly interfaces with TraderJoe's V2.2 router contract, implementing:
- **Liquidity Book (LB) pairs** for concentrated liquidity
- **Multi-hop routing** through optimal token paths
- **Bin-based price discovery** for better execution
- **Version-aware routing** (V1/V2.1/V2.2 compatibility)

#### Supported Swap Operations
```python
# Native AVAX to ERC-20 tokens
swapExactNATIVEForTokens(amountOutMin, path, to, deadline)

# ERC-20 tokens to native AVAX  
swapExactTokensForNATIVE(amountIn, amountOutMinNATIVE, path, to, deadline)

# ERC-20 to ERC-20 token swaps
swapExactTokensForTokens(amountIn, amountOutMin, path, to, deadline)
```

## Technical Architecture

### Domain-Driven Design Implementation

The service follows DDD patterns with clear bounded contexts:

```
Domain Layer (Business Logic)
├── Aggregates: Wallet, Transaction, Swap, Token, Chain, Approval
├── Value Objects: Address, Amount, SlippageTolerance, etc.
├── Domain Events: TransactionCreated, SwapCompleted, etc.
└── Commands: CreateWalletCommand, SwapExactNativeToTokenCommand

Service Layer (Application Logic)  
├── Command Handlers: Process business commands
├── Event Handlers: React to domain events
├── Unit of Work: Manage transaction boundaries
└── Message Bus: Internal command/event routing

Adapter Layer (Infrastructure)
├── Database: PostgreSQL with SQLAlchemy async ORM
├── Blockchain: Web3.py + TraderJoe protocol adapters
├── Message Broker: RabbitMQ for event publishing
└── HTTP: FastAPI REST endpoints
```

### Event-Driven Architecture

The system uses event sourcing for transaction lifecycle:

```python
# Domain events flow
WalletCreated → TransactionCreated → SwapCreated → TransactionConfirmed → SwapCompleted
```

Events are published via RabbitMQ with topic-based routing:
- Exchange: `transaction.events` (topic)
- Routing keys: `transaction.created`, `swap.completed`, etc.

### Database Architecture

**Primary-Standby PostgreSQL Setup:**
- **Primary DB**: Write operations, immediate consistency
- **Standby DB**: Read operations, eventual consistency
- **Connection pooling**: Async SQLAlchemy sessions
- **SSL encryption**: Certificate-based security

### Blockchain Integration Architecture

#### Web3.py Async Implementation
```python
# Avalanche C-Chain connection
chain = AsyncWeb3(AsyncHTTPProvider("https://api.avax.network/ext/bc/C/rpc"))

# Contract interaction
contract = chain.eth.contract(address=router_address, abi=traderjoe_abi)
tx = await contract.functions.swapExactNATIVEForTokens(...).build_transaction({...})
```

#### Gas Optimization Strategy
- **Dynamic gas pricing**: 10% buffer over network gas price
- **Gas estimation**: Pre-transaction simulation for accuracy
- **Transaction monitoring**: Block confirmation tracking

#### Security Implementation
- **Private key encryption**: AES-256 encryption at rest
- **Transaction signing**: Local signing with eth-account
- **SSL/TLS**: End-to-end encryption for all communications

## Technology Stack Deep Dive

### Core Framework Stack
```python
# Web framework
FastAPI 0.115.0          # High-performance async web framework
Uvicorn 0.34.2          # ASGI server implementation
Starlette 0.41.0        # Lightweight ASGI framework

# Database stack  
SQLAlchemy 2.0.36       # Async ORM with declarative mapping
asyncpg 0.30.0          # Async PostgreSQL driver
psycopg2 2.9.10         # Sync PostgreSQL driver (for migrations)

# Blockchain integration
web3 7.6.0              # Ethereum/Avalanche interaction
eth-account 0.13.1      # Wallet and transaction signing
```

### Message Broker & Security
```python
# Message broker
aio-pika 9.5.5          # Async RabbitMQ client
aiormq 6.8.1            # Low-level AMQP implementation

# Security & encryption
python-jose 3.3.0       # JWT token handling
argon2-cffi 23.1.0      # Password hashing
cryptography 44.0.0     # Encryption primitives
```

### Data Validation & HTTP
```python
# Data validation
pydantic 2.10.0         # Runtime type checking and validation

# HTTP client & WebSockets
httpx 0.28.0            # Async HTTP client with HTTP/2
websockets 13.1         # WebSocket implementation
```

## Real-World Usage Examples

### 1. Automated AVAX → USDC Swap
```bash
POST /transaction/swaps/exact-native-to-token
{
  "token_out_id": "usdc_avalanche",
  "amount_in": "1000000000000000000",    # 1 AVAX in wei
  "amount_out_min": "25000000",          # Min 25 USDC (6 decimals)
  "slippage_tolerance": "0.5",           # 0.5% slippage
  "deadline_minutes": 20
}
```

### 2. Multi-hop Token Swap (USDC → WAVAX → JOE)
The service automatically determines optimal routing through TraderJoe's liquidity pools:
```python
# Automatic path discovery
path = {
    "pairBinSteps": [15, 20],     # Bin steps for each hop
    "versions": [2, 2],           # V2.2 pools
    "tokenPath": [USDC, WAVAX, JOE]  # Token addresses
}
```

### 3. Real-time Transaction Monitoring
```javascript
// WebSocket connection for live updates
const ws = new WebSocket('ws://localhost:8000/transaction/ws/user123');
ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    // Handle: pending, confirmed, failed status updates
};
```

## Development Environment Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- PostgreSQL client (optional, for debugging)

### Local Development
```bash
# 1. Clone and setup
git clone <repository>
cd Transaction-Service

# 2. Environment configuration
mkdir -p config/secrets/environments
# Create .env.primary, .env.standby, .env.dev files

# 3. SSL certificates
./scripts/ssl-configurations.sh

# 4. Start infrastructure
make up

# 5. Verify service
curl http://localhost:8000/ping
```

### Testing Strategy
```bash
# Unit tests (domain logic)
pytest tests/unit/

# Integration tests (database, blockchain)
pytest tests/integration/

# End-to-end tests (full workflows)
pytest tests/e2e/

# Contract tests (API compatibility)
pytest tests/contracts/
```

## Production Deployment Considerations

### Environment Variables
```bash
# Database configuration
DATABASE_URL=postgresql+asyncpg://user:pass@primary:5432/db
STANDBY_DATABASE_URL=postgresql+asyncpg://user:pass@standby:5432/db

# Blockchain configuration
AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc
TRADERJOE_ROUTER_ADDRESS=0x18556DA13313f3532c54711497A8FedAC273220E

# Security
JWT_SECRET_KEY=your_production_secret
ENCRYPTION_KEY=32_byte_encryption_key
```

### Performance Characteristics
- **API Response Time**: < 50ms (local operations)
- **Swap Transaction Time**: 2-10 seconds (blockchain dependent)
- **Database Connections**: Pool of 20 async connections
- **Message Throughput**: 1000+ events/second

### Monitoring & Observability
```bash
# Service health
GET /ping                 # Basic health check
GET /                    # Service information

# Database health
docker exec primary_db pg_isready

# Message broker health
docker exec rabbitmq_broker rabbitmq-diagnostics check_running
```

## Common Integration Patterns

### 1. Trading Bot Integration
```python
# Automated arbitrage example
async def arbitrage_opportunity():
    quote = await get_swap_quote("USDC", "JOE", "1000000000")
    if quote.price_impact < 0.1:  # Less than 0.1% impact
        await execute_swap(quote)
```

### 2. DeFi Dashboard Integration
```python
# Portfolio tracking
async def get_user_transactions():
    response = await httpx.get(
        f"{API_BASE}/transaction/transactions/history",
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    return response.json()
```

### 3. Webhook Integration
```python
# React to transaction events
@app.post("/webhooks/transaction-update")
async def handle_transaction_update(event: TransactionEvent):
    if event.status == "confirmed":
        await update_user_portfolio(event.user_id)
```

## Architecture Decision Records (ADRs)

### Why TraderJoe V2.2?
- **Concentrated liquidity**: Better capital efficiency than V1
- **Reduced slippage**: Bin-based pricing for smaller trades
- **Lower fees**: Optimized fee structure
- **Active ecosystem**: Highest TVL on Avalanche

### Why Async Python?
- **High concurrency**: Handle multiple blockchain calls simultaneously
- **Resource efficiency**: Single-threaded event loop
- **Framework ecosystem**: FastAPI + SQLAlchemy async support

### Why Primary-Standby DB?
- **Write consistency**: Immediate consistency for transactions
- **Read scaling**: Distribute read queries to standby
- **High availability**: Failover capability

---

**Technical Contact**: Mübarek (0xmillennium@protonmail.com)  
**License**: MIT  
**Version**: 1.0.0
