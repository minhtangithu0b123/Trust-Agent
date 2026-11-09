"""Register the Trust Agent on an ERC-8004 Identity Registry.

The registration JSON must be reachable at ERC8004_AGENT_URI before running.
After the script adds the registry coordinates and agentId, publish that file
again so its registration entry can be checked against the chain.
"""

import json
import os
from pathlib import Path

from web3 import Web3

ABI = [
    {"type": "function", "name": "register", "stateMutability": "nonpayable", "inputs": [{"name": "agentURI", "type": "string"}], "outputs": [{"name": "agentId", "type": "uint256"}]},
    {"type": "event", "name": "Registered", "anonymous": False, "inputs": [{"name": "agentId", "type": "uint256", "indexed": True}, {"name": "agentURI", "type": "string", "indexed": False}, {"name": "owner", "type": "address", "indexed": True}]},
]


def main() -> None:
    web3 = Web3(Web3.HTTPProvider(os.environ["ERC8004_RPC_URL"]))
    private_key = os.environ["ERC8004_PRIVATE_KEY"]
    registry_address = Web3.to_checksum_address(os.environ["ERC8004_REGISTRY_ADDRESS"])
    chain_id = int(os.environ["ERC8004_CHAIN_ID"])
    agent_uri = os.environ["ERC8004_AGENT_URI"]
    if not agent_uri.startswith("https://"):
        raise ValueError("ERC8004_AGENT_URI must use HTTPS")
    if not web3.is_connected() or web3.eth.chain_id != chain_id:
        raise RuntimeError("RPC unavailable or chain id does not match ERC8004_CHAIN_ID")
    account = web3.eth.account.from_key(private_key)
    registry = web3.eth.contract(address=registry_address, abi=ABI)
    tx = registry.functions.register(agent_uri).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "chainId": chain_id,
        "gas": 500_000,
        "maxFeePerGas": web3.eth.gas_price * 2,
        "maxPriorityFeePerGas": web3.to_wei(0.001, "gwei"),
    })
    signed = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status != 1:
        raise RuntimeError(f"ERC-8004 registration reverted: {tx_hash.hex()}")
    events = registry.events.Registered().process_receipt(receipt)
    if not events:
        raise RuntimeError("Transaction succeeded but no Registered event was emitted")
    agent_id = int(events[0]["args"]["agentId"])
    registry_id = f"eip155:{chain_id}:{registry_address}"
    metadata_path = Path(os.getenv("ERC8004_METADATA_FILE", "app/agent-registration.example.json"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["registrations"] = [{"agentId": agent_id, "agentRegistry": registry_id}]
    metadata["active"] = True
    metadata["x402Support"] = os.getenv("X402_ENABLED", "false").casefold() == "true"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Registered agentId={agent_id}; tx={tx_hash.hex()}; registry={registry_id}")
    print(f"Publish {metadata_path} at {agent_uri} and verify HTTPS domain ownership before advertising it.")


if __name__ == "__main__":
    main()
