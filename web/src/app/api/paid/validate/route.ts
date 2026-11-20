import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(request: Request) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Yêu cầu không đúng định dạng." }, { status: 400 });
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("query" in payload) ||
    typeof payload.query !== "string" ||
    payload.query.trim().length < 2
  ) {
    return NextResponse.json({ detail: "Hãy nhập câu hỏi có ít nhất 2 ký tự." }, { status: 400 });
  }

  const apiUrl = (process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000")
    .trim()
    .replace(/\/+$/, "");
  const headers = new Headers({ "content-type": "application/json" });
  const apiKey = process.env.API_ACCESS_TOKEN?.trim();
  if (apiKey) headers.set("X-API-Key", apiKey);
  const conversationId =
    "conversation_id" in payload && typeof payload.conversation_id === "string"
      ? payload.conversation_id.trim()
      : "";

  try {
    const upstream = await fetch(`${apiUrl}/paid/traffic/validate`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: payload.query.trim(),
        k: 5,
        conversation_id: conversationId || undefined,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    const body = await upstream.json().catch(() => ({ detail: "Phản hồi không hợp lệ." }));
    return NextResponse.json(body, { status: upstream.status });
  } catch (error) {
    console.error("[api/paid/validate] Upstream error:", error);
    return NextResponse.json(
      { detail: "Chưa kết nối được với Trust Agent API." },
      { status: 502 },
    );
  }
}
