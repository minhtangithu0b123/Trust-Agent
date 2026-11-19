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

  const apiUrl = (process.env.TRUST_AGENT_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
  const requestBody: { query: string; k: number; thread_id?: string; stream?: boolean } = {
    query: payload.query.trim(),
    k: 5,
  };

  if ("thread_id" in payload && typeof payload.thread_id === "string" && payload.thread_id.trim()) {
    requestBody.thread_id = payload.thread_id.trim();
  }

  const isStreamRequested =
    ("stream" in payload && Boolean((payload as Record<string, unknown>).stream)) ||
    request.headers.get("accept")?.includes("text/event-stream");

  if (isStreamRequested) {
    requestBody.stream = true;
  }

  try {
    const rawApiKey = process.env.API_ACCESS_TOKEN;
    const apiKey = typeof rawApiKey === "string" && rawApiKey.trim().length > 0 ? rawApiKey.trim() : undefined;

    // Cold-starting the local cross-encoder and Router fan-out can exceed 90s.
    const timeoutSignal = AbortSignal.timeout(180_000);
    const signal =
      typeof AbortSignal.any === "function"
        ? AbortSignal.any([request.signal, timeoutSignal])
        : timeoutSignal;

    const headers: Record<string, string> = {
      "content-type": "application/json",
    };
    if (apiKey) {
      headers["X-API-Key"] = apiKey;
    }

    const upstream = await fetch(`${apiUrl}/router/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify(requestBody),
      cache: "no-store",
      signal,
    });

    const contentType = upstream.headers.get("content-type") || "";
    if (upstream.ok && contentType.includes("text/event-stream") && upstream.body) {
      return new Response(upstream.body, {
        status: 200,
        headers: {
          "content-type": "text/event-stream; charset=utf-8",
          "cache-control": "no-cache, no-transform",
          "connection": "keep-alive",
        },
      });
    }

    const body = await upstream.json().catch(() => null);

    if (!upstream.ok) {
      let detailMessage = "Đã xảy ra lỗi từ phía dịch vụ.";
      if (body && typeof body === "object" && "detail" in body) {
        const detail = (body as { detail: unknown }).detail;
        if (Array.isArray(detail)) {
          detailMessage = detail
            .map((item: unknown) => {
              if (typeof item === "object" && item !== null && "msg" in item) {
                return String((item as { msg: unknown }).msg);
              }
              return typeof item === "string" ? item : JSON.stringify(item);
            })
            .join(", ");
        } else if (typeof detail === "string") {
          detailMessage = detail;
        } else if (detail !== undefined && detail !== null) {
          detailMessage = String(detail);
        }
      } else if (upstream.status >= 502 && upstream.status <= 504) {
        detailMessage = `Dịch vụ Trust Agent tạm thời gián đoạn (mã HTTP ${upstream.status}). Vui lòng thử lại sau giây lát.`;
      }

      console.error(`[api/ask] Upstream returned status ${upstream.status}:`, detailMessage);
      return NextResponse.json({ detail: detailMessage }, { status: upstream.status });
    }

    if (!body) {
      console.error("[api/ask] Upstream returned non-JSON or empty response body.");
      return NextResponse.json(
        { detail: "Backend trả về dữ liệu không đúng định dạng." },
        { status: 502 },
      );
    }

    return NextResponse.json(body, { status: upstream.status });
  } catch (error: unknown) {
    console.error("[api/ask] Upstream error:", error);
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
      { detail: "Chưa kết nối được với Trust Agent API. Hãy kiểm tra backend và thử lại." },
      { status: 502 },
    );
  }
}
