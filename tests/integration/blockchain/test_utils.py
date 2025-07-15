import pytest
from web3 import AsyncWeb3
from src.adapters.blockchain.utils.abi import AbiEncoder
from src.adapters.blockchain.utils.transaction import TransactionBuilder

pytestmark = pytest.mark.asyncio

class TestAbiEncoder:
    def test_encode_path(self):
        """Test TraderJoe V2.2 path encoding."""
        token_a = "0x5425890298aed601595a70AB815c96711a31Bc65"  # USDC
        token_b = "0xd00ae08403B9bbb9124bB305C09058E32C39A48c"  # WAVAX
        fees = [100]  # 1% fee

        encoded_path = AbiEncoder.encode_path([token_a, token_b], fees)
        assert isinstance(encoded_path, bytes)

        # Decode and verify
        decoded = AbiEncoder.decode_path(encoded_path)
        assert decoded["tokens"][0].lower() == token_a.lower()
        assert decoded["tokens"][1].lower() == token_b.lower()
        assert decoded["fees"] == fees

    def test_encode_path_validation(self):
        """Test path encoding validation."""
        with pytest.raises(ValueError, match="Path must contain at least 2 tokens"):
            AbiEncoder.encode_path(["0x123"], [])

        with pytest.raises(ValueError, match="Length of fees must be one less than tokens"):
            AbiEncoder.encode_path(
                ["0x123", "0x456"],
                [100, 100]  # Too many fees
            )

class TestTransactionBuilder:
    async def test_build_transaction(self, fuji_chain):
        """Test transaction building."""
        builder = TransactionBuilder(fuji_chain.web3)

        tx = await builder.build_transaction(
            from_address="0x0000000000000000000000000000000000000000",
            to_address="0x0000000000000000000000000000000000000001",
            value=100000
        )

        assert isinstance(tx, dict)
        assert tx['chainId'] == fuji_chain.chain_id
        assert tx['value'] == 100000
        assert 'gas' in tx
        assert ('gasPrice' in tx) or ('maxFeePerGas' in tx)

    async def test_estimate_gas_cost(self, fuji_chain):
        """Test gas cost estimation."""
        builder = TransactionBuilder(fuji_chain.web3)

        tx = {
            'from': "0x0000000000000000000000000000000000000000",
            'to': "0x0000000000000000000000000000000000000001",
            'value': 100000,
            'gas': 21000,
            'gasPrice': 25000000000  # 25 gwei
        }

        cost = await builder.estimate_gas_cost(tx)
        assert isinstance(cost, int)
        assert cost == 21000 * 25000000000  # gas * gasPrice

    async def test_invalid_address_validation(self, fuji_chain):
        """Test validation of invalid addresses."""
        builder = TransactionBuilder(fuji_chain.web3)

        with pytest.raises(ValueError, match="Invalid from address"):
            await builder.build_transaction(
                from_address="invalid_address",
                to_address="0x0000000000000000000000000000000000000001"
            )

        with pytest.raises(ValueError, match="Invalid to address"):
            await builder.build_transaction(
                from_address="0x0000000000000000000000000000000000000000",
                to_address="invalid_address"
            )
