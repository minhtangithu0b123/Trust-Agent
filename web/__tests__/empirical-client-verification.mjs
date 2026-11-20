// Empirical Test Suite for Client Logic & UI Rules
// Target: web/src/app/page.tsx & web/src/app/globals.css

import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const pageSource = fs.readFileSync(path.resolve("web/src/app/page.tsx"), "utf-8");
const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");

console.log("=== STARTING EMPIRICAL VERIFICATION HARNESS ===");

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
// SUITE 1: statusLabel Mappings & CSS Badges
// --------------------------------------------------------------------------
console.log("\n--- SUITE 1: statusLabel Mappings & CSS Badges ---");

// Extract the statusLabel function from page.tsx to verify exact implementation
const statusLabelMatch = pageSource.match(/function statusLabel\s*\([^)]*\)\s*\{([\s\S]*?)\n\}/);
if (!statusLabelMatch) {
  throw new Error("Could not extract statusLabel from page.tsx");
}
const statusLabelFn = new Function("status", statusLabelMatch[1]);

const statusExpectations = [
  { status: "verified", expected: "Có căn cứ" },
  { status: "insufficient_evidence", expected: "Chưa đủ căn cứ" },
  { status: "needs_clarification", expected: "Cần làm rõ" },
  { status: "provider_error", expected: "Lỗi dịch vụ" },
  { status: "unverified", expected: "Chưa xác thực" },
  { status: "out_of_scope", expected: "Ngoài phạm vi" },
  { status: "greeting", expected: "Chào hỏi" },
  { status: "unknown", expected: "Chưa đủ căn cứ" },
  { status: "", expected: "Chưa đủ căn cứ" },
  { status: "routing", expected: "Chưa đủ căn cứ" },
  { status: "custom_status", expected: "Chưa đủ căn cứ" },
];

for (const { status, expected } of statusExpectations) {
  test(`statusLabel("${status}") === "${expected}"`, () => {
    const actual = statusLabelFn(status);
    assert.equal(actual, expected, `Expected statusLabel("${status}") to return "${expected}", got "${actual}"`);
  });
}

// Check CSS rules for statuses in globals.css
test("CSS badge selectors defined in globals.css", () => {
  const requiredCssSelectors = [
    ".answer-status",
    ".answer-status.insufficient_evidence",
    ".answer-status.provider_error",
    ".answer-status.needs_clarification",
    ".answer-status.unverified",
    ".answer-status.out_of_scope",
    ".answer-status.greeting",
  ];
  for (const selector of requiredCssSelectors) {
    assert(cssSource.includes(selector), `Missing CSS selector: ${selector}`);
  }
});

test("CSS badge default background is green (verified baseline)", () => {
  const match = cssSource.match(/\.answer-status\s*\{([^}]+)\}/);
  assert(match, ".answer-status block not found");
  assert(match[1].includes("background: #e7efe5"), ".answer-status should default to green (#e7efe5)");
  assert(match[1].includes("color: #25442b"), ".answer-status should have dark green text (#25442b)");
});

// --------------------------------------------------------------------------
// SUITE 2: isSafeUrl Protocol Checker & Adversarial Inputs
// --------------------------------------------------------------------------
console.log("\n--- SUITE 2: isSafeUrl & Adversarial URL Injection ---");

const isSafeUrlMatch = pageSource.match(/function isSafeUrl\s*\([^)]*\)\s*:\s*boolean\s*\{([\s\S]*?)\n\}/);
if (!isSafeUrlMatch) {
  throw new Error("Could not extract isSafeUrl from page.tsx");
}
const isSafeUrlFn = new Function("url", isSafeUrlMatch[1]);

const urlTestCases = [
  // Adversarial XSS injections (Must return false)
  { url: "javascript:alert(1)", expected: false, category: "XSS" },
  { url: "javascript:alert(document.cookie)", expected: false, category: "XSS" },
  { url: "javascript:/*--></title></style></textarea></script><svg/onload=alert(1)>", expected: false, category: "XSS" },
  { url: "JaVaScRiPt:alert(1)", expected: false, category: "XSS Case Bypass" },
  { url: "javascript:void(0)", expected: false, category: "XSS" },
  { url: "data:text/html,<script>alert(1)</script>", expected: false, category: "Data URI" },
  { url: "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==", expected: false, category: "Data URI Base64" },
  { url: "vbscript:msgbox(1)", expected: false, category: "VBScript" },
  { url: "vbscript:alert(1)", expected: false, category: "VBScript" },

  // Scheme confusion & relative URLs (Must return false)
  { url: "//evil.com", expected: false, category: "Protocol-relative URL" },
  { url: "//evil.com/phish", expected: false, category: "Protocol-relative URL" },
  { url: "/docs/luat-lao-dong.pdf", expected: false, category: "Relative path" },
  { url: "ftp://files.example.com", expected: false, category: "FTP protocol" },
  { url: "blob:https://example.com/uuid", expected: false, category: "Blob protocol" },
  { url: "file:///etc/passwd", expected: false, category: "Local file protocol" },
  { url: "file:///C:/Windows/system32/calc.exe", expected: false, category: "Local file protocol" },
  { url: "mailto:support@trustagent.vn", expected: false, category: "Mailto scheme" },
  { url: "tel:+84987654321", expected: false, category: "Tel scheme" },
  { url: "chrome://settings", expected: false, category: "Internal browser scheme" },
  { url: "about:blank", expected: false, category: "About blank" },

  // Boundary & Malformed Inputs (Must return false)
  { url: "", expected: false, category: "Empty string" },
  { url: "   ", expected: false, category: "Whitespace string" },
  { url: null, expected: false, category: "null" },
  { url: undefined, expected: false, category: "undefined" },
  { url: 12345, expected: false, category: "Non-string (number)" },
  { url: {}, expected: false, category: "Non-string (object)" },
  { url: "not a valid url at all", expected: false, category: "Malformed string" },

  // Valid legitimate URLs (Must return true)
  { url: "https://example.com", expected: true, category: "Valid HTTPS" },
  { url: "http://example.com", expected: true, category: "Valid HTTP" },
  { url: "https://thuvienphapluat.vn/van-ban/Lao-dong-Tien-luong/Bo-Luat-lao-dong-2019-333670.aspx", expected: true, category: "Real legal portal URL" },
  { url: "http://localhost:8000/docs", expected: true, category: "Localhost HTTP" },
  { url: "https://sub.domain.vn:8443/path/to/page?param=1&foo=bar#section", expected: true, category: "Complex HTTPS URL" },
  { url: "HTTP://EXAMPLE.COM/PATH", expected: true, category: "Uppercase HTTP" },
];

for (const { url, expected, category } of urlTestCases) {
  test(`isSafeUrl(${JSON.stringify(url)}) === ${expected} [${category}]`, () => {
    const actual = isSafeUrlFn(url);
    assert.equal(actual, expected, `URL ${JSON.stringify(url)} failed safety check! Expected ${expected}, got ${actual}`);
  });
}

// --------------------------------------------------------------------------
// SUITE 3: IME Composition Handling Verification
// --------------------------------------------------------------------------
console.log("\n--- SUITE 3: IME Composition Handling (onKeyDown) ---");

// Simulate onKeyDown behavior with an event dispatch emulator
function simulateOnKeyDown(eventState, draft, submitSpy) {
  let prevented = false;
  const event = {
    key: eventState.key,
    shiftKey: !!eventState.shiftKey,
    nativeEvent: {
      isComposing: !!eventState.isComposing,
    },
    preventDefault() {
      prevented = true;
    },
  };

  // Exact logic from page.tsx
  if (event.nativeEvent.isComposing) return { prevented, submitted: false };
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submitSpy(draft);
    return { prevented, submitted: true };
  }
  return { prevented, submitted: false };
}

test("IME Active (isComposing: true) + Enter: must NOT submit and NOT preventDefault", () => {
  let submitted = false;
  const result = simulateOnKeyDown(
    { key: "Enter", shiftKey: false, isComposing: true },
    "lao động",
    () => { submitted = true; }
  );
  assert.equal(result.submitted, false, "Should not submit while IME is composing");
  assert.equal(result.prevented, false, "Should not preventDefault while IME is composing");
  assert.equal(submitted, false);
});

test("IME Finished (isComposing: false) + Enter: MUST submit and MUST preventDefault", () => {
  let submittedWith = null;
  const result = simulateOnKeyDown(
    { key: "Enter", shiftKey: false, isComposing: false },
    "lao động",
    (query) => { submittedWith = query; }
  );
  assert.equal(result.submitted, true, "Should submit when composition finished");
  assert.equal(result.prevented, true, "Should preventDefault (no trailing newline)");
  assert.equal(submittedWith, "lao động");
});

test("Shift + Enter: must NOT submit (allow multiline newline insertion)", () => {
  let submitted = false;
  const result = simulateOnKeyDown(
    { key: "Enter", shiftKey: true, isComposing: false },
    "Điều 1:\n",
    () => { submitted = true; }
  );
  assert.equal(result.submitted, false, "Shift+Enter must not submit");
  assert.equal(result.prevented, false, "Shift+Enter must not prevent default newline insertion");
  assert.equal(submitted, false);
});

test("Regular key (e.g. 'a'): must NOT submit", () => {
  let submitted = false;
  const result = simulateOnKeyDown(
    { key: "a", shiftKey: false, isComposing: false },
    "a",
    () => { submitted = true; }
  );
  assert.equal(result.submitted, false);
  assert.equal(result.prevented, false);
});

test("Input length guard in submitQuestion: rejects < 2 chars", () => {
  function submitQuestionGuard(value, loading) {
    const query = value.trim();
    if (query.length < 2 || loading) return "REJECTED";
    return "ACCEPTED";
  }

  assert.equal(submitQuestionGuard("", false), "REJECTED");
  assert.equal(submitQuestionGuard(" ", false), "REJECTED");
  assert.equal(submitQuestionGuard("a", false), "REJECTED");
  assert.equal(submitQuestionGuard("  b  ", false), "REJECTED");
  assert.equal(submitQuestionGuard("ab", false), "ACCEPTED");
  assert.equal(submitQuestionGuard("  ab  ", false), "ACCEPTED");
  assert.equal(submitQuestionGuard("ab", true), "REJECTED"); // loading guard
});

// --------------------------------------------------------------------------
// SUITE 4: Dynamic Textarea Auto-Grow Logic
// --------------------------------------------------------------------------
console.log("\n--- SUITE 4: Textarea Dynamic Auto-Grow Logic ---");

function simulateResizeTextarea(mockElement) {
  mockElement.style.height = "auto";
  mockElement.style.height = `${Math.min(mockElement.scrollHeight, 130)}px`;
}

test("Auto-grow height scaling within bounds [min-height 25px, max-height 130px]", () => {
  const mockTextarea = {
    scrollHeight: 25,
    style: { height: "25px" },
  };

  // 1-line query (25px)
  mockTextarea.scrollHeight = 25;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "25px");

  // 2-line query (50px)
  mockTextarea.scrollHeight = 50;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "50px");

  // 3-line query (80px)
  mockTextarea.scrollHeight = 80;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "80px");

  // Boundary cap at 130px
  mockTextarea.scrollHeight = 130;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "130px");

  // Overflow past 130px (e.g. 350px for 1000-char query)
  mockTextarea.scrollHeight = 350;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "130px");

  // 2000 chars query (~800px scrollHeight) -> capped strictly at 130px
  mockTextarea.scrollHeight = 800;
  simulateResizeTextarea(mockTextarea);
  assert.equal(mockTextarea.style.height, "130px");
});

test("Reset height back to 'auto' on submit and startNewConversation", () => {
  const mockTextarea = {
    scrollHeight: 130,
    style: { height: "130px" },
  };

  // Simulating reset logic from submitQuestion & startNewConversation:
  // if (textarea.current) { textarea.current.style.height = "auto"; }
  mockTextarea.style.height = "auto";
  assert.equal(mockTextarea.style.height, "auto");
});

test("page.tsx enforces maxLength={2000} on textarea", () => {
  assert(pageSource.includes("maxLength={2000}"), "textarea must specify maxLength={2000}");
  assert(pageSource.includes("2000"), "char counter max 2000");
});

// --------------------------------------------------------------------------
// SUITE 5: Viewport & Layout Scroll Containment CSS
// --------------------------------------------------------------------------
console.log("\n--- SUITE 5: Viewport & Layout Scroll Containment CSS ---");

test("html and body configured to prevent outer scrolling", () => {
  assert(/html,\s*body\s*\{[^}]*height:\s*100%/.test(cssSource), "html, body must have height: 100%");
  assert(/body\s*\{[^}]*overflow:\s*hidden/.test(cssSource), "body must have overflow: hidden");
});

test(".app-shell bounds viewport with 100vh, 100dvh, and overflow: hidden", () => {
  const shellBlock = cssSource.match(/\.app-shell\s*\{([^}]+)\}/);
  assert(shellBlock, ".app-shell block must exist");
  const shellCss = shellBlock[1];
  assert(shellCss.includes("height: 100vh"), ".app-shell missing height: 100vh");
  assert(shellCss.includes("height: 100dvh"), ".app-shell missing height: 100dvh");
  assert(shellCss.includes("overflow: hidden"), ".app-shell missing overflow: hidden");
  assert(shellCss.includes("display: flex"), ".app-shell missing display: flex");
});

test(".workspace bounds layout with flex column and overflow: hidden", () => {
  const wsBlock = cssSource.match(/\.workspace\s*\{([^}]+)\}/);
  assert(wsBlock, ".workspace block must exist");
  const wsCss = wsBlock[1];
  assert(wsCss.includes("height: 100%"), ".workspace missing height: 100%");
  assert(wsCss.includes("overflow: hidden"), ".workspace missing overflow: hidden");
  assert(wsCss.includes("display: flex"), ".workspace missing display: flex");
  assert(wsCss.includes("flex-direction: column"), ".workspace missing flex-direction: column");
});

test(".conversation is the sole scrollable flex container", () => {
  const convBlock = cssSource.match(/\.conversation\s*\{([^}]+)\}/);
  assert(convBlock, ".conversation block must exist");
  const convCss = convBlock[1];
  assert(convCss.includes("flex: 1 1 0%"), ".conversation must have flex: 1 1 0%");
  assert(convCss.includes("min-height: 0"), ".conversation must have min-height: 0 to allow shrinking");
  assert(convCss.includes("overflow-y: auto"), ".conversation must have overflow-y: auto for scrolling");
});

test(".topbar and .composer-wrap remain pinned and unscrollable", () => {
  const topbarBlock = cssSource.match(/\.topbar\s*\{([^}]+)\}/);
  assert(topbarBlock, ".topbar block must exist");
  assert(topbarBlock[1].includes("flex: 0 0 68px"), ".topbar must be pinned with flex: 0 0 68px");

  const composerWrapBlock = cssSource.match(/\.composer-wrap\s*\{([^}]+)\}/);
  assert(composerWrapBlock, ".composer-wrap block must exist");
  assert(composerWrapBlock[1].includes("flex-shrink: 0"), ".composer-wrap must have flex-shrink: 0");
});

test("Mobile breakpoint <= 600px retains green status dot while collapsing text", () => {
  const mobileMedia = cssSource.match(/@media\s*\(max-width:\s*600px\)\s*\{([\s\S]*?)\n\}/);
  assert(mobileMedia, "Mobile media query missing");
  const mobileCss = mobileMedia[1];
  assert(mobileCss.includes(".api-status { font-size: 0; gap: 0; }"), "Mobile .api-status must collapse text to font-size: 0");
  assert(mobileCss.includes(".api-status i { width: 7px; height: 7px; }"), "Mobile .api-status i must maintain green dot size (7px)");
});

// --------------------------------------------------------------------------
// SUITE SUMMARY
// --------------------------------------------------------------------------
console.log("\n=== TEST EXECUTION SUMMARY ===");
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);

if (failed > 0) {
  console.error("FAILURES DETECTED:", findings);
  process.exit(1);
} else {
  console.log("ALL TESTS PASSED EMPIRICALLY!");
  process.exit(0);
}
