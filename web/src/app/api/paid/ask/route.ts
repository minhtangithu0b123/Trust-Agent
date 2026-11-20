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

  if (payload.query.trim().length > 2000) {
    return NextResponse.json(
      { detail: "Câu hỏi vượt quá độ dài cho phép (tối đa 2000 ký tự)." },
      { status: 400 },
    );
  }

  const apiUrl = (process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000")
    .trim()
    .replace(/\/+$/, "");
  const headers = new Headers({ "content-type": "application/json" });
  const apiKey = process.env.API_ACCESS_TOKEN?.trim();
  if (apiKey) headers.set("X-API-Key", apiKey);

  const paymentSignature = request.headers.get("PAYMENT-SIGNATURE");
  const legacyPayment = request.headers.get("X-PAYMENT");
  if (paymentSignature) headers.set("PAYMENT-SIGNATURE", paymentSignature);
  if (legacyPayment) headers.set("X-PAYMENT", legacyPayment);
  const conversationId =
    "conversation_id" in payload && typeof payload.conversation_id === "string"
      ? payload.conversation_id.trim()
      : "";

  try {
    const upstream = await fetch(`${apiUrl}/paid/traffic/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        query: payload.query.trim(),
        k: 5,
        conversation_id: conversationId || undefined,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(180_000),
    });

    const responseHeaders = new Headers();
    for (const name of ["content-type", "cache-control", "payment-required", "payment-response", "x-payment-response"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("[api/paid/ask] Upstream error:", error);
    const isTimeout =
      error instanceof Error &&
      (error.name === "TimeoutError" || error.name === "AbortError");

    if (isTimeout) {
      return NextResponse.json(
        { detail: "Yêu cầu tra cứu quá thời gian phản hồi từ Trust Agent API (timeout 180s). Vui lòng thử lại sau." },
        { status: 504 },
      );
    }

    return NextResponse.json(
      { detail: "Chưa kết nối được với paid Trust Agent API. Hãy kiểm tra backend và thử lại." },
      { status: 502 },
    );
  }
}
