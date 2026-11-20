# Hoàn tất ERC-8004 Identity cho demo Avalanche Fuji

Tài liệu này hướng dẫn chủ backend/production hoàn tất **đăng ký Identity ERC-8004** cho Trust Agent trên Avalanche Fuji. Repo có script đăng ký và endpoint metadata; chủ sở hữu agent vẫn phải cấu hình ví, công khai metadata và gửi một giao dịch testnet.

> Đây là hướng dẫn testnet. Không dùng private key mainnet hoặc ký giao dịch nếu chưa xác nhận đúng Fuji, đúng Identity Registry và đúng agent metadata.

## 1. Những gì ERC-8004 đang làm trong dự án

- Identity Registry cấp một `agentId` dạng NFT cho agent.
- `agentURI` trỏ đến JSON công khai mô tả agent và các service.
- Metadata công bố web app và endpoint trả phí x402.
- Trust Agent có registration Base Sepolia agent ID `10773` và Avalanche Fuji agent ID `355` (tx `0x8b9b1a0f908151f9d07838191a2f2a61ec506bc41809ea1a7f58c38373438692`). Cả hai registration cùng được khai báo trong metadata.
- Fuji Identity Registry: `0x8004A818BFB912233c491871b3d84c89A494BD9e`, chain ID `43113`.

ERC-8004 Reputation/Validation registry và cơ chế ghi điểm reputation tự động chưa được triển khai trong luồng này. Không diễn giải việc có Identity NFT là đã được đánh giá uy tín on-chain.

Địa chỉ Identity Registry Fuji và cấu trúc `registration-v1` cần được đối chiếu với [repo hợp đồng ERC-8004](https://github.com/erc-8004/erc-8004-contracts) và [đặc tả EIP-8004](https://eips.ethereum.org/EIPS/eip-8004).

## 2. Chuẩn bị quyền và ví

Chủ backend/agent cần:

1. Quyền deploy Vercel project (root directory `web`) để phục vụ metadata tĩnh `web/public/agent-registration.json`.
2. Một ví EVM riêng cho registration, có **AVAX testnet Fuji** để trả gas.
3. Private key của ví đó được lưu cục bộ trong `crawl/.env` dưới `ERC8004_PRIVATE_KEY`.
4. Vercel deployment HTTPS ổn định. URI mặc định của demo là `https://trust-agent-eight.vercel.app/agent-registration.json`.

Ví đăng ký có thể khác ví nhận x402 `X402_PAY_TO`. Ví registration sẽ sở hữu ERC-8004 Identity NFT. Không gửi private key qua chat, không commit `.env`, và không tái sử dụng `ANCHOR_PRIVATE_KEY` cho mục đích này.

## 3. Deploy metadata lên Vercel trước

1. Đưa code mới nhất lên Vercel project của Trust Agent với Root Directory `web`. Metadata Fuji hiện là file tĩnh trong `web/public`, vì vậy URI không phụ thuộc trạng thái Cloudflare Tunnel:

   ```text
   GET https://trust-agent-eight.vercel.app/agent-registration.json
   ```

2. Trong `crawl/.env`, đặt URL FE chính thức (giá trị này cũng được backend metadata endpoint cũ dùng cho registration Base):

   ```env
   TRUST_AGENT_WEB_URL=https://trust-agent-eight.vercel.app
   ```

   Nếu Vercel project dùng domain khác, thay bằng domain thật của project.

3. Mở URL Vercel và xác nhận:
   - Trả HTTP 200 với JSON.
   - `type` là `https://eips.ethereum.org/EIPS/eip-8004#registration-v1`.
   - `services` có `web` trỏ tới Vercel và `x402` trỏ tới `https://trust-agent-eight.vercel.app/api/paid/ask`.
   - `x402Support` là `true` khi backend đã bật x402.
   - Không có URL Quick Tunnel cũ hoặc endpoint `/docs` bị khai báo nhầm thành web app.

4. Metadata cần công khai **trước** giao dịch registration. Dùng URI Vercel ổn định; giữ nguyên URI này trong thời gian agent được quảng bá.

## 4. Điền cấu hình ERC-8004

Trong `crawl/.env`, đặt các giá trị sau. Metadata Fuji nằm trên Vercel, còn endpoint x402 được FE proxy về backend.

```env
ERC8004_RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
ERC8004_PRIVATE_KEY=<private-key-cua-vi-registration-fuji>
ERC8004_REGISTRY_ADDRESS=0x8004A818BFB912233c491871b3d84c89A494BD9e
ERC8004_CHAIN_ID=43113
ERC8004_AGENT_URI=https://trust-agent-eight.vercel.app/agent-registration.json
ERC8004_METADATA_FILE=../web/public/agent-registration.json
```

Nếu `.env` server đã có `ERC8004_METADATA_FILE` trỏ tới `app/agent-registration.example.json`, hãy đổi nó thành `../web/public/agent-registration.json`. Giá trị trong `.env` ghi đè giá trị mặc định/mẫu.

`ERC8004_PRIVATE_KEY` chỉ dùng để ký giao dịch đăng ký; script không in key. Ví phải có Fuji AVAX. Script sẽ kiểm tra network, địa chỉ registry, bytecode contract, metadata HTTPS, và số dư gas trước khi gửi.

### Chạy script trên máy backend

Trong thư mục `crawl/` của checkout có code mới nhất:

```bash
source .venv/bin/activate
pip install -e '.[blockchain]'
python scripts/register_erc8004.py
```

Nếu dùng Windows PowerShell để chạy script:

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[blockchain]"
python scripts/register_erc8004.py
```

Giao dịch này tạo ERC-8004 Identity NFT mới trên Fuji và tiêu thụ một lượng nhỏ Fuji AVAX làm gas. Script chờ giao dịch được xác nhận, đọc event `Registered`, rồi thêm `agentId` và `agentRegistry` vào `web/public/agent-registration.json`.

Script có kiểm tra lặp: nếu metadata đã có Fuji agent ID, nó kiểm tra owner và `tokenURI` on-chain rồi dừng thay vì mint thêm token. Nếu giao dịch thành công nhưng bị ngắt trước khi cập nhật file metadata, tra transaction/agent ID trong explorer và cập nhật entry thủ công trước khi chạy lại để tránh đăng ký trùng.

## 5. Public metadata sau khi đăng ký

Sau khi script báo thành công:

1. Kiểm tra `web/public/agent-registration.json` có entry mới dạng:

   ```json
   {
     "agentId": 12345,
     "agentRegistry": "eip155:43113:0x8004A818BFB912233c491871b3d84c89A494BD9e"
   }
   ```

2. Đảm bảo entry Base Sepolia cũ vẫn còn nếu agent đã đăng ký ở Base.
3. Script ghi entry Fuji vào `web/public/agent-registration.json`. Commit/push file JSON metadata công khai theo quy trình repo, sau đó redeploy Vercel. Mở lại URI Vercel và xác nhận entry Fuji xuất hiện.
4. Không commit `crawl/.env` hoặc private key.

## 6. Xác minh on-chain và metadata

Sau khi public metadata đã có Fuji entry, vẫn ở `crawl/`, chạy:

```bash
python scripts/verify_erc8004.py
```

Hoặc trong PowerShell:

```powershell
python scripts/verify_erc8004.py
```

Verifier chỉ đọc dữ liệu. Nó xác nhận RPC đang ở Fuji, contract có bytecode, metadata công khai có đúng một registration Fuji, và `ownerOf(agentId)`/`tokenURI(agentId)` trên chain khớp với metadata URL đã cấu hình. Script in ra agent ID, địa chỉ owner và link explorer.

Kiểm tra thêm bằng tay:

1. Mở transaction hash do script `register_erc8004.py` in ra trên Avalanche Fuji explorer.
2. Xác nhận transaction thành công và event `Registered` chứa đúng ví owner/agent ID.
3. Mở `ERC8004_AGENT_URI` từ trình duyệt ẩn danh để chắc chắn metadata không yêu cầu đăng nhập/API key.
4. Đối chiếu `agentRegistry` chính xác là `eip155:43113:0x8004A818BFB912233c491871b3d84c89A494BD9e`.

## 7. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `ERC8004_AGENT_URI must be the public HTTPS metadata URL` | Điền URL HTTPS đầy đủ đến `/agent-registration.json`. |
| Cannot fetch valid public JSON | Vercel chưa deploy file metadata, URL sai hoặc TLS lỗi. Mở URL trong trình duyệt trước. |
| RPC chain ID không phải 43113 | `ERC8004_RPC_URL` đang trỏ nhầm mạng; dùng Fuji C-Chain RPC. |
| No contract code found at registry | Sai chain/registry hoặc RPC chưa truy cập được. Không gửi giao dịch cho đến khi đúng address registry. |
| Thiếu Fuji AVAX | Nạp test AVAX vào ví được suy ra từ `ERC8004_PRIVATE_KEY`, rồi chạy lại. Không cần dùng USDC payer. |
| Metadata thiếu `agentId` sau registration | Đăng lại JSON đã cập nhật lên Vercel; chạy `verify_erc8004.py` sau đó. |
| `ownerOf` hoặc `tokenURI` không khớp | Không đăng ký lại ngay. Kiểm tra đúng private key, `ERC8004_AGENT_URI`, chain, registry address và registration JSON hiện đang public. |

## 8. Tiêu chí hoàn tất demo Identity

- [ ] `GET https://trust-agent-eight.vercel.app/agent-registration.json` truy cập công khai bằng HTTPS.
- [ ] Metadata có service web Vercel và x402 proxy `/api/paid/ask` chính xác.
- [x] Registration trên Fuji được xác nhận: agent ID `355`, tx `0x8b9b1a0f908151f9d07838191a2f2a61ec506bc41809ea1a7f58c38373438692`.
- [ ] Metadata public chứa entry `eip155:43113` mới.
- [ ] `python scripts/verify_erc8004.py` xác nhận `ownerOf` và `tokenURI` khớp.

Khi đủ các mục trên, **ERC-8004 Identity demo** hoàn tất. Reputation/Validation registry vẫn là phạm vi triển khai riêng, cần định nghĩa nguồn đánh giá và cơ chế chống spam trước khi ghi điểm on-chain.
