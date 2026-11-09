"""Submit a prepared Merkle root to the configured BatchAnchor contract."""

import os

from dotenv import load_dotenv
from web3 import Web3

from app.provenance import next_batch

ABI = [
    {"type": "function", "name": "anchor", "stateMutability": "nonpayable", "inputs": [{"name": "root", "type": "bytes32"}, {"name": "count", "type": "uint64"}], "outputs": []}
]


def main() -> None:
    load_dotenv(".env")
    rpc = os.environ["ANCHOR_RPC_URL"]
    private_key = os.environ["ANCHOR_PRIVATE_KEY"]
    contract_address = Web3.to_checksum_address(os.environ["ANCHOR_CONTRACT_ADDRESS"])
    expected_chain = int(os.environ["ANCHOR_CHAIN_ID"])
    web3 = Web3(Web3.HTTPProvider(rpc))
    if not web3.is_connected() or web3.eth.chain_id != expected_chain:
        raise RuntimeError("RPC unavailable or chain id does not match ANCHOR_CHAIN_ID")
    batch = next_batch()
    if batch is None:
        print("No staged batch is waiting for anchoring.")
        return
    account = web3.eth.account.from_key(private_key)
    contract = web3.eth.contract(address=contract_address, abi=ABI)
    transaction = contract.functions.anchor(bytes.fromhex(batch["root"]), batch["count"]).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "chainId": expected_chain,
        "gas": 180_000,
        "maxFeePerGas": web3.eth.gas_price * 2,
        "maxPriorityFeePerGas": web3.to_wei(0.001, "gwei"),
    })
    signed = web3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError(f"Anchor transaction reverted: {tx_hash.hex()}")
    from app.provenance import mark_batch_anchored

    mark_batch_anchored(batch["root"], tx_hash.hex(), expected_chain)
    print(f"Anchored {batch['count']} receipts; tx={tx_hash.hex()} root={batch['root']}")


if __name__ == "__main__":
    main()
