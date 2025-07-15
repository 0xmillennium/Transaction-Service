import pytest
from web3 import AsyncWeb3
from src.adapters.blockchain.chains.avalanche import AvalancheFuji
from src.adapters.blockchain.protocols.erc20 import ERC20Protocol
from src.adapters.blockchain.protocols.traderjoe import TraderJoeV2Protocol

# Test constants for Avalanche Fuji testnet
TEST_RPC_URL = "https://api.avax-test.network/ext/bc/C/rpc"
TEST_ACCOUNT = "0x0000000000000000000000000000000000000000"  # Replace with a test account
TEST_PRIVATE_KEY = "your_private_key_here"  # Replace with test private key

# Test token addresses on Fuji
TEST_USDC_ADDRESS = "0x5425890298aed601595a70AB815c96711a31Bc65"  # Fuji USDC
TEST_WAVAX_ADDRESS = "0xd00ae08403B9bbb9124bB305C09058E32C39A48c"  # Fuji WAVAX
TEST_JOE_ROUTER_ADDRESS = "0xd7f655E3376cE2D7A2b08fF01Eb3B1023191A901"  # TraderJoe V2.2 Router

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def fuji_chain():
    """Create an instance of AvalancheFuji chain for testing."""
    chain = AvalancheFuji(rpc_url=TEST_RPC_URL)
    await chain.connect()
    return chain

@pytest.fixture(scope="session")
async def usdc_contract(fuji_chain):
    """Create an instance of USDC token contract for testing."""
    return ERC20Protocol(contract_address=TEST_USDC_ADDRESS).bind(fuji_chain)

@pytest.fixture(scope="session")
async def wavax_contract(fuji_chain):
    """Create an instance of WAVAX token contract for testing."""
    return ERC20Protocol(contract_address=TEST_WAVAX_ADDRESS).bind(fuji_chain)

@pytest.fixture(scope="session")
async def trader_joe_contract(fuji_chain):
    """Create an instance of TraderJoe V2.2 contract for testing."""
    return TraderJoeV2Protocol(contract_address=TEST_JOE_ROUTER_ADDRESS).bind(fuji_chain)

@pytest.fixture(scope="session")
def sender_wallet():
    """Return sender wallet information for testing."""
    return {
        "address": TEST_ACCOUNT,
        "private_key": TEST_PRIVATE_KEY
    }
