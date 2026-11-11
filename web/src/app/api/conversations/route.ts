import { NextResponse } from "next/server";

function upstreamUrl(path = "") {
  return `${(process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "")}/api/conversations${path}`;
}

function headers() {
  const result: Record<string, string> = { "content-type": "application/json" };
  const key = process.env.API_ACCESS_TOKEN?.trim();
  if (key) result["X-API-Key"] = key;
  return result;
}

async function forward(response: Response) {
  const body = await response.json().catch(() => null);
  return NextResponse.json(body ?? { detail: "Backend returned an invalid response." }, { status: response.status });
}

export async function GET() {
  try {
    return await forward(await fetch(upstreamUrl(), { headers: headers(), cache: "no-store" }));
  } catch {
    return NextResponse.json({ detail: "Cannot connect to Trust Agent API." }, { status: 502 });
  }
}

export async function POST(request: Request) {
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 }); }
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return NextResponse.json({ detail: "Request body must be an object." }, { status: 400 });
  }
  try {
    return await forward(await fetch(upstreamUrl(), { method: "POST", headers: headers(), body: JSON.stringify(body) }));
  } catch {
    return NextResponse.json({ detail: "Cannot connect to Trust Agent API." }, { status: 502 });
  }
}