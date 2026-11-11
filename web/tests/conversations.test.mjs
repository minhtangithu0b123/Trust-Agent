// Comprehensive Next.js API Route Proxy Test Suite for Conversations
// Target:
//   - web/src/app/api/conversations/route.ts (GET list, POST create)
//   - web/src/app/api/conversations/[id]/route.ts (PATCH rename, DELETE)
//   - web/src/app/api/conversations/[id]/messages/route.ts (GET message history)

import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { register } from "node:module";
import { pathToFileURL } from "node:url";

// Register custom loader for .ts resolution and next/server alias
try {
  register("./web/tests/loader.mjs", pathToFileURL("./"));
} catch {
  // Already registered or passed via --loader
}

// ---------------------------------------------------------------------------
// IN-MEMORY MOCK HTTP SERVER HARNESS (Zero TCP socket restrictions)
// ---------------------------------------------------------------------------
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
  const port = 52000 + (mockCounter++);
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

// Environment Management
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
// DYNAMIC ROUTE IMPORTS (Inspects implementation presence)
// ---------------------------------------------------------------------------
const listRoutePath = path.resolve("web/src/app/api/conversations/route.ts");
const idRoutePath = path.resolve("web/src/app/api/conversations/[id]/route.ts");
const messagesRoutePath = path.resolve("web/src/app/api/conversations/[id]/messages/route.ts");

const routesExist =
  fs.existsSync(listRoutePath) &&
  fs.existsSync(idRoutePath) &&
  fs.existsSync(messagesRoutePath);

let listRoute = null;
let idRoute = null;
let messagesRoute = null;

if (routesExist) {
  try {
    listRoute = await import("../src/app/api/conversations/route.ts");
    idRoute = await import("../src/app/api/conversations/[id]/route.ts");
    messagesRoute = await import("../src/app/api/conversations/[id]/messages/route.ts");
  } catch (err) {
    console.error("Warning: Failed to import conversation route modules:", err.message);
  }
}

const skipReason = routesExist && listRoute && idRoute && messagesRoute
  ? false
  : "Pending implementation: Route files under web/src/app/api/conversations/ not yet created by M3 swe implementer";

// ===========================================================================
// SUITE 1: GET /api/conversations (Session List Proxy)
// ===========================================================================

test("1.1 GET /api/conversations: proxies to upstream and returns JSON session list", { skip: skipReason }, async () => {
  resetEnv();
  const mockSessions = [
    { id: "s1", title: "Hội thoại 1", created_at: "2026-11-11T01:00:00Z", updated_at: "2026-11-11T01:00:00Z", message_count: 2 },
    { id: "s2", title: "Hội thoại 2", created_at: "2026-11-11T02:00:00Z", updated_at: "2026-11-11T02:00:00Z", message_count: 5 },
  ];

  let capturedPath = null;
  const server = await createMockServer((req, res) => {
    capturedPath = req.url;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(mockSessions));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations", { method: "GET" });
    const res = await listRoute.GET(req);

    assert.equal(res.status, 200);
    const data = await res.json();
    assert.deepEqual(data, mockSessions);
    assert(capturedPath.includes("/conversations"), `Expected /conversations in upstream path, got: ${capturedPath}`);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("1.2 GET /api/conversations: injects X-API-Key when API_ACCESS_TOKEN is configured", { skip: skipReason }, async () => {
  resetEnv();
  let capturedHeaders = null;
  const server = await createMockServer((req, res) => {
    capturedHeaders = req.headers;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  });

  process.env.TRUST_AGENT_API_URL = server.url;
  process.env.API_ACCESS_TOKEN = "super-secret-token-123";

  try {
    const req = new Request("http://localhost/api/conversations", { method: "GET" });
    const res = await listRoute.GET(req);

    assert.equal(res.status, 200);
    assert.equal(capturedHeaders["x-api-key"], "super-secret-token-123");
  } finally {
    await server.close();
    resetEnv();
  }
});

test("1.3 GET /api/conversations: omits X-API-Key when API_ACCESS_TOKEN is not configured", { skip: skipReason }, async () => {
  resetEnv();
  let capturedHeaders = null;
  const server = await createMockServer((req, res) => {
    capturedHeaders = req.headers;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  });

  process.env.TRUST_AGENT_API_URL = server.url;
  delete process.env.API_ACCESS_TOKEN;

  try {
    const req = new Request("http://localhost/api/conversations", { method: "GET" });
    const res = await listRoute.GET(req);

    assert.equal(res.status, 200);
    assert.equal(capturedHeaders["x-api-key"], undefined);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("1.4 GET /api/conversations: strips trailing slashes from TRUST_AGENT_API_URL", { skip: skipReason }, async () => {
  resetEnv();
  let capturedUrl = null;
  const server = await createMockServer((req, res) => {
    capturedUrl = req.url;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  });

  process.env.TRUST_AGENT_API_URL = `${server.url}///`;

  try {
    const req = new Request("http://localhost/api/conversations", { method: "GET" });
    const res = await listRoute.GET(req);

    assert.equal(res.status, 200);
    assert(!capturedUrl.startsWith("//"));
  } finally {
    await server.close();
    resetEnv();
  }
});

test("1.5 GET /api/conversations: normalizes upstream 502/503/504 errors", { skip: skipReason }, async () => {
  resetEnv();
  const server = await createMockServer((req, res) => {
    res.writeHead(503, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Service Unavailable" }));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations", { method: "GET" });
    const res = await listRoute.GET(req);

    assert.equal(res.status, 503);
    const data = await res.json();
    assert(data.detail, "Expected detail field in error response");
  } finally {
    await server.close();
    resetEnv();
  }
});

test("1.6 GET /api/conversations: handles upstream connection failure with 502", { skip: skipReason }, async () => {
  resetEnv();
  // Port where nothing is listening
  process.env.TRUST_AGENT_API_URL = "http://127.0.0.1:59998";

  const req = new Request("http://localhost/api/conversations", { method: "GET" });
  const res = await listRoute.GET(req);

  assert.equal(res.status, 502);
  const data = await res.json();
  assert(data.detail, "Expected friendly error message on connection error");
});

// ===========================================================================
// SUITE 2: POST /api/conversations (Session Creation Proxy)
// ===========================================================================

test("2.1 POST /api/conversations: proxies creation payload { title } and returns 201/200", { skip: skipReason }, async () => {
  resetEnv();
  let receivedBody = null;
  const createdRecord = {
    id: "conv-created-1",
    title: "Tư vấn thuế doanh nghiệp",
    created_at: "2026-11-11T03:00:00Z",
    updated_at: "2026-11-11T03:00:00Z",
    message_count: 0,
  };

  const server = await createMockServer((req, res) => {
    let bodyStr = "";
    req.on("data", (chunk) => { bodyStr += chunk; });
    req.on("end", () => {
      receivedBody = JSON.parse(bodyStr);
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(JSON.stringify(createdRecord));
    });
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Tư vấn thuế doanh nghiệp" }),
    });
    const res = await listRoute.POST(req);

    assert(res.status === 201 || res.status === 200, `Expected 201 or 200, got ${res.status}`);
    const data = await res.json();
    assert.deepEqual(data, createdRecord);
    assert.equal(receivedBody.title, "Tư vấn thuế doanh nghiệp");
  } finally {
    await server.close();
    resetEnv();
  }
});

test("2.2 POST /api/conversations: accepts optional/omitted title in payload", { skip: skipReason }, async () => {
  resetEnv();
  const createdRecord = {
    id: "conv-default",
    title: "Cuộc trò chuyện mới",
    created_at: "2026-11-11T03:00:00Z",
    updated_at: "2026-11-11T03:00:00Z",
    message_count: 0,
  };

  const server = await createMockServer((req, res) => {
    res.writeHead(201, { "Content-Type": "application/json" });
    res.end(JSON.stringify(createdRecord));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const res = await listRoute.POST(req);
    assert(res.status === 201 || res.status === 200);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("2.3 POST /api/conversations: rejects malformed JSON with 400 Bad Request", { skip: skipReason }, async () => {
  resetEnv();
  const req = new Request("http://localhost/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{ malformed json: ",
  });
  const res = await listRoute.POST(req);
  assert.equal(res.status, 400);
});

test("2.4 POST /api/conversations: rejects non-object request payload with 400 Bad Request", { skip: skipReason }, async () => {
  resetEnv();
  const invalidPayloads = ["raw string", 12345, true, null];
  for (const p of invalidPayloads) {
    const req = new Request("http://localhost/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    });
    const res = await listRoute.POST(req);
    assert.equal(res.status, 400, `Payload ${JSON.stringify(p)} must return 400`);
  }
});

test("2.5 POST /api/conversations: injects X-API-Key header to upstream", { skip: skipReason }, async () => {
  resetEnv();
  let capturedHeaders = null;
  const server = await createMockServer((req, res) => {
    capturedHeaders = req.headers;
    res.writeHead(201, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ id: "1", title: "New" }));
  });

  process.env.TRUST_AGENT_API_URL = server.url;
  process.env.API_ACCESS_TOKEN = "post-secret-key";

  try {
    const req = new Request("http://localhost/api/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New" }),
    });
    const res = await listRoute.POST(req);
    assert(res.status === 201 || res.status === 200);
    assert.equal(capturedHeaders["x-api-key"], "post-secret-key");
  } finally {
    await server.close();
    resetEnv();
  }
});

// ===========================================================================
// SUITE 3: GET /api/conversations/[id]/messages (History Query Proxy)
// ===========================================================================

test("3.1 GET /api/conversations/[id]/messages: proxies history query with Promise params", { skip: skipReason }, async () => {
  resetEnv();
  const mockMessages = [
    { id: 1, role: "user", content: "Nghỉ phép năm bao nhiêu ngày?" },
    { id: 2, role: "assistant", content: "Theo Điều 113 BLLĐ 2019..." },
  ];

  let capturedPath = null;
  const server = await createMockServer((req, res) => {
    capturedPath = req.url;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(mockMessages));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-123/messages", { method: "GET" });
    const res = await messagesRoute.GET(req, { params: Promise.resolve({ id: "conv-123" }) });

    assert.equal(res.status, 200);
    const data = await res.json();
    assert.deepEqual(data, mockMessages);
    assert(capturedPath.includes("conv-123/messages"), `Expected conv-123/messages in path, got: ${capturedPath}`);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("3.2 GET /api/conversations/[id]/messages: supports sync object params fallback", { skip: skipReason }, async () => {
  resetEnv();
  const server = await createMockServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-sync/messages", { method: "GET" });
    const res = await messagesRoute.GET(req, { params: { id: "conv-sync" } });
    assert.equal(res.status, 200);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("3.3 GET /api/conversations/[id]/messages: normalizes upstream 404 (not found)", { skip: skipReason }, async () => {
  resetEnv();
  const server = await createMockServer((req, res) => {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Conversation not found" }));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/non-existent/messages", { method: "GET" });
    const res = await messagesRoute.GET(req, { params: Promise.resolve({ id: "non-existent" }) });

    assert.equal(res.status, 404);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("3.4 GET /api/conversations/[id]/messages: injects X-API-Key header", { skip: skipReason }, async () => {
  resetEnv();
  let capturedHeaders = null;
  const server = await createMockServer((req, res) => {
    capturedHeaders = req.headers;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify([]));
  });

  process.env.TRUST_AGENT_API_URL = server.url;
  process.env.API_ACCESS_TOKEN = "msg-history-token";

  try {
    const req = new Request("http://localhost/api/conversations/conv-1/messages", { method: "GET" });
    const res = await messagesRoute.GET(req, { params: Promise.resolve({ id: "conv-1" }) });

    assert.equal(res.status, 200);
    assert.equal(capturedHeaders["x-api-key"], "msg-history-token");
  } finally {
    await server.close();
    resetEnv();
  }
});

// ===========================================================================
// SUITE 4: PATCH /api/conversations/[id] (Rename Proxy)
// ===========================================================================

test("4.1 PATCH /api/conversations/[id]: proxies rename payload and returns 200", { skip: skipReason }, async () => {
  resetEnv();
  let receivedBody = null;
  let receivedMethod = null;
  const updatedRecord = {
    id: "conv-rename-1",
    title: "Tiêu đề mới cập nhật",
    created_at: "2026-11-11T01:00:00Z",
    updated_at: "2026-11-11T04:00:00Z",
  };

  const server = await createMockServer((req, res) => {
    receivedMethod = req.method;
    let bodyStr = "";
    req.on("data", (chunk) => { bodyStr += chunk; });
    req.on("end", () => {
      receivedBody = JSON.parse(bodyStr);
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(updatedRecord));
    });
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-rename-1", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Tiêu đề mới cập nhật" }),
    });
    const res = await idRoute.PATCH(req, { params: Promise.resolve({ id: "conv-rename-1" }) });

    assert.equal(res.status, 200);
    assert.equal(receivedMethod, "PATCH");
    assert.equal(receivedBody.title, "Tiêu đề mới cập nhật");
    const data = await res.json();
    assert.deepEqual(data, updatedRecord);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("4.2 PATCH /api/conversations/[id]: rejects empty title or whitespace-only with 400", { skip: skipReason }, async () => {
  resetEnv();
  const invalidTitles = ["", "   ", "\t\n  "];
  for (const t of invalidTitles) {
    const req = new Request("http://localhost/api/conversations/conv-1", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: t }),
    });
    const res = await idRoute.PATCH(req, { params: Promise.resolve({ id: "conv-1" }) });
    assert.equal(res.status, 400, `Empty title '${t}' must return 400`);
  }
});

test("4.3 PATCH /api/conversations/[id]: rejects missing title field with 400", { skip: skipReason }, async () => {
  resetEnv();
  const req = new Request("http://localhost/api/conversations/conv-1", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ other_field: "foo" }),
  });
  const res = await idRoute.PATCH(req, { params: Promise.resolve({ id: "conv-1" }) });
  assert.equal(res.status, 400);
});

test("4.4 PATCH /api/conversations/[id]: normalizes upstream 404 (session not found)", { skip: skipReason }, async () => {
  resetEnv();
  const server = await createMockServer((req, res) => {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Conversation not found" }));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-not-found", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Valid Title" }),
    });
    const res = await idRoute.PATCH(req, { params: Promise.resolve({ id: "conv-not-found" }) });
    assert.equal(res.status, 404);
  } finally {
    await server.close();
    resetEnv();
  }
});

// ===========================================================================
// SUITE 5: DELETE /api/conversations/[id] (Deletion Proxy)
// ===========================================================================

test("5.1 DELETE /api/conversations/[id]: proxies deletion and returns 204 or 200", { skip: skipReason }, async () => {
  resetEnv();
  let capturedMethod = null;
  let capturedPath = null;

  const server = await createMockServer((req, res) => {
    capturedMethod = req.method;
    capturedPath = req.url;
    res.writeHead(204);
    res.end();
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-del-1", { method: "DELETE" });
    const res = await idRoute.DELETE(req, { params: Promise.resolve({ id: "conv-del-1" }) });

    assert(res.status === 204 || res.status === 200, `Expected 204 or 200, got ${res.status}`);
    assert.equal(capturedMethod, "DELETE");
    assert(capturedPath.includes("conv-del-1"));
  } finally {
    await server.close();
    resetEnv();
  }
});

test("5.2 DELETE /api/conversations/[id]: injects X-API-Key header to upstream", { skip: skipReason }, async () => {
  resetEnv();
  let capturedHeaders = null;
  const server = await createMockServer((req, res) => {
    capturedHeaders = req.headers;
    res.writeHead(204);
    res.end();
  });

  process.env.TRUST_AGENT_API_URL = server.url;
  process.env.API_ACCESS_TOKEN = "del-auth-token";

  try {
    const req = new Request("http://localhost/api/conversations/conv-del-2", { method: "DELETE" });
    const res = await idRoute.DELETE(req, { params: Promise.resolve({ id: "conv-del-2" }) });

    assert(res.status === 204 || res.status === 200);
    assert.equal(capturedHeaders["x-api-key"], "del-auth-token");
  } finally {
    await server.close();
    resetEnv();
  }
});

test("5.3 DELETE /api/conversations/[id]: normalizes upstream 404 (session not found)", { skip: skipReason }, async () => {
  resetEnv();
  const server = await createMockServer((req, res) => {
    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ detail: "Conversation not found" }));
  });

  process.env.TRUST_AGENT_API_URL = server.url;

  try {
    const req = new Request("http://localhost/api/conversations/conv-del-404", { method: "DELETE" });
    const res = await idRoute.DELETE(req, { params: Promise.resolve({ id: "conv-del-404" }) });
    assert.equal(res.status, 404);
  } finally {
    await server.close();
    resetEnv();
  }
});

test("5.4 DELETE /api/conversations/[id]: handles upstream 502/down gracefully", { skip: skipReason }, async () => {
  resetEnv();
  process.env.TRUST_AGENT_API_URL = "http://127.0.0.1:59997";

  const req = new Request("http://localhost/api/conversations/conv-del-down", { method: "DELETE" });
  const res = await idRoute.DELETE(req, { params: Promise.resolve({ id: "conv-del-down" }) });
  assert.equal(res.status, 502);
});
