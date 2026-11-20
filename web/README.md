# Trust Agent web

Next.js App Router frontend for the Trust Agent API. The app calls its same-origin `/api/ask` route, which forwards requests to FastAPI's `/router/ask` endpoint. This keeps local browser requests same-origin and avoids requiring CORS configuration in FastAPI.

## Run locally

In one terminal, start the backend from `crawl/`:

```powershell
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd web
pnpm install
Copy-Item .env.example .env.local
pnpm dev
```

Open `http://localhost:3000`. Change `TRUST_AGENT_API_URL` in `.env.local` if FastAPI runs somewhere else. The API key remains on the server; do not prefix it with `NEXT_PUBLIC_`.

For a hosted backend with `REQUIRE_API_KEY=true`, set the same secret value as `API_ACCESS_TOKEN` in the Next.js service. The server-side `/api/ask` route forwards it as `X-API-Key`; it is never sent to the browser. Keep this API key separate from `INGEST_ADMIN_TOKEN` and `REWARD_ADMIN_TOKEN`.

## Paid x402 questions

The chat keeps the regular free `/router/ask` path. The separate **X402 · 0.01 USDC** action uses the same multi-domain router for traffic, labor, and tax questions, then proxies to `/paid/traffic/ask` through `/api/paid/ask`. The stable backend route name preserves compatibility with existing x402 clients. The user connects an injected EVM wallet (MetaMask, Rabby, Coinbase Wallet), switches to Avalanche Fuji, reviews the recipient and confirms before the wallet signs. The browser never receives or stores a private key. The client refuses payment challenges unless they specify exact x402, Avalanche Fuji, Fuji USDC, and exactly 0.01 USDC.

Set `NEXT_PUBLIC_X402_PAY_TO` in the Next.js deployment to the expected receiving wallet when available; this adds a recipient allowlist check. If omitted, the UI still shows the challenge recipient in a confirmation prompt. The backend deployment must separately have x402 enabled and a working `X402_FACILITATOR_URL`. Paid questions are persisted in the same server-side conversation history as free questions.

## API contract

The proxy sends `{ "query": "...", "k": 5 }` to `POST /router/ask`. It passes through the backend's `answer`, `status`, and `citations` fields. The current UI handles `verified`, `insufficient_evidence`, `needs_clarification`, and `provider_error` statuses.
