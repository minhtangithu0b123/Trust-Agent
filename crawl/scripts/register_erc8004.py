"""Register the Trust Agent in an ERC-8004 Identity Registry.

Run from ``crawl/`` after the public agent registration JSON is deployed and
reachable at ERC8004_AGENT_URI. The script writes the mined agent ID back to
ERC8004_METADATA_FILE; publish that updated JSON after registration.
"""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from web3 import Web3

FUJI_CHAIN_ID = 43113
FUJI_IDENTITY_REGISTRY = "0x8004A818BFB912233c491871b3d84c89A494BD9e"
REGISTRATION_TYPE = "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"

ABI = [
    {
        "type": "function",
        "name": "register",
        "stateMutability": "nonpayable",
        "inputs": [{"name": "agentURI", "type": "string"}],
        "outputs": [{"name": "agentId", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "ownerOf",
        "stateMutability": "view",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "owner", "type": "address"}],
    },
    {
        "type": "function",
        "name": "tokenURI",
        "stateMutability": "view",
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "outputs": [{"name": "uri", "type": "string"}],
    },
    {
        "type": "event",
        "name": "Registered",
        "anonymous": False,
        "inputs": [
            {"name": "agentId", "type": "uint256", "indexed": True},
            {"name": "agentURI", "type": "string", "indexed": False},
            {"name": "owner", "type": "address", "indexed": True},
        ],
    },
]


def fetch_public_metadata(agent_uri: str) -> dict:
    request = Request(agent_uri, headers={"User-Agent": "TrustAgent-ERC8004-Setup/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Metadata URL returned HTTP {response.status}: {agent_uri}")
            metadata = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot fetch valid public JSON from ERC8004_AGENT_URI: {exc}") from exc

    if not isinstance(metadata, dict) or metadata.get("type") != REGISTRATION_TYPE:
        raise RuntimeError(f"Metadata must use ERC-8004 registration type {REGISTRATION_TYPE}")
    if not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
        raise RuntimeError("Metadata must contain a non-empty name")
    if not isinstance(metadata.get("services"), list) or not metadata["services"]:
        raise RuntimeError("Metadata must publish at least one service endpoint")
    web_url = os.getenv("TRUST_AGENT_WEB_URL", "https://trust-agent-eight.vercel.app").strip().rstrip("/")
    services = metadata["services"]
    web_service = next((item for item in services if isinstance(item, dict) and item.get("name") == "web"), None)
    x402_service = next((item for item in services if isinstance(item, dict) and item.get("name") == "x402"), None)
    if not web_service or web_service.get("endpoint", "").rstrip("/") != web_url:
        raise RuntimeError(f"Metadata web service must point to TRUST_AGENT_WEB_URL ({web_url})")
    if not x402_service or not x402_service.get("endpoint", "").endswith("/paid/traffic/ask"):
        raise RuntimeError("Metadata must publish the x402 endpoint ending in /paid/traffic/ask")
    if metadata.get("x402Support") is not True:
        raise RuntimeError("Public metadata says x402Support is not enabled; fix backend X402_ENABLED and redeploy")
    return metadata


def main() -> None:
    load_dotenv(".env")
    if os.getenv("X402_ENABLED", "false").casefold() != "true":
        raise RuntimeError("Set X402_ENABLED=true in crawl/.env before registering the x402 demo agent")
    rpc_url = os.environ["ERC8004_RPC_URL"].strip()
    private_key = os.getenv("ERC8004_PRIVATE_KEY", "").strip()
    if not private_key:
        raise RuntimeError("Set ERC8004_PRIVATE_KEY in crawl/.env; never commit or share it")

    registry_address = Web3.to_checksum_address(os.environ["ERC8004_REGISTRY_ADDRESS"])
    chain_id = int(os.environ["ERC8004_CHAIN_ID"])
    agent_uri = os.environ["ERC8004_AGENT_URI"].strip()
    if not agent_uri.startswith("https://"):
        raise ValueError("ERC8004_AGENT_URI must be the public HTTPS metadata URL")
    if chain_id != FUJI_CHAIN_ID:
        raise ValueError(f"This demo registration script is restricted to Avalanche Fuji ({FUJI_CHAIN_ID})")
    if registry_address != Web3.to_checksum_address(FUJI_IDENTITY_REGISTRY):
        raise ValueError(f"Unexpected Fuji Identity Registry address: {registry_address}")

    # Validate the public file before spending testnet gas.
    metadata = fetch_public_metadata(agent_uri)

    web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not web3.is_connected():
        raise RuntimeError("ERC8004_RPC_URL is unreachable")
    if web3.eth.chain_id != chain_id:
        raise RuntimeError(f"RPC chain ID {web3.eth.chain_id} does not match ERC8004_CHAIN_ID={chain_id}")
    if not web3.eth.get_code(registry_address):
        raise RuntimeError(f"No contract code found at ERC-8004 registry {registry_address}")

    account = web3.eth.account.from_key(private_key)
    registry_id = f"eip155:{chain_id}:{registry_address}"
    registry = web3.eth.contract(address=registry_address, abi=ABI)
    registrations = metadata.get("registrations", [])
    if not isinstance(registrations, list):
        raise RuntimeError("Metadata 'registrations' must be a JSON array")

    # Be safe to rerun after a successful registration: verify the recorded token
    # rather than minting another agent identity for the same metadata file.
    existing = [
        item for item in registrations
        if isinstance(item, dict)
        and isinstance(item.get("agentRegistry"), str)
        and item["agentRegistry"].lower() == registry_id.lower()
    ]
    if existing:
        if len(existing) != 1:
            raise RuntimeError(f"Metadata has multiple registration entries for {registry_id}; resolve manually")
        agent_id = int(existing[0]["agentId"])
        try:
            owner = registry.functions.ownerOf(agent_id).call()
            registered_uri = registry.functions.tokenURI(agent_id).call()
        except Exception as exc:
            raise RuntimeError(f"Metadata agentId={agent_id} is not readable on the configured registry") from exc
        if owner.lower() != account.address.lower() or registered_uri != agent_uri:
            raise RuntimeError(
                f"Existing Fuji registration does not match this key/URI: agentId={agent_id}, "
                f"owner={owner}, tokenURI={registered_uri}"
            )
        print(f"Already registered and verified: agentId={agent_id}; registry={registry_id}")
        print(f"Metadata: {agent_uri}")
        return

    call = registry.functions.register(agent_uri)
    gas_limit = int(call.estimate_gas({"from": account.address}) * 1.2)
    gas_price = web3.eth.gas_price
    estimated_cost = gas_limit * gas_price
    balance = web3.eth.get_balance(account.address)
    if balance < estimated_cost:
        raise RuntimeError(
            f"Registration wallet {account.address} lacks Fuji AVAX for gas: "
            f"balance={web3.from_wei(balance, 'ether')} AVAX, "
            f"estimated={web3.from_wei(estimated_cost, 'ether')} AVAX"
        )

    transaction = call.build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "chainId": chain_id,
        "gas": gas_limit,
        "gasPrice": gas_price,
    })
    signed = web3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Registration submitted: tx={tx_hash.hex()}; waiting for Fuji confirmation...")
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        raise RuntimeError(f"ERC-8004 registration reverted: {tx_hash.hex()}")

    events = registry.events.Registered().process_receipt(receipt)
    if not events:
        raise RuntimeError(f"Transaction succeeded but emitted no Registered event: {tx_hash.hex()}")
    event = next(
        (item for item in events if item["args"]["owner"].lower() == account.address.lower()),
        events[0],
    )
    agent_id = int(event["args"]["agentId"])

    registrations = [
        item for item in registrations
        if not isinstance(item, dict) or item.get("agentRegistry", "").lower() != registry_id.lower()
    ]
    registrations.append({"agentId": agent_id, "agentRegistry": registry_id})
    metadata["registrations"] = registrations
    metadata["active"] = True
    metadata["x402Support"] = True

    metadata_path = Path(os.getenv("ERC8004_METADATA_FILE", "app/agent-registration.example.json"))
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Registered agentId={agent_id}; tx={tx_hash.hex()}; registry={registry_id}")
    print(f"Metadata updated: {metadata_path}")
    print("Publish the updated JSON at ERC8004_AGENT_URI, then run scripts/verify_erc8004.py.")


if __name__ == "__main__":
    main()
