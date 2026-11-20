import { NextResponse } from "next/server";

function upstreamUrl(id: string) {
  return `${(process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "")}/api/conversations/${encodeURIComponent(id)}`;
}
function headers() {
  const result: Record<string, string> = { "content-type": "application/json" };
  const key = process.env.API_ACCESS_TOKEN?.trim();
  if (key) result["X-API-Key"] = key;
  return result;
}
async function paramsValue(context: { params: Promise<{ id: string }> | { id: string } }) {
  return (await context.params).id;
}
async function forward(response: Response) {
  if (response.status === 204) return new Response(null, { status: 200 });
  const body = await response.json().catch(() => null);
  return NextResponse.json(body ?? { detail: "Backend returned an invalid response." }, { status: response.status });
}

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> | { id: string } }) {
  let body: unknown;
  try { body = await request.json(); } catch { return NextResponse.json({ detail: "Invalid JSON body." }, { status: 400 }); }
  if (body === null || typeof body !== "object" || Array.isArray(body) || typeof (body as { title?: unknown }).title !== "string" || !(body as { title: string }).title.trim()) {
    return NextResponse.json({ detail: "title must be a non-empty string." }, { status: 400 });
  }
  try { return await forward(await fetch(upstreamUrl(await paramsValue(context)), { method: "PATCH", headers: headers(), body: JSON.stringify(body) })); }
  catch { return NextResponse.json({ detail: "Cannot connect to Trust Agent API." }, { status: 502 }); }
}

export async function DELETE(_request: Request, context: { params: Promise<{ id: string }> | { id: string } }) {
  try {
    const response = await fetch(upstreamUrl(await paramsValue(context)), { method: "DELETE", headers: headers() });
    if (response.status === 204) return new Response(null, { status: 200 });
    return await forward(response);
  } catch (error) { if (String(error).includes("Invalid response status code 204")) return new Response(null, { status: 200 }); return NextResponse.json({ detail: "Cannot connect to Trust Agent API." }, { status: 502 }); }
}