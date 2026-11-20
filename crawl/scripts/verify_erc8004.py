"""Read-only verification for a Trust Agent ERC-8004 Fuji registration."""

import json
import os
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from web3 import Web3

from register_erc8004 import ABI, FUJI_CHAIN_ID, FUJI_IDENTITY_REGISTRY, REGISTRATION_TYPE


def main() -> None:
    load_dotenv(".env")
    rpc_url = os.environ["ERC8004_RPC_URL"].strip()
    agent_uri = os.environ["ERC8004_AGENT_URI"].strip()
    registry_address = Web3.to_checksum_address(os.environ["ERC8004_REGISTRY_ADDRESS"])
    chain_id = int(os.environ["ERC8004_CHAIN_ID"])

    if chain_id != FUJI_CHAIN_ID:
        raise RuntimeError(f"Expected Avalanche Fuji chain ID {FUJI_CHAIN_ID}, got {chain_id}")
    if registry_address != Web3.to_checksum_address(FUJI_IDENTITY_REGISTRY):
        raise RuntimeError(f"Unexpected Fuji Identity Registry address: {registry_address}")
    if not agent_uri.startswith("https://"):
        raise RuntimeError("ERC8004_AGENT_URI must use HTTPS")

    request = Request(agent_uri, headers={"User-Agent": "TrustAgent-ERC8004-Verify/1.0"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"Metadata URL returned HTTP {response.status}")
        metadata = json.loads(response.read().decode("utf-8"))
    if not isinstance(metadata, dict) or metadata.get("type") != REGISTRATION_TYPE:
        raise RuntimeError("Public URL does not serve valid ERC-8004 registration JSON")
    services = metadata.get("services", [])
    if not isinstance(services, list):
        raise RuntimeError("Metadata 'services' must be a JSON array")
    expected_web_url = os.getenv("TRUST_AGENT_WEB_URL", "https://trust-agent-eight.vercel.app").strip().rstrip("/")
    web_service = next((item for item in services if isinstance(item, dict) and item.get("name") == "web"), None)
    x402_service = next((item for item in services if isinstance(item, dict) and item.get("name") == "x402"), None)
    if not web_service or web_service.get("endpoint", "").rstrip("/") != expected_web_url:
        raise RuntimeError(f"Metadata web service must point to TRUST_AGENT_WEB_URL ({expected_web_url})")
    x402_endpoint = x402_service.get("endpoint", "") if x402_service else ""
    if not (x402_endpoint.endswith("/paid/traffic/ask") or x402_endpoint.endswith("/api/paid/ask")):
        raise RuntimeError("Metadata must publish a valid x402 endpoint")
    if metadata.get("x402Support") is not True:
        raise RuntimeError("Public metadata does not declare x402 support")

    registry_id = f"eip155:{chain_id}:{registry_address}"
    registrations = metadata.get("registrations", [])
    if not isinstance(registrations, list):
        raise RuntimeError("Metadata 'registrations' must be a JSON array")
    matching = [
        item for item in registrations
        if isinstance(item, dict)
        and isinstance(item.get("agentRegistry"), str)
        and item["agentRegistry"].lower() == registry_id.lower()
    ]
    if len(matching) != 1:
        raise RuntimeError(f"Expected exactly one Fuji registration for {registry_id}; found {len(matching)}")
    agent_id = int(matching[0]["agentId"])

    web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not web3.is_connected() or web3.eth.chain_id != chain_id:
        raise RuntimeError("RPC unavailable or connected to a chain other than Avalanche Fuji")
    if not web3.eth.get_code(registry_address):
        raise RuntimeError(f"No Identity Registry contract at {registry_address}")

    registry = web3.eth.contract(address=registry_address, abi=ABI)
    owner = registry.functions.ownerOf(agent_id).call()
    registered_uri = registry.functions.tokenURI(agent_id).call()
    if registered_uri != agent_uri:
        raise RuntimeError(f"On-chain tokenURI differs from ERC8004_AGENT_URI: {registered_uri}")

    print("ERC-8004 Identity registration verified")
    print(f"Network: Avalanche Fuji ({chain_id})")
    print(f"Registry: {registry_address}")
    print(f"Agent ID: {agent_id}")
    print(f"Owner: {owner}")
    print(f"Metadata: {agent_uri}")
    print(f"Explorer: https://testnet.snowtrace.io/address/{registry_address}?tab=contract")


if __name__ == "__main__":
    main()
