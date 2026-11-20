"""Compile and deploy BatchAnchor.sol to the chain configured in crawl/.env."""

import os
from pathlib import Path

from dotenv import load_dotenv
from solcx import compile_source, install_solc
from web3 import Web3


def update_env(name: str, value: str) -> None:
    env_path = Path(".env")
    lines = env_path.read_text(encoding="utf-8").splitlines()
    prefix = f"{name}="
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = prefix + value
            break
    else:
        lines.append(prefix + value)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    load_dotenv(".env")
    rpc = os.environ["ANCHOR_RPC_URL"]
    private_key = os.environ["ANCHOR_PRIVATE_KEY"]
    expected_chain = int(os.getenv("ANCHOR_CHAIN_ID", "84532"))
    web3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not web3.is_connected() or web3.eth.chain_id != expected_chain:
        raise RuntimeError("RPC unavailable or chain id does not match ANCHOR_CHAIN_ID")
    account = web3.eth.account.from_key(private_key)
    balance = web3.eth.get_balance(account.address)
    print(f"Connected to chain {expected_chain}; deployer {account.address}; balance {web3.from_wei(balance, 'ether')} test ETH")
    if balance == 0:
        raise RuntimeError("The test wallet has no ETH for deployment gas")

    install_solc("0.8.30")
    source_path = Path("contracts/BatchAnchor.sol")
    compiled = compile_source(source_path.read_text(encoding="utf-8"), output_values=["abi", "bin"], solc_version="0.8.30")
    _, artifact = next(iter(compiled.items()))
    factory = web3.eth.contract(abi=artifact["abi"], bytecode=artifact["bin"])
    transaction = factory.constructor().build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address),
        "chainId": expected_chain,
        "gas": 1_000_000,
        "maxFeePerGas": web3.eth.gas_price * 2,
        "maxPriorityFeePerGas": web3.to_wei(0.001, "gwei"),
    })
    signed = web3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1 or not receipt.contractAddress:
        raise RuntimeError(f"Contract deployment failed: {tx_hash.hex()}")
    contract_address = Web3.to_checksum_address(receipt.contractAddress)
    update_env("ANCHOR_CONTRACT_ADDRESS", contract_address)
    print(f"BatchAnchor deployed at {contract_address}; tx={tx_hash.hex()}")
    print("The address was saved to the ignored crawl/.env file.")


if __name__ == "__main__":
    main()
