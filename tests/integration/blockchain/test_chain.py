import pytest
from web3 import AsyncWeb3
from src.adapters.blockchain.chains.avalanche import AvalancheFuji

pytestmark = pytest.mark.asyncio

async def test_chain_connection(fuji_chain):
    """Test that the chain connects successfully."""
    assert fuji_chain.web3 is not None
    assert await fuji_chain.web3.is_connected()
    assert fuji_chain.chain_id == 43113

async def test_get_native_balance(fuji_chain):
    """Test getting AVAX balance."""
    balance = await fuji_chain.get_native_balance("0x0000000000000000000000000000000000000000")
    assert isinstance(balance, int)
    assert balance >= 0

async def test_chain_properties(fuji_chain):
    """Test chain property getters."""
    assert fuji_chain.native_currency == "AVAX"
    assert fuji_chain.block_explorer_url == "https://testnet.snowtrace.io"

async def test_contract_call(fuji_chain, usdc_contract):
    """Test calling a contract method."""
    decimals = await fuji_chain.call_contract(
        usdc_contract.contract_address,
        usdc_contract.abi,
        "decimals"
    )
    assert isinstance(decimals, int)
    assert decimals == 6  # USDC has 6 decimals

@pytest.mark.skip(reason="Requires account with funds")
async def test_send_transaction(fuji_chain, sender_wallet):
    """Test sending a transaction."""
    tx = {
        'from': sender_wallet['address'],
        'to': "0x0000000000000000000000000000000000000000",
        'value': 100000,  # 0.0001 AVAX
        'nonce': await fuji_chain.web3.eth.get_transaction_count(sender_wallet['address']),
        'gas': 21000,
        'chainId': fuji_chain.chain_id
    }

    tx_hash = await fuji_chain.send_transaction(tx)
    assert isinstance(tx_hash, str)
    assert tx_hash.startswith("0x")
