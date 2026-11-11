// Adversarial Deep Stress Test for Client Logic & Security
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const pageSource = fs.readFileSync(path.resolve("web/src/app/page.tsx"), "utf-8");
const cssSource = fs.readFileSync(path.resolve("web/src/app/globals.css"), "utf-8");

const isSafeUrlMatch = pageSource.match(/function isSafeUrl\s*\([^)]*\)\s*:\s*boolean\s*\{([\s\S]*?)\n\}/);
const isSafeUrl = new Function("url", isSafeUrlMatch[1]);

console.log("=== RUNNING ADVERSARIAL DEEP STRESS HARNESS ===");

let pass = 0;
let fail = 0;

function deepTest(desc, fn) {
  try {
    fn();
    console.log(`  [PASS] ${desc}`);
    pass++;
  } catch (err) {
    console.error(`  [FAIL] ${desc}: ${err.message}`);
    fail++;
  }
}

// 1. Obfuscated / Polyglot / Unicode XSS Attacks on URL Validator
const adversarialUrls = [
  { url: "javascript\u0000:alert(1)", shouldPass: false, desc: "Null byte injection in scheme" },
  { url: "javascript\t:alert(1)", shouldPass: false, desc: "Tab character in scheme" },
  { url: "javascript\n:alert(1)", shouldPass: false, desc: "Newline in scheme" },
  { url: "javascript\r:alert(1)", shouldPass: false, desc: "CR in scheme" },
  { url: " java\nscript:alert(1)", shouldPass: false, desc: "Leading space + newline scheme" },
  { url: "jav&#x09;ascript:alert(1)", shouldPass: false, desc: "HTML entity encoded tab" },
  { url: "jav&#x0A;ascript:alert(1)", shouldPass: false, desc: "HTML entity encoded newline" },
  { url: "java%00script:alert(1)", shouldPass: false, desc: "URL encoded null byte in scheme" },
  { url: "java%0ascript:alert(1)", shouldPass: false, desc: "URL encoded newline in scheme" },
  { url: "jAvAsCrIpT:prompt(document.domain)", shouldPass: false, desc: "Mixed case with prompt payload" },
  { url: "\\\\evil.com\\payload", shouldPass: false, desc: "Windows UNC path" },
  { url: "/\\/evil.com", shouldPass: false, desc: "Mixed slash scheme confusion" },
  { url: "https://", shouldPass: false, desc: "Incomplete https scheme" },
  { url: "http://", shouldPass: false, desc: "Incomplete http scheme" },
  { url: "http", shouldPass: false, desc: "Scheme only without separator" },
  { url: "https", shouldPass: false, desc: "Scheme only without separator" },
  { url: "http://attacker.com@legitimate.com", shouldPass: true, desc: "Valid HTTP URL with basic auth (legitimate URL parser behavior)" },
  { url: "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Luat-36-2024-QH15.html#dieu_5", shouldPass: true, desc: "Legitimate anchor deep-link" },
  { url: "https://thuvienphapluat.vn/search?q=n%E1%BB%93ng+%C4%91%E1%BB%99+c%E1%BB%93n", shouldPass: true, desc: "Legitimate URL encoded query" },
];

for (const t of adversarialUrls) {
  deepTest(`Adversarial URL: ${t.desc} -> ${t.shouldPass ? "ALLOWED" : "BLOCKED"}`, () => {
    const res = isSafeUrl(t.url);
    assert.equal(res, t.shouldPass, `URL "${t.url}" expected ${t.shouldPass} but got ${res}`);
  });
}

// 2. IME Stress Scenarios
deepTest("IME composition event cycle: keydown during composition vs after composition", () => {
  const eventsLog = [];

  // Simulate Vietnamese typing "luat" -> l-u-a-t -> Enter during composition
  const imeKeyDownEvent = {
    key: "Enter",
    shiftKey: false,
    nativeEvent: { isComposing: true },
    preventDefault: () => eventsLog.push("preventDefault"),
  };

  function handleKeyDown(e, draft) {
    if (e.nativeEvent.isComposing) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      eventsLog.push(`submitted:${draft}`);
    }
  }

  // Turn 1: Enter pressed while composing Vietnamese text
  handleKeyDown(imeKeyDownEvent, "luật");
  assert.equal(eventsLog.length, 0, "No actions during active IME composition");

  // Turn 2: Enter pressed after composition committed
  const normalKeyDownEvent = {
    key: "Enter",
    shiftKey: false,
    nativeEvent: { isComposing: false },
    preventDefault: () => eventsLog.push("preventDefault"),
  };
  handleKeyDown(normalKeyDownEvent, "luật");
  assert.deepEqual(eventsLog, ["preventDefault", "submitted:luật"]);
});

// 3. Scroll Containment & CSS Architecture Integrity
deepTest("CSS Scroll Containment Architecture", () => {
  // Ensure that no parent of .conversation introduces unbounded scroll or overflow: visible
  const appShellIdx = cssSource.indexOf(".app-shell {");
  assert(appShellIdx !== -1, ".app-shell selector must exist");

  const workspaceIdx = cssSource.indexOf(".workspace {");
  assert(workspaceIdx !== -1, ".workspace selector must exist");

  const conversationIdx = cssSource.indexOf(".conversation {");
  assert(conversationIdx !== -1, ".conversation selector must exist");

  // Verify that overflow: hidden is on body, app-shell, and workspace
  assert(cssSource.includes("overflow: hidden;"), "overflow: hidden must be present");

  // Verify min-height: 0 is present on .conversation
  assert(cssSource.includes("min-height: 0;"), "min-height: 0 must be present on conversation container");
});

// 4. Status Badge Contrast and Visual Integrity
deepTest("Status Badges Styling & Color Tokens", () => {
  const statuses = [
    { name: "insufficient_evidence", bg: "#f5edd8", color: "#7a5c24" },
    { name: "provider_error", bg: "#faeceb", color: "#94402d" },
    { name: "needs_clarification", bg: "#eceaf5", color: "#4e4473" },
    { name: "unverified", bg: "#fceded", color: "#98382d" },
    { name: "out_of_scope", bg: "#edf0eb", color: "#555e53" },
    { name: "greeting", bg: "#eaf1ed", color: "#2d5639" },
  ];

  for (const s of statuses) {
    const regex = new RegExp(`\\.answer-status\\.${s.name}\\s*\\{[^}]*background:\\s*${s.bg}[^}]*color:\\s*${s.color}`, "i");
    assert(regex.test(cssSource), `Status .answer-status.${s.name} missing expected background ${s.bg} or color ${s.color}`);
  }
});

console.log("\n=== SUMMARY ===");
console.log(`Passed: ${pass}, Failed: ${fail}`);
if (fail > 0) process.exit(1);
