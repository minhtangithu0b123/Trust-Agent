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
    typeof payload !== "object" || payload === null ||
    !("query" in payload) || typeof payload.query !== "string" || payload.query.trim().length < 2
  ) {
    return NextResponse.json({ detail: "Hãy nhập câu hỏi có ít nhất 2 ký tự." }, { status: 400 });
  }

  const apiUrl = process.env.TRUST_AGENT_API_URL ?? "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(`${apiUrl.replace(/\/$/, "")}/router/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ query: payload.query.trim(), k: 5 }),
      cache: "no-store",
      signal: AbortSignal.timeout(90_000),
    });
    const body = await upstream.json().catch(() => ({ detail: "Backend trả về dữ liệu không đọc được." }));
    return NextResponse.json(body, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { detail: "Chưa kết nối được với Trust Agent API. Hãy kiểm tra backend và thử lại." },
      { status: 502 },
    );
  }
}
