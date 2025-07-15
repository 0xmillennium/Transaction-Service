import pytest
from decimal import Decimal
from src.adapters.blockchain.protocols.erc20 import ERC20Protocol

pytestmark = pytest.mark.asyncio

async def test_erc20_initialization(usdc_contract):
    """Test ERC20 protocol initialization."""
    assert isinstance(usdc_contract, ERC20Protocol)
    assert usdc_contract.protocol_type == "ERC20"
    assert 43113 in usdc_contract.supported_chains

async def test_get_token_info(usdc_contract):
    """Test getting basic token information."""
    decimals = await usdc_contract.get_decimals()
    assert decimals == 6

    symbol = await usdc_contract.chain.call_contract(
        usdc_contract.contract_address,
        usdc_contract.abi,
        "symbol"
    )
    assert symbol == "USDC"

async def test_get_balance(usdc_contract):
    """Test getting token balance."""
    # Test with zero address as it always exists
    balance = await usdc_contract.get_balance("0x0000000000000000000000000000000000000000")
    assert isinstance(balance, int)
    assert balance >= 0

async def test_get_allowance(usdc_contract):
    """Test getting token allowance."""
    allowance = await usdc_contract.get_allowance(
        "0x0000000000000000000000000000000000000000",  # owner
        "0x0000000000000000000000000000000000000000"   # spender
    )
    assert isinstance(allowance, int)
    assert allowance >= 0

@pytest.mark.skip(reason="Requires account with token balance")
async def test_approve(usdc_contract, sender_wallet):
    """Test token approval."""
    spender = "0x0000000000000000000000000000000000000000"
    amount = 1000000  # 1 USDC (6 decimals)

    tx_hash = await usdc_contract.approve(
        spender=spender,
        amount=amount,
        sender=sender_wallet
    )

    assert isinstance(tx_hash, str)
    assert tx_hash.startswith("0x")

    # Verify allowance after approval
    allowance = await usdc_contract.get_allowance(
        sender_wallet['address'],
        spender
    )
    assert allowance >= amount
