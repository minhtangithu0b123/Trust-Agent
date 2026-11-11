import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { POST } from "../src/app/api/ask/route.ts";

// Helper: in-memory mock HTTP server simulating Node.js http.Server without sandbox TCP restrictions
const originalFetch = globalThis.fetch;
const activeMocks = new Map();
let mockCounter = 1;

globalThis.fetch = async (url, options = {}) => {
  const urlStr = typeof url === "string" ? url : url.toString();
  for (const [mockBaseUrl, handler] of activeMocks.entries()) {
    if (urlStr.startsWith(mockBaseUrl)) {
      return runMockHandler(handler, urlStr, options);
    }
  }
  return originalFetch(url, options);
};

function runMockHandler(handler, urlStr, options) {
  return new Promise((resolve, reject) => {
    let statusCode = 200;
    let responseHeaders = {};
    let responseBody = "";
    let destroyed = false;

    const signal = options.signal;
    if (signal?.aborted) {
      const err = new Error("The operation was aborted");
      err.name = "AbortError";
      return reject(err);
    }

    const abortHandler = () => {
      const err = new Error("The operation was aborted");
      err.name = "AbortError";
      reject(err);
    };

    if (signal) {
      signal.addEventListener("abort", abortHandler, { once: true });
    }

    const req = new EventEmitter();
    const parsedUrl = new URL(urlStr);
    req.url = parsedUrl.pathname + parsedUrl.search;
    req.method = options.method || "GET";
    req.headers = Object.fromEntries(
      Object.entries(options.headers || {}).map(([k, v]) => [k.toLowerCase(), v])
    );
    req.socket = {
      destroy: () => {
        destroyed = true;
        const err = new TypeError("fetch failed");
        err.cause = { code: "ECONNRESET", syscall: "read" };
        reject(err);
      },
    };

    const res = {
      writeHead: (code, headers = {}) => {
        statusCode = code;
        responseHeaders = { ...responseHeaders, ...headers };
      },
      setHeader: (name, val) => {
        responseHeaders[name.toLowerCase()] = val;
      },
      end: (chunk) => {
        if (destroyed) return;
        if (signal) {
          signal.removeEventListener("abort", abortHandler);
        }
        if (chunk) responseBody += chunk;
        const resp = new Response(responseBody, {
          status: statusCode,
          headers: responseHeaders,
        });
        resolve(resp);
      },
    };

    // Execute handler in microtask
    queueMicrotask(() => {
      try {
        handler(req, res);
        if (options.body) {
          req.emit("data", options.body);
        }
        req.emit("end");
      } catch (err) {
        reject(err);
      }
    });
  });
}

function createMockServer(handler) {
  const port = 50000 + (mockCounter++);
  const url = `http://127.0.0.1:${port}`;
  activeMocks.set(url, handler);
  return Promise.resolve({
    port,
    url,
    close: () => {
      activeMocks.delete(url);
      return Promise.resolve();
    },
  });
}

// Save initial env
const initialApiUrl = process.env.TRUST_AGENT_API_URL;
const initialApiKey = process.env.API_ACCESS_TOKEN;

function resetEnv() {
  if (initialApiUrl !== undefined) {
    process.env.TRUST_AGENT_API_URL = initialApiUrl;
  } else {
    delete process.env.TRUST_AGENT_API_URL;
  }
  if (initialApiKey !== undefined) {
    process.env.API_ACCESS_TOKEN = initialApiKey;
  } else {
    delete process.env.API_ACCESS_TOKEN;
  }
}

// ---------------------------------------------------------------------------
// SUITE 1: Request Body & Query Boundary Testing
// ---------------------------------------------------------------------------
test("1.1 Empty request body returns 400", async () => {
  resetEnv();
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "",
  });
  const res = await POST(req);
  assert.equal(res.status, 400);
  const data = await res.json();
  assert.equal(data.detail, "Yêu cầu không đúng định dạng.");
});

test("1.2 Malformed JSON returns 400", async () => {
  resetEnv();
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{ invalid_json: ",
  });
  const res = await POST(req);
  assert.equal(res.status, 400);
  const data = await res.json();
  assert.equal(data.detail, "Yêu cầu không đúng định dạng.");
});

test("1.3 Non-object payloads return 400", async () => {
  resetEnv();
  const invalidPayloads = [null, 123, true, "string query", []];
  for (const p of invalidPayloads) {
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    const res = await POST(req);
    assert.equal(res.status, 400, `Payload ${JSON.stringify(p)} should return 400`);
    const data = await res.json();
    assert.equal(data.detail, "Hãy nhập câu hỏi có ít nhất 2 ký tự.");
  }
});

test("1.4 Missing query property returns 400", async () => {
  resetEnv();
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ other: "field" }),
  });
  const res = await POST(req);
  assert.equal(res.status, 400);
  const data = await res.json();
  assert.equal(data.detail, "Hãy nhập câu hỏi có ít nhất 2 ký tự.");
});

test("1.5 Non-string query types return 400", async () => {
  resetEnv();
  const invalidQueries = [123, true, false, null, {}, ["query"]];
  for (const q of invalidQueries) {
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const res = await POST(req);
    assert.equal(res.status, 400, `query=${JSON.stringify(q)} should return 400`);
    const data = await res.json();
    assert.equal(data.detail, "Hãy nhập câu hỏi có ít nhất 2 ký tự.");
  }
});

test("1.6 Query length 0 and whitespace-only return 400", async () => {
  resetEnv();
  const queries = ["", " ", "   ", "\t\n  \r"];
  for (const q of queries) {
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const res = await POST(req);
    assert.equal(res.status, 400, `query='${q}' should return 400`);
    const data = await res.json();
    assert.equal(data.detail, "Hãy nhập câu hỏi có ít nhất 2 ký tự.");
  }
});

test("1.7 Query length 1 returns 400", async () => {
  resetEnv();
  const queries = ["a", " a ", " 1 "];
  for (const q of queries) {
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
    const res = await POST(req);
    assert.equal(res.status, 400, `query='${q}' should return 400`);
    const data = await res.json();
    assert.equal(data.detail, "Hãy nhập câu hỏi có ít nhất 2 ký tự.");
  }
});

test("1.8 Query length 2001 returns 400 max length exceeded", async () => {
  resetEnv();
  const longQuery = "a".repeat(2001);
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: longQuery }),
  });
  const res = await POST(req);
  assert.equal(res.status, 400);
  const data = await res.json();
  assert.equal(data.detail, "Câu hỏi vượt quá độ dài cho phép (tối đa 2000 ký tự).");
});

test("1.9 Query length 2000 is accepted and forwarded", async () => {
  let receivedBody = null;
  const mock = await createMockServer((req, res) => {
    let buf = "";
    req.on("data", (chunk) => (buf += chunk));
    req.on("end", () => {
      receivedBody = JSON.parse(buf);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ query: receivedBody.query, answer: "ok", status: "verified" }));
    });
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const query2000 = "x".repeat(2000);
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query2000 }),
    });
    const res = await POST(req);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.answer, "ok");
    assert.equal(receivedBody.query.length, 2000);
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("1.10 Query length 2 is accepted and trimmed", async () => {
  let receivedBody = null;
  const mock = await createMockServer((req, res) => {
    let buf = "";
    req.on("data", (chunk) => (buf += chunk));
    req.on("end", () => {
      receivedBody = JSON.parse(buf);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ query: receivedBody.query, answer: "ok", status: "verified" }));
    });
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "  ab  " }),
    });
    const res = await POST(req);
    assert.equal(res.status, 200);
    assert.equal(receivedBody.query, "ab");
    assert.equal(receivedBody.k, 5);
  } finally {
    await mock.close();
    resetEnv();
  }
});

// ---------------------------------------------------------------------------
// SUITE 2: thread_id Handling
// ---------------------------------------------------------------------------
test("2.1 thread_id omitted when missing, empty or whitespace", async () => {
  let receivedBodies = [];
  const mock = await createMockServer((req, res) => {
    let buf = "";
    req.on("data", (chunk) => (buf += chunk));
    req.on("end", () => {
      receivedBodies.push(JSON.parse(buf));
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ query: "ok", answer: "ok", status: "verified" }));
    });
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const testCases = [
      { query: "câu hỏi số 1" },
      { query: "câu hỏi số 2", thread_id: "" },
      { query: "câu hỏi số 3", thread_id: "    " },
      { query: "câu hỏi số 4", thread_id: 12345 },
      { query: "câu hỏi số 5", thread_id: null },
      { query: "câu hỏi số 6", thread_id: { id: "abc" } },
    ];

    for (const tc of testCases) {
      const req = new Request("http://localhost/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tc),
      });
      const res = await POST(req);
      assert.equal(res.status, 200);
    }

    assert.equal(receivedBodies.length, 6);
    for (const b of receivedBodies) {
      assert.equal("thread_id" in b, false, `thread_id should not exist in: ${JSON.stringify(b)}`);
    }
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("2.2 thread_id included and trimmed when valid string", async () => {
  let receivedBody = null;
  const mock = await createMockServer((req, res) => {
    let buf = "";
    req.on("data", (chunk) => (buf += chunk));
    req.on("end", () => {
      receivedBody = JSON.parse(buf);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ query: "ok", answer: "ok", status: "verified" }));
    });
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "luật lao động", thread_id: "  session-999  " }),
    });
    const res = await POST(req);
    assert.equal(res.status, 200);
    assert.equal(receivedBody.thread_id, "session-999");
  } finally {
    await mock.close();
    resetEnv();
  }
});

// ---------------------------------------------------------------------------
// SUITE 3: Upstream URL Resolution & Environment Variables
// ---------------------------------------------------------------------------
test("3.1 TRUST_AGENT_API_URL trailing slashes are stripped", async () => {
  let requestPath = null;
  const mock = await createMockServer((req, res) => {
    requestPath = req.url;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ query: "ok", answer: "ok", status: "verified" }));
  });

  try {
    // Set URL with multiple trailing slashes
    process.env.TRUST_AGENT_API_URL = `${mock.url}///`;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "kiểm tra URL" }),
    });
    const res = await POST(req);
    assert.equal(res.status, 200);
    assert.equal(requestPath, "/router/ask");
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("3.2 TRUST_AGENT_API_URL empty string falls back to default 127.0.0.1:8000", async () => {
  resetEnv();
  process.env.TRUST_AGENT_API_URL = "";
  // When default URL is used and backend is not at 8000, should attempt 127.0.0.1:8000 and return 502
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "kiểm tra default URL" }),
  });
  const res = await POST(req);
  // Expect 502 connection refused because 8000 is not running
  assert.equal(res.status, 502);
  const data = await res.json();
  assert.equal(data.detail, "Chưa kết nối được với Trust Agent API. Hãy kiểm tra backend và thử lại.");
});

test("3.3 TRUST_AGENT_API_URL with whitespace-only behaves (stress test)", async () => {
  resetEnv();
  process.env.TRUST_AGENT_API_URL = "    ";
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "kiểm tra whitespace URL" }),
  });
  const res = await POST(req);
  // When whitespace trimmed becomes "", fetch("/router/ask") throws TypeError, caught as 502
  assert.equal(res.status, 502);
});

test("3.4 API_ACCESS_TOKEN handling in request headers", async () => {
  let receivedHeaders = null;
  const mock = await createMockServer((req, res) => {
    receivedHeaders = req.headers;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ query: "ok", answer: "ok", status: "verified" }));
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;

    // Case A: token present
    process.env.API_ACCESS_TOKEN = "  secret-token-123  ";
    const req1 = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "kiểm tra token" }),
    });
    await POST(req1);
    assert.equal(receivedHeaders["x-api-key"], "secret-token-123");

    // Case B: token empty string or whitespace
    process.env.API_ACCESS_TOKEN = "   ";
    const req2 = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "kiểm tra token empty" }),
    });
    await POST(req2);
    assert.equal(receivedHeaders["x-api-key"], undefined);
  } finally {
    await mock.close();
    resetEnv();
  }
});

// ---------------------------------------------------------------------------
// SUITE 4: FastAPI 422 Error Serialization & Gateway Statuses
// ---------------------------------------------------------------------------
test("4.1 FastAPI 422 array of dicts serialized to comma-separated msg", async () => {
  const mock = await createMockServer((req, res) => {
    res.writeHead(422, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        detail: [
          { loc: ["body", "query"], msg: "String should have at least 2 characters", type: "string_too_short" },
          { loc: ["body", "k"], msg: "Input should be greater than 0", type: "greater_than" },
        ],
      }),
    );
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "hợp lệ nhưng upstream trả 422" }),
    });
    const res = await POST(req);
    assert.equal(res.status, 422);
    const data = await res.json();
    assert.equal(data.detail, "String should have at least 2 characters, Input should be greater than 0");
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("4.2 Upstream 422 with string detail returned directly", async () => {
  const mock = await createMockServer((req, res) => {
    res.writeHead(422, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Unprocessable Entity custom message" }));
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "hợp lệ nhưng upstream lỗi" }),
    });
    const res = await POST(req);
    assert.equal(res.status, 422);
    const data = await res.json();
    assert.equal(data.detail, "Unprocessable Entity custom message");
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("4.3 Upstream 502/503/504 gateway statuses map to Vietnamese notice when body empty", async () => {
  for (const status of [502, 503, 504]) {
    const mock = await createMockServer((req, res) => {
      res.writeHead(status, { "Content-Type": "text/html" });
      res.end("<html><body>Gateway Error</body></html>");
    });

    try {
      process.env.TRUST_AGENT_API_URL = mock.url;
      const req = new Request("http://localhost/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "hỏi khi gateway lỗi" }),
      });
      const res = await POST(req);
      assert.equal(res.status, status);
      const data = await res.json();
      assert.equal(
        data.detail,
        `Dịch vụ Trust Agent tạm thời gián đoạn (mã HTTP ${status}). Vui lòng thử lại sau giây lát.`,
      );
    } finally {
      await mock.close();
    }
  }
  resetEnv();
});

test("4.4 Upstream returns 200 with invalid/empty body triggers 502 formatting error", async () => {
  const mock = await createMockServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(""); // empty body
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "hỏi khi backend trả rỗng" }),
    });
    const res = await POST(req);
    assert.equal(res.status, 502);
    const data = await res.json();
    assert.equal(data.detail, "Backend trả về dữ liệu không đúng định dạng.");
  } finally {
    await mock.close();
    resetEnv();
  }
});

// ---------------------------------------------------------------------------
// SUITE 5: Upstream Timeout & Abort Handling (504 vs 502)
// ---------------------------------------------------------------------------
test("5.1 Upstream connection refused returns 502", async () => {
  resetEnv();
  // Port 59999 is inactive
  process.env.TRUST_AGENT_API_URL = "http://127.0.0.1:59999";
  const req = new Request("http://localhost/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: "kiểm tra kết nối sập" }),
  });
  const res = await POST(req);
  assert.equal(res.status, 502);
  const data = await res.json();
  assert.equal(data.detail, "Chưa kết nối được với Trust Agent API. Hãy kiểm tra backend và thử lại.");
});

test("5.2 Client request abort returns 504 Timeout/Abort", async () => {
  const mock = await createMockServer((req, res) => {
    // Deliberately hold request open
    setTimeout(() => {
      res.writeHead(200);
      res.end("{}");
    }, 5000);
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const controller = new AbortController();
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "kiểm tra client abort" }),
      signal: controller.signal,
    });

    // Abort after 50ms
    setTimeout(() => controller.abort(), 50);

    const res = await POST(req);
    assert.equal(res.status, 504);
    const data = await res.json();
    assert.equal(
      data.detail,
      "Yêu cầu tra cứu quá thời gian phản hồi từ Trust Agent API (timeout 90s). Vui lòng thử lại sau.",
    );
  } finally {
    await mock.close();
    resetEnv();
  }
});

test("5.3 Upstream socket destroyed mid-request returns 502", async () => {
  const mock = await createMockServer((req, res) => {
    // Forcefully destroy client socket
    req.socket.destroy();
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "kiểm tra socket crash" }),
    });
    const res = await POST(req);
    assert.equal(res.status, 502);
    const data = await res.json();
    assert.equal(data.detail, "Chưa kết nối được với Trust Agent API. Hãy kiểm tra backend và thử lại.");
  } finally {
    await mock.close();
    resetEnv();
  }
});

// ---------------------------------------------------------------------------
// SUITE 6: End-to-end Success & Payload Integrity
// ---------------------------------------------------------------------------
test("6.1 Successful query forwards exact payload and returns 200", async () => {
  let receivedBody = null;
  const mock = await createMockServer((req, res) => {
    let buf = "";
    req.on("data", (chunk) => (buf += chunk));
    req.on("end", () => {
      receivedBody = JSON.parse(buf);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          query: receivedBody.query,
          answer: "Theo quy định tại Điều 105 Bộ luật Lao động 2019...",
          status: "verified",
          citations: [
            {
              title: "Bộ luật Lao động 2019",
              url: "https://thuvienphapluat.vn",
              article: "Điều 105",
            },
          ],
          thread_id: receivedBody.thread_id,
        }),
      );
    });
  });

  try {
    process.env.TRUST_AGENT_API_URL = mock.url;
    const req = new Request("http://localhost/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "Thời giờ làm việc bình thường là bao nhiêu?",
        thread_id: "session-legal-001",
      }),
    });
    const res = await POST(req);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.status, "verified");
    assert.equal(data.citations.length, 1);
    assert.equal(receivedBody.query, "Thời giờ làm việc bình thường là bao nhiêu?");
    assert.equal(receivedBody.k, 5);
    assert.equal(receivedBody.thread_id, "session-legal-001");
  } finally {
    await mock.close();
    resetEnv();
  }
});
