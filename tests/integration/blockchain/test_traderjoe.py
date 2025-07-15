import pytest
import time
from src.adapters.blockchain.protocols.traderjoe import TraderJoeV2Protocol
from src.adapters.blockchain.utils.abi import AbiEncoder

pytestmark = pytest.mark.asyncio

async def test_traderjoe_initialization(trader_joe_contract):
    """Test TraderJoe protocol initialization."""
    assert isinstance(trader_joe_contract, TraderJoeV2Protocol)
    assert trader_joe_contract.protocol_type == "TRADERJOE_V2_2"
    assert 43113 in trader_joe_contract.supported_chains

async def test_get_quote(trader_joe_contract, usdc_contract, wavax_contract):
    """Test getting swap quote."""
    amount_in = 1_000_000  # 1 USDC (6 decimals)

    amount_out, path = await trader_joe_contract.get_quote(
        token_in=usdc_contract.contract_address,
        token_out=wavax_contract.contract_address,
        amount_in=amount_in,
        bin_step=100  # 1% bin step
    )

    assert isinstance(amount_out, int)
    assert amount_out > 0
    assert isinstance(path, bytes)

    # Decode path to verify
    decoded = AbiEncoder.decode_path(path)
    assert decoded["tokens"][0].lower() == usdc_contract.contract_address.lower()
    assert decoded["tokens"][1].lower() == wavax_contract.contract_address.lower()
    assert decoded["fees"][0] == 100  # 1% fee

@pytest.mark.skip(reason="Requires account with USDC balance and approval")
async def test_swap_exact_tokens_for_tokens(
    trader_joe_contract,
    usdc_contract,
    wavax_contract,
    sender_wallet
):
    """Test token to token swap."""
    amount_in = 1_000_000  # 1 USDC

    # First approve USDC spending
    await usdc_contract.approve(
        spender=trader_joe_contract.contract_address,
        amount=amount_in,
        sender=sender_wallet
    )

    # Get quote and execute swap
    amount_out, path = await trader_joe_contract.get_quote(
        token_in=usdc_contract.contract_address,
        token_out=wavax_contract.contract_address,
        amount_in=amount_in
    )

    deadline = int(time.time()) + 1200  # 20 minutes from now

    tx_hash = await trader_joe_contract.swap_exact_tokens_for_tokens(
        amount_in=amount_in,
        amount_out_min=int(amount_out * 0.99),  # 1% slippage
        path=path,
        to_address=sender_wallet["address"],
        deadline=deadline,
        sender=sender_wallet
    )

    assert isinstance(tx_hash, str)
    assert tx_hash.startswith("0x")

@pytest.mark.skip(reason="Requires account with AVAX balance")
async def test_swap_exact_avax_for_tokens(
    trader_joe_contract,
    usdc_contract,
    sender_wallet
):
    """Test AVAX to token swap."""
    amount_in = 100_000_000_000_000_000  # 0.1 AVAX

    # Get quote for AVAX -> USDC
    amount_out, path = await trader_joe_contract.get_quote(
        token_in=trader_joe_contract.WAVAX_ADDRESS,
        token_out=usdc_contract.contract_address,
        amount_in=amount_in
    )

    deadline = int(time.time()) + 1200  # 20 minutes from now

    tx_hash = await trader_joe_contract.swap_exact_avax_for_tokens(
        amount_in=amount_in,
        amount_out_min=int(amount_out * 0.99),  # 1% slippage
        path=path,
        to_address=sender_wallet["address"],
        deadline=deadline,
        sender=sender_wallet
    )

    assert isinstance(tx_hash, str)
    assert tx_hash.startswith("0x")
