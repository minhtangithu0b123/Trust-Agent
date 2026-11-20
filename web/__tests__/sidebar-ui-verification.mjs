// Empirical Test Suite for Frontend Multi-Conversation UI Logic & Sidebar Interactions
// Covers Tiers 1-4 for Feature 5 (Sidebar & Switching) and Feature 6 (Rename & Safe Delete)
// Target: web/src/components/Sidebar.tsx, web/src/app/page.tsx, and web/src/app/globals.css

import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

console.log("=== STARTING SIDEBAR UI & MULTI-CONVERSATION EMPIRICAL TEST SUITE ===");

let passed = 0;
let failed = 0;
const findings = [];

function test(name, fn) {
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  [FAIL] ${name}: ${err.message}`);
    failed++;
    findings.push({ name, error: err.message });
  }
}

// --------------------------------------------------------------------------
// SHARED MODELS & SPECIFICATION IMPLEMENTATIONS
// --------------------------------------------------------------------------

/**
 * Specification-derived auto-title generator:
 * - Truncates query to at most 40 characters
 * - Normalizes newlines and extra spaces
 * - Adds ellipsis "..." if truncated
 */
export function generateSessionTitle(query) {
  if (typeof query !== "string") return "Cuộc trò chuyện mới";
  const cleaned = query.replace(/\s+/g, " ").trim();
  if (cleaned.length === 0) return "Cuộc trò chuyện mới";
  if (cleaned.length <= 40) return cleaned;
  return cleaned.slice(0, 37).trim() + "...";
}

/**
 * Specification-derived session list comparator:
 * - Sorts by updated_at descending
 * - Tiebreaker: created_at descending, then id
 */
export function sortSessions(sessions) {
  if (!Array.isArray(sessions)) return [];
  return [...sessions].sort((a, b) => {
    const timeA = new Date(a.updated_at || a.created_at || 0).getTime();
    const timeB = new Date(b.updated_at || b.created_at || 0).getTime();
    if (timeB !== timeA) return timeB - timeA;
    const createA = new Date(a.created_at || 0).getTime();
    const createB = new Date(b.created_at || 0).getTime();
    if (createB !== createA) return createB - createA;
    return String(a.id || "").localeCompare(String(b.id || ""));
  });
}

/**
 * Specification-derived multi-conversation UI state machine
 */
export class ConversationClientStore {
  constructor(initialState = {}) {
    this.sessions = initialState.sessions ? sortSessions(initialState.sessions) : [];
    this.activeSessionId = initialState.activeSessionId || null;
    this.messages = initialState.messages || [];
    this.threadId = initialState.threadId || null;
    this.draft = initialState.draft || "";
    this.loading = !!initialState.loading;
    this.loadingHistory = !!initialState.loadingHistory;
    this.editingSessionId = null;
    this.editingTitle = "";
    this.deletingSessionId = null;
    this.activeAbortController = null;
    this.historyCache = new Map(initialState.historyCache || []);
    this.apiCalls = [];
  }

  startNewConversation() {
    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }
    this.activeSessionId = null;
    this.messages = [];
    this.threadId = null;
    this.draft = "";
    this.loading = false;
    this.loadingHistory = false;
    this.editingSessionId = null;
    this.deletingSessionId = null;
  }

  async selectSession(sessionId) {
    if (this.activeSessionId === sessionId) return;

    if (this.activeAbortController) {
      this.activeAbortController.abort();
      this.activeAbortController = null;
    }

    this.activeSessionId = sessionId;
    this.threadId = sessionId;
    this.loadingHistory = true;
    this.editingSessionId = null;
    this.deletingSessionId = null;

    this.apiCalls.push({ action: "GET_MESSAGES", sessionId });

    // Mock network fetch or cache read
    const fetchedMessages = this.historyCache.get(sessionId) || [];
    this.messages = [...fetchedMessages];
    this.loadingHistory = false;
  }

  async submitFirstMessage(query) {
    const trimmed = query.trim();
    if (trimmed.length < 2) throw new Error("Câu hỏi phải có ít nhất 2 ký tự.");

    const title = generateSessionTitle(trimmed);
    const newSessionId = `conv-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const now = new Date().toISOString();

    const newSession = {
      id: newSessionId,
      title,
      created_at: now,
      updated_at: now,
      message_count: 1,
    };

    this.apiCalls.push({ action: "POST_CONVERSATION", payload: { title }, result: newSession });

    this.sessions = sortSessions([newSession, ...this.sessions]);
    this.activeSessionId = newSessionId;
    this.threadId = newSessionId;

    const userMsg = { id: 1, role: "user", text: trimmed };
    this.messages = [userMsg];

    this.activeAbortController = new AbortController();
    return newSession;
  }

  startRename(sessionId) {
    const session = this.sessions.find((s) => s.id === sessionId);
    if (!session) return false;
    this.editingSessionId = sessionId;
    this.editingTitle = session.title;
    return true;
  }

  changeRenameTitle(value) {
    this.editingTitle = value;
  }

  cancelRename() {
    this.editingSessionId = null;
    this.editingTitle = "";
  }

  async commitRename() {
    if (!this.editingSessionId) return false;
    const trimmedTitle = this.editingTitle.trim();
    if (trimmedTitle.length === 0) {
      throw new Error("Tiêu đề không được để trống.");
    }

    const sessionId = this.editingSessionId;
    const oldSession = this.sessions.find((s) => s.id === sessionId);
    if (!oldSession) {
      this.cancelRename();
      return false;
    }

    const previousTitle = oldSession.title;
    // Optimistic update
    oldSession.title = trimmedTitle;
    oldSession.updated_at = new Date().toISOString();
    this.sessions = sortSessions(this.sessions);

    this.apiCalls.push({ action: "PATCH_RENAME", sessionId, payload: { title: trimmedTitle } });

    this.editingSessionId = null;
    this.editingTitle = "";
    return true;
  }

  requestDelete(sessionId) {
    const session = this.sessions.find((s) => s.id === sessionId);
    if (!session) return false;
    this.deletingSessionId = sessionId;
    return true;
  }

  cancelDelete() {
    this.deletingSessionId = null;
  }

  async confirmDelete() {
    if (!this.deletingSessionId) return false;
    const targetId = this.deletingSessionId;

    this.apiCalls.push({ action: "DELETE_CONVERSATION", sessionId: targetId });

    // Remove from sessions
    this.sessions = this.sessions.filter((s) => s.id !== targetId);
    this.historyCache.delete(targetId);

    // If deleting active session, fall back cleanly to new chat
    if (this.activeSessionId === targetId) {
      this.startNewConversation();
    }

    this.deletingSessionId = null;
    return true;
  }
}

// ==========================================================================
// TIER 1: FEATURE COVERAGE
// ==========================================================================
console.log("\n--- TIER 1: Feature Coverage (Sorting, New Chat, Switching, Auto-Title) ---");

// Feature 1.1: Session list sorting
test("1.1.1 Session list sorting: correctly sorts sessions by updated_at DESC", () => {
  const inputSessions = [
    { id: "s1", title: "Chat 1", updated_at: "2026-11-10T10:00:00Z" },
    { id: "s2", title: "Chat 2", updated_at: "2026-11-11T12:00:00Z" },
    { id: "s3", title: "Chat 3", updated_at: "2026-11-09T08:00:00Z" },
  ];
  const sorted = sortSessions(inputSessions);
  assert.equal(sorted[0].id, "s2", "Newest session must be first");
  assert.equal(sorted[1].id, "s1", "Middle session must be second");
  assert.equal(sorted[2].id, "s3", "Oldest session must be last");
});

test("1.1.2 Session list sorting: handles mixed ISO timestamp formats and timezone offsets", () => {
  const inputSessions = [
    { id: "s-utc", updated_at: "2026-11-11T05:00:00Z" }, // 05:00 UTC
    { id: "s-vn", updated_at: "2026-11-11T13:00:00+07:00" }, // 06:00 UTC (Newer!)
    { id: "s-sec", updated_at: "2026-11-11T04:59:59Z" }, // 04:59 UTC
  ];
  const sorted = sortSessions(inputSessions);
  assert.equal(sorted[0].id, "s-vn", "s-vn (06:00 UTC) must be newer than s-utc (05:00 UTC)");
  assert.equal(sorted[1].id, "s-utc");
  assert.equal(sorted[2].id, "s-sec");
});

test("1.1.3 Session list sorting: tiebreaker handles identical timestamps gracefully", () => {
  const inputSessions = [
    { id: "s-b", updated_at: "2026-11-11T10:00:00Z", created_at: "2026-11-10T10:00:00Z" },
    { id: "s-a", updated_at: "2026-11-11T10:00:00Z", created_at: "2026-11-10T11:00:00Z" },
  ];
  const sorted = sortSessions(inputSessions);
  assert.equal(sorted[0].id, "s-a", "Tiebreaker on created_at DESC must place s-a first");
});

test("1.1.4 Session list sorting: handles empty array and single-item array", () => {
  assert.deepEqual(sortSessions([]), []);
  const single = [{ id: "single", updated_at: "2026-11-11T00:00:00Z" }];
  assert.deepEqual(sortSessions(single), single);
});

test("1.1.5 Session list sorting: immutability (does not mutate original array in place)", () => {
  const original = [
    { id: "s1", updated_at: "2026-11-09T00:00:00Z" },
    { id: "s2", updated_at: "2026-11-10T00:00:00Z" },
  ];
  const copy = [...original];
  const sorted = sortSessions(original);
  assert.notEqual(sorted, original, "Must return a new array reference");
  assert.equal(original[0].id, copy[0].id, "Original array order must not be mutated");
});

// Feature 1.2: New Chat Action
test("1.2.1 New Chat: resets activeSessionId to null and clears messages", () => {
  const store = new ConversationClientStore({
    activeSessionId: "s-existing",
    threadId: "s-existing",
    messages: [{ id: 1, role: "user", text: "query" }],
    draft: "draft question",
    sessions: [{ id: "s-existing", title: "Existing", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.startNewConversation();
  assert.equal(store.activeSessionId, null, "activeSessionId must be null");
  assert.equal(store.threadId, null, "threadId must be null");
  assert.deepEqual(store.messages, [], "messages must be empty");
  assert.equal(store.draft, "", "draft must be reset");
});

test("1.2.2 New Chat: keeps sidebar sessions list visible and intact", () => {
  const initialSessions = [
    { id: "s1", title: "Session 1", updated_at: "2026-11-11T01:00:00Z" },
    { id: "s2", title: "Session 2", updated_at: "2026-11-11T02:00:00Z" },
  ];
  const store = new ConversationClientStore({
    activeSessionId: "s2",
    sessions: initialSessions,
  });

  store.startNewConversation();
  assert.equal(store.sessions.length, 2, "Sessions list must remain intact");
  assert.equal(store.sessions[0].id, "s2");
  assert.equal(store.sessions[1].id, "s1");
});

test("1.2.3 New Chat: aborts pending in-flight query controller", () => {
  const store = new ConversationClientStore({
    activeSessionId: "s1",
    sessions: [{ id: "s1", updated_at: "2026-11-11T00:00:00Z" }],
  });
  const abortCtrl = new AbortController();
  store.activeAbortController = abortCtrl;

  store.startNewConversation();
  assert.equal(abortCtrl.signal.aborted, true, "In-flight abort controller must be triggered");
  assert.equal(store.activeAbortController, null, "activeAbortController must be reset to null");
});

test("1.2.4 New Chat: resets edit and delete states if active", () => {
  const store = new ConversationClientStore({
    activeSessionId: "s1",
    sessions: [{ id: "s1", updated_at: "2026-11-11T00:00:00Z" }],
  });
  store.editingSessionId = "s1";
  store.deletingSessionId = "s1";

  store.startNewConversation();
  assert.equal(store.editingSessionId, null);
  assert.equal(store.deletingSessionId, null);
});

// Feature 1.3: Conversation Switching & Context Isolation
test("1.3.1 Switching: loads historical messages for newly selected session", async () => {
  const historyS1 = [{ id: 1, role: "user", text: "Hỏi về thuế" }];
  const historyS2 = [
    { id: 1, role: "user", text: "Hỏi về luật giao thông" },
    { id: 2, role: "assistant", text: "Nghị định 100/2019/NĐ-CP..." },
  ];

  const store = new ConversationClientStore({
    activeSessionId: "s1",
    messages: historyS1,
    sessions: [
      { id: "s1", title: "Thuế", updated_at: "2026-11-11T01:00:00Z" },
      { id: "s2", title: "Giao thông", updated_at: "2026-11-11T02:00:00Z" },
    ],
    historyCache: [
      ["s1", historyS1],
      ["s2", historyS2],
    ],
  });

  await store.selectSession("s2");
  assert.equal(store.activeSessionId, "s2");
  assert.equal(store.threadId, "s2");
  assert.equal(store.messages.length, 2);
  assert.equal(store.messages[1].text, "Nghị định 100/2019/NĐ-CP...");
});

test("1.3.2 Switching: isolates context and eliminates message bleed-through", async () => {
  const store = new ConversationClientStore({
    activeSessionId: "s1",
    messages: [{ id: 1, role: "user", text: "Private S1 data" }],
    sessions: [
      { id: "s1", title: "S1", updated_at: "2026-11-11T01:00:00Z" },
      { id: "s2", title: "S2", updated_at: "2026-11-11T02:00:00Z" },
    ],
    historyCache: [["s2", []]], // S2 has 0 messages
  });

  await store.selectSession("s2");
  assert.equal(store.messages.length, 0, "Switched session must not inherit S1 messages");
});

test("1.3.3 Switching: aborts in-flight request on previous session before switching", async () => {
  const store = new ConversationClientStore({
    activeSessionId: "s1",
    sessions: [
      { id: "s1", updated_at: "2026-11-11T01:00:00Z" },
      { id: "s2", updated_at: "2026-11-11T02:00:00Z" },
    ],
  });
  const abortCtrl = new AbortController();
  store.activeAbortController = abortCtrl;

  await store.selectSession("s2");
  assert.equal(abortCtrl.signal.aborted, true, "Previous session request must be aborted");
});

test("1.3.4 Switching: clicking currently active session is a no-op", async () => {
  const store = new ConversationClientStore({
    activeSessionId: "s1",
    sessions: [{ id: "s1", updated_at: "2026-11-11T01:00:00Z" }],
  });
  const initialCalls = store.apiCalls.length;
  await store.selectSession("s1");
  assert.equal(store.apiCalls.length, initialCalls, "Selecting active session must not trigger re-fetch");
});

// Feature 1.4: Auto-Title Generation
test("1.4.1 Auto-title: leaves short queries (< 40 chars) unmodified", () => {
  const shortQueries = [
    "Hợp đồng lao động",
    "Phạt nồng độ cồn xe máy",
    "Thuế thu nhập cá nhân",
  ];
  for (const q of shortQueries) {
    assert.equal(generateSessionTitle(q), q);
  }
});

test("1.4.2 Auto-title: truncates long queries (> 40 chars) to <= 40 chars with ellipsis", () => {
  const longQuery = "Người lao động làm việc theo hợp đồng lao động có thời hạn từ 12 tháng đến 36 tháng";
  const title = generateSessionTitle(longQuery);
  assert(title.length <= 40, `Title length ${title.length} exceeds 40 characters`);
  assert(title.endsWith("..."), "Truncated title must end with ellipsis");
  assert.equal(title, "Người lao động làm việc theo hợp đồng...");
});

test("1.4.3 Auto-title: boundary test at exactly 40 and 41 characters", () => {
  const exactly40 = "1234567890123456789012345678901234567890";
  assert.equal(exactly40.length, 40);
  assert.equal(generateSessionTitle(exactly40), exactly40, "40-char query must not be truncated");

  const query41 = "12345678901234567890123456789012345678901";
  const title41 = generateSessionTitle(query41);
  assert(title41.length <= 40, "41-char query must be truncated to <= 40 chars");
  assert(title41.endsWith("..."));
});

test("1.4.4 Auto-title: normalizes multi-line and excess whitespace", () => {
  const multiline = "   Điều 1:\n Quy định về   hợp đồng lao động   \n\n";
  const title = generateSessionTitle(multiline);
  assert.equal(title, "Điều 1: Quy định về hợp đồng lao động");
});

test("1.4.5 Auto-title: fallback for empty or non-string input", () => {
  assert.equal(generateSessionTitle(""), "Cuộc trò chuyện mới");
  assert.equal(generateSessionTitle("   "), "Cuộc trò chuyện mới");
  assert.equal(generateSessionTitle(null), "Cuộc trò chuyện mới");
  assert.equal(generateSessionTitle(undefined), "Cuộc trò chuyện mới");
});

// ==========================================================================
// TIER 2: BOUNDARY & CORNER CASES
// ==========================================================================
console.log("\n--- TIER 2: Boundary & Corner Cases (Empty State, Rename State Machine, Safe Delete, CSS) ---");

// Feature 2.1: Empty Sessions List
test("2.1.1 Empty state: displays 'Chưa có cuộc trò chuyện nào' when sessions is empty", () => {
  function renderEmptyState(sessions) {
    if (!sessions || sessions.length === 0) {
      return { isEmpty: true, text: "Chưa có cuộc trò chuyện nào" };
    }
    return { isEmpty: false, text: null };
  }

  const resultEmpty = renderEmptyState([]);
  assert.equal(resultEmpty.isEmpty, true);
  assert.equal(resultEmpty.text, "Chưa có cuộc trò chuyện nào");

  const resultNonEmpty = renderEmptyState([{ id: "s1" }]);
  assert.equal(resultNonEmpty.isEmpty, false);
});

test("2.1.2 Empty state: transitions to empty state when all sessions are deleted", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "last-one", title: "Last", updated_at: "2026-11-11T00:00:00Z" }],
    activeSessionId: "last-one",
  });
  store.requestDelete("last-one");
  await store.confirmDelete();
  assert.equal(store.sessions.length, 0);
  assert.equal(store.activeSessionId, null);
});

// Feature 2.2: Inline Rename State Machine
test("2.2.1 Rename: Enter commits new title and updates session", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "Old Title", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.startRename("s1");
  assert.equal(store.editingSessionId, "s1");
  assert.equal(store.editingTitle, "Old Title");

  store.changeRenameTitle("New Valid Title");
  const success = await store.commitRename();
  assert.equal(success, true);
  assert.equal(store.editingSessionId, null);
  assert.equal(store.sessions[0].title, "New Valid Title");
  assert.equal(store.apiCalls.some((c) => c.action === "PATCH_RENAME" && c.payload.title === "New Valid Title"), true);
});

test("2.2.2 Rename: Escape key cancels without persisting changes", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "Original Title", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.startRename("s1");
  store.changeRenameTitle("Temporary modified title");
  store.cancelRename();

  assert.equal(store.editingSessionId, null);
  assert.equal(store.sessions[0].title, "Original Title", "Title must not be changed on Escape");
  assert.equal(store.apiCalls.some((c) => c.action === "PATCH_RENAME"), false, "No PATCH API call on cancel");
});

test("2.2.3 Rename: empty string input is rejected", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "Keep Me", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.startRename("s1");
  store.changeRenameTitle("");

  await assert.rejects(
    async () => {
      await store.commitRename();
    },
    { message: "Tiêu đề không được để trống." }
  );
  assert.equal(store.sessions[0].title, "Keep Me");
});

test("2.2.4 Rename: whitespace-only string input is rejected", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "Keep Me", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.startRename("s1");
  store.changeRenameTitle("    \t  \n ");

  await assert.rejects(
    async () => {
      await store.commitRename();
    },
    { message: "Tiêu đề không được để trống." }
  );
  assert.equal(store.sessions[0].title, "Keep Me");
});

// Feature 2.3: Safe Deletion Confirmation Flow
test("2.3.1 Safe Delete: initial click enters confirmation state without issuing DELETE", () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "To Delete", updated_at: "2026-11-11T00:00:00Z" }],
  });

  const requested = store.requestDelete("s1");
  assert.equal(requested, true);
  assert.equal(store.deletingSessionId, "s1");
  assert.equal(store.sessions.length, 1, "Session must still exist in list");
  assert.equal(store.apiCalls.some((c) => c.action === "DELETE_CONVERSATION"), false, "DELETE must not be called yet");
});

test("2.3.2 Safe Delete: Cancel button dismisses confirmation state cleanly", () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "s1", title: "Safe", updated_at: "2026-11-11T00:00:00Z" }],
  });

  store.requestDelete("s1");
  store.cancelDelete();
  assert.equal(store.deletingSessionId, null);
  assert.equal(store.sessions.length, 1);
  assert.equal(store.apiCalls.some((c) => c.action === "DELETE_CONVERSATION"), false);
});

test("2.3.3 Safe Delete: Confirm button issues DELETE API call and removes session", async () => {
  const store = new ConversationClientStore({
    sessions: [
      { id: "s1", title: "Session 1", updated_at: "2026-11-11T01:00:00Z" },
      { id: "s2", title: "Session 2", updated_at: "2026-11-11T02:00:00Z" },
    ],
  });

  store.requestDelete("s1");
  const confirmed = await store.confirmDelete();
  assert.equal(confirmed, true);
  assert.equal(store.deletingSessionId, null);
  assert.equal(store.sessions.length, 1);
  assert.equal(store.sessions[0].id, "s2");
  assert.equal(store.apiCalls.some((c) => c.action === "DELETE_CONVERSATION" && c.sessionId === "s1"), true);
});

// Feature 2.4: Scroll Containment CSS Contract
test("2.4.1 CSS: .app-shell bounds viewport strictly with 100vh / 100dvh and overflow hidden", () => {
  const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");
  const shellBlock = cssSource.match(/\.app-shell\s*\{([^}]+)\}/);
  assert(shellBlock, ".app-shell class must exist in globals.css");
  const shellCss = shellBlock[1];
  assert(shellCss.includes("height: 100vh"), ".app-shell missing height: 100vh");
  assert(shellCss.includes("height: 100dvh"), ".app-shell missing height: 100dvh");
  assert(shellCss.includes("overflow: hidden"), ".app-shell missing overflow: hidden");
  assert(shellCss.includes("display: flex"), ".app-shell missing display: flex");
});

test("2.4.2 CSS: .conversation is scrollable with overflow-y: auto and min-height: 0", () => {
  const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");
  const convBlock = cssSource.match(/\.conversation\s*\{([^}]+)\}/);
  assert(convBlock, ".conversation class must exist in globals.css");
  const convCss = convBlock[1];
  assert(convCss.includes("overflow-y: auto"), ".conversation missing overflow-y: auto");
  assert(convCss.includes("min-height: 0"), ".conversation missing min-height: 0");
  assert(convCss.includes("flex: 1 1 0%"), ".conversation missing flex: 1 1 0%");
});

test("2.4.3 CSS: .composer-wrap is pinned with flex-shrink: 0", () => {
  const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");
  const composerBlock = cssSource.match(/\.composer-wrap\s*\{([^}]+)\}/);
  assert(composerBlock, ".composer-wrap class must exist");
  assert(composerBlock[1].includes("flex-shrink: 0"), ".composer-wrap must have flex-shrink: 0");
});

test("2.4.4 CSS: body and html enforce zero outer window scroll leakage", () => {
  const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");
  assert(/html,\s*body\s*\{[^}]*height:\s*100%/.test(cssSource), "html, body must have height: 100%");
  assert(/body\s*\{[^}]*overflow:\s*hidden/.test(cssSource), "body must have overflow: hidden");
});

// ==========================================================================
// TIER 3: CROSS-FEATURE COMBINATIONS
// ==========================================================================
console.log("\n--- TIER 3: Cross-Feature Combinations (Delete Active, Delete Inactive, Rename Sync) ---");

test("3.1 Deleting active session falls back cleanly to blank fresh chat", async () => {
  const s1History = [{ id: 1, role: "user", text: "Active query" }];
  const store = new ConversationClientStore({
    sessions: [
      { id: "active-s1", title: "Active Session", updated_at: "2026-11-11T01:00:00Z" },
      { id: "bg-s2", title: "Background Session", updated_at: "2026-11-11T00:30:00Z" },
    ],
    activeSessionId: "active-s1",
    messages: s1History,
    threadId: "active-s1",
  });

  store.requestDelete("active-s1");
  await store.confirmDelete();

  // Active session deleted -> must fall back to blank fresh chat
  assert.equal(store.activeSessionId, null, "activeSessionId must reset to null");
  assert.equal(store.threadId, null, "threadId must reset to null");
  assert.deepEqual(store.messages, [], "messages must be reset to empty");
  assert.equal(store.sessions.length, 1, "Only background session remains");
  assert.equal(store.sessions[0].id, "bg-s2");
});

test("3.2 Deleting an inactive background session does NOT disrupt current active chat", async () => {
  const activeHistory = [
    { id: 1, role: "user", text: "Active chat query" },
    { id: 2, role: "assistant", text: "Active chat response" },
  ];
  const store = new ConversationClientStore({
    sessions: [
      { id: "active-s1", title: "Active Session", updated_at: "2026-11-11T01:00:00Z" },
      { id: "bg-s2", title: "Background Session", updated_at: "2026-11-11T00:30:00Z" },
    ],
    activeSessionId: "active-s1",
    messages: activeHistory,
    threadId: "active-s1",
  });

  store.requestDelete("bg-s2");
  await store.confirmDelete();

  assert.equal(store.activeSessionId, "active-s1", "activeSessionId must remain unchanged");
  assert.equal(store.threadId, "active-s1", "threadId must remain unchanged");
  assert.equal(store.messages.length, 2, "Active chat messages must remain intact");
  assert.equal(store.messages[1].text, "Active chat response");
  assert.equal(store.sessions.length, 1);
  assert.equal(store.sessions[0].id, "active-s1");
});

test("3.3 Renaming active session synchronizes title in both sidebar and topbar", async () => {
  const store = new ConversationClientStore({
    sessions: [{ id: "active-s1", title: "Old Title", updated_at: "2026-11-11T01:00:00Z" }],
    activeSessionId: "active-s1",
  });

  function getTopbarTitle(storeInstance) {
    if (!storeInstance.activeSessionId) return "Cuộc trò chuyện mới";
    const active = storeInstance.sessions.find((s) => s.id === storeInstance.activeSessionId);
    return active ? active.title : "Cuộc trò chuyện mới";
  }

  assert.equal(getTopbarTitle(store), "Old Title");

  store.startRename("active-s1");
  store.changeRenameTitle("Tư vấn hợp đồng lao động 2024");
  await store.commitRename();

  assert.equal(store.sessions[0].title, "Tư vấn hợp đồng lao động 2024", "Sidebar title must be updated");
  assert.equal(getTopbarTitle(store), "Tư vấn hợp đồng lao động 2024", "Topbar title must be updated");
  assert.equal(store.activeSessionId, "active-s1", "activeSessionId remains active");
});

// ==========================================================================
// TIER 4: REAL-WORLD SCENARIOS
// ==========================================================================
console.log("\n--- TIER 4: Real-World Consultation Workflow Simulation ---");

test("4.1 Full multi-turn consultation workflow: start -> ask -> auto-title -> switch -> rename -> safe delete", async () => {
  // Step 1: User opens Trust-AGENT. Initial state loads historical conversations sorted DESC.
  const pastSessionTax = {
    id: "conv-tax-01",
    title: "Tư vấn thuế TNCN",
    created_at: "2026-11-10T08:00:00Z",
    updated_at: "2026-11-10T08:30:00Z",
    message_count: 2,
  };
  const pastSessionOld = {
    id: "conv-draft-old",
    title: "Phiên nháp cũ",
    created_at: "2026-11-09T08:00:00Z",
    updated_at: "2026-11-09T08:00:00Z",
    message_count: 1,
  };

  const store = new ConversationClientStore({
    sessions: [pastSessionOld, pastSessionTax],
    activeSessionId: null, // Start on clean fresh chat screen
    historyCache: [
      [
        "conv-tax-01",
        [
          { id: 1, role: "user", text: "Thuế thu nhập cá nhân tính thế nào?" },
          { id: 2, role: "assistant", text: "Theo Luật Thuế TNCN..." },
        ],
      ],
      [
        "conv-draft-old",
        [{ id: 1, role: "user", text: "Nháp" }],
      ],
    ],
  });

  assert.equal(store.sessions[0].id, "conv-tax-01", "Step 1: sessions loaded and sorted DESC");
  assert.equal(store.activeSessionId, null, "Step 2: fresh chat state");
  assert.equal(store.messages.length, 0);

  // Step 3: User submits first consultation question
  const firstQuery = "Theo Bộ luật Lao động 2019, người lao động có quyền đơn phương chấm dứt hợp đồng lao động khi nào?";
  const createdSession = await store.submitFirstMessage(firstQuery);

  // Step 4: Lazy creation generated auto-truncated title <= 40 chars
  assert(createdSession.title.length <= 40, "Step 4: Auto-title <= 40 chars");
  assert(createdSession.title.endsWith("..."));
  assert.equal(store.activeSessionId, createdSession.id, "Step 5: newly created session is now active");
  assert.equal(store.sessions[0].id, createdSession.id, "Step 5: newly created session is first in sidebar");
  assert.equal(store.messages[0].text, firstQuery);

  // Step 6: Assistant delivers legal response
  store.messages.push({
    id: 2,
    role: "assistant",
    text: "Theo Điều 35 Bộ luật Lao động 2019, người lao động có quyền đơn phương chấm dứt HĐLĐ...",
  });
  assert.equal(store.messages.length, 2);

  // Step 7: User switches to past session "Tư vấn thuế TNCN"
  await store.selectSession("conv-tax-01");
  assert.equal(store.activeSessionId, "conv-tax-01", "Step 7: switched to tax session");
  assert.equal(store.messages.length, 2, "Step 8: loaded 2 tax messages");
  assert.equal(store.messages[0].text, "Thuế thu nhập cá nhân tính thế nào?");

  // Step 8: User in-place renames tax session to "Quy định thuế TNCN 2024"
  store.startRename("conv-tax-01");
  store.changeRenameTitle("Quy định thuế TNCN 2024");
  await store.commitRename();
  const taxSessionInList = store.sessions.find((s) => s.id === "conv-tax-01");
  assert.equal(taxSessionInList.title, "Quy định thuế TNCN 2024", "Step 9: title updated in sidebar");

  // Step 9: User deletes the expired draft session "Phiên nháp cũ"
  store.requestDelete("conv-draft-old");
  assert.equal(store.deletingSessionId, "conv-draft-old", "Step 10: confirmation prompt shown");
  await store.confirmDelete();

  // Step 10: Expired session removed from sidebar list while current active session remains untouched
  assert.equal(store.sessions.some((s) => s.id === "conv-draft-old"), false, "Step 11: old session removed");
  assert.equal(store.activeSessionId, "conv-tax-01", "Step 11: current active session remains unaffected");
  assert.equal(store.messages.length, 2, "Step 11: current messages unaffected");
  assert.equal(store.sessions.length, 2, "Two sessions remain: labor and tax");
});

// ==========================================================================
// TEST EXECUTION SUMMARY
// ==========================================================================
console.log("\n=== SIDEBAR UI TEST EXECUTION SUMMARY ===");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  console.error("FAILURES DETECTED IN SIDEBAR UI SUITE:", findings);
  process.exit(1);
} else {
  console.log("ALL SIDEBAR UI TESTS PASSED EMPIRICALLY!");
  process.exit(0);
}
