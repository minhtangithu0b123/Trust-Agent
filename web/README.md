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

## API contract

The proxy sends `{ "query": "...", "k": 5 }` to `POST /router/ask`. It passes through the backend's `answer`, `status`, and `citations` fields. The current UI handles `verified`, `insufficient_evidence`, `needs_clarification`, and `provider_error` statuses.
