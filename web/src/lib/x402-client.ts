"use client";

import { x402Client } from "@x402/core/client";
import type { PaymentPolicy } from "@x402/core/client";
import type { PaymentRequirements } from "@x402/core/types";
import type { ClientEvmSigner } from "@x402/evm";
import { registerExactEvmScheme } from "@x402/evm/exact/client";
import { wrapFetchWithPayment, x402HTTPClient } from "@x402/fetch";
import { createWalletClient, custom, type Address, type TypedDataDomain } from "viem";
import { avalancheFuji } from "viem/chains";

export const AVALANCHE_FUJI_NETWORK = "eip155:43113";
export const AVALANCHE_FUJI_CHAIN_ID = "0xa869";
export const AVALANCHE_FUJI_USDC = "0x5425890298aed601595a70AB815c96711a31Bc65";
export const PAID_ASK_AMOUNT = "10000"; // 0.01 USDC, 6 decimals

export type InjectedEvmProvider = {
  request(args: { method: string; params?: unknown[] | object }): Promise<unknown>;
};

declare global {
  interface Window {
    ethereum?: InjectedEvmProvider;
  }
}

function getInjectedProvider(): InjectedEvmProvider {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new Error("Không tìm thấy ví EVM trong trình duyệt. Hãy cài MetaMask, Rabby hoặc Coinbase Wallet.");
  }
  return window.ethereum;
}

async function ensureAvalancheFuji(provider: InjectedEvmProvider) {
  const chainId = await provider.request({ method: "eth_chainId" });
  if (String(chainId).toLowerCase() === AVALANCHE_FUJI_CHAIN_ID) return;

  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: AVALANCHE_FUJI_CHAIN_ID }],
    });
  } catch (error) {
    const code = (error as { code?: number })?.code;
    if (code !== 4902) throw error;
    await provider.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: AVALANCHE_FUJI_CHAIN_ID,
          chainName: "Avalanche Fuji Testnet",
          nativeCurrency: { name: "Avalanche", symbol: "AVAX", decimals: 18 },
          rpcUrls: ["https://api.avax-test.network/ext/bc/C/rpc"],
          blockExplorerUrls: ["https://testnet.snowtrace.io"],
        },
      ],
    });
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: AVALANCHE_FUJI_CHAIN_ID }],
    });
  }
}

export async function connectAvalancheFujiWallet(): Promise<Address> {
  const provider = getInjectedProvider();
  const accounts = await provider.request({ method: "eth_requestAccounts" });
  if (!Array.isArray(accounts) || typeof accounts[0] !== "string") {
    throw new Error("Ví chưa cung cấp địa chỉ tài khoản.");
  }
  await ensureAvalancheFuji(provider);
  return accounts[0] as Address;
}

export async function createPaidX402Client(address: Address) {
  const provider = getInjectedProvider();
  await ensureAvalancheFuji(provider);

  const walletClient = createWalletClient({
    account: address,
    chain: avalancheFuji,
    transport: custom(provider as never),
  });

  const signer: ClientEvmSigner = {
    address,
    signTypedData: (typedData) =>
      walletClient.signTypedData({
        account: address,
        domain: typedData.domain as TypedDataDomain,
        types: typedData.types as never,
        primaryType: typedData.primaryType,
        message: typedData.message as never,
      } as never),
  };

  const client = new x402Client();
  client.setSpendControls({
    maxAmountPerPayment: "$0.01",
    allowedAssets: [
      {
        network: AVALANCHE_FUJI_NETWORK,
        asset: AVALANCHE_FUJI_USDC,
        maxAmountPerPayment: PAID_ASK_AMOUNT,
      },
    ],
  });
  registerExactEvmScheme(client, {
    signer,
    networks: [AVALANCHE_FUJI_NETWORK],
    policies: [
      ((_version: number, requirements: PaymentRequirements[]) =>
        requirements.filter(
          (requirement: PaymentRequirements) =>
            requirement.network === AVALANCHE_FUJI_NETWORK &&
            requirement.scheme === "exact" &&
            requirement.asset.toLowerCase() === AVALANCHE_FUJI_USDC.toLowerCase() &&
            requirement.amount === PAID_ASK_AMOUNT,
        )) as PaymentPolicy,
    ],
  });

  client.onBeforePaymentCreation(async ({ selectedRequirements }) => {
    const expectedPayTo = process.env.NEXT_PUBLIC_X402_PAY_TO?.trim().toLowerCase();
    const payTo = selectedRequirements.payTo;
    if (
      selectedRequirements.network !== AVALANCHE_FUJI_NETWORK ||
      selectedRequirements.scheme !== "exact" ||
      selectedRequirements.asset.toLowerCase() !== AVALANCHE_FUJI_USDC.toLowerCase() ||
      selectedRequirements.amount !== PAID_ASK_AMOUNT ||
      (expectedPayTo && payTo.toLowerCase() !== expectedPayTo)
    ) {
      return {
        abort: true,
        reason: "Điều khoản thanh toán không khớp cấu hình an toàn của Trust Agent.",
      };
    }

    const confirmed = window.confirm(
      `Xác nhận thanh toán 0.01 USDC trên Avalanche Fuji?\n\nVí nhận: ${payTo}\n\nVí sẽ yêu cầu ký xác nhận. Private key không rời khỏi ví.`,
    );
    if (!confirmed) {
      return { abort: true, reason: "Bạn đã hủy thanh toán; chưa gửi yêu cầu trả phí." };
    }
  });

  const httpClient = new x402HTTPClient(client);
  return {
    fetchWithPayment: wrapFetchWithPayment(fetch, client),
    getSettlement: (response: Response) =>
      httpClient.getPaymentSettleResponse((name) => response.headers.get(name)),
  };
}
