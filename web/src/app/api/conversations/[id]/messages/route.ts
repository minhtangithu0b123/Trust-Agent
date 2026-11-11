import { NextResponse } from "next/server";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> | { id: string } }) {
  const id = (await context.params).id;
  const base = (process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
  const headers: Record<string, string> = { "content-type": "application/json" };
  const key = process.env.API_ACCESS_TOKEN?.trim();
  if (key) headers["X-API-Key"] = key;
  try {
    const response = await fetch(`${base}/api/conversations/${encodeURIComponent(id)}/messages`, { headers, cache: "no-store" });
    const body = await response.json().catch(() => null);
    return NextResponse.json(body ?? { detail: "Backend returned an invalid response." }, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Cannot connect to Trust Agent API." }, { status: 502 });
  }
}