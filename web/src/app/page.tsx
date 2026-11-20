"use client";

import {
  ChangeEvent,
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { connectAvalancheFujiWallet, createPaidX402Client } from "../lib/x402-client";

type AnswerStatus =
  | "verified"
  | "insufficient_evidence"
  | "unverified"
  | "needs_clarification"
  | "provider_error"
  | "greeting"
  | "out_of_scope"
  | (string & {});

type Citation = {
  document_id?: string;
  ten_van_ban?: string | null;
  so_hieu?: string | null;
  chuong?: string | null;
  dieu?: string | null;
  khoan?: string | null;
  source?: string | null;
  status?: string | null;
  effective_from?: string | null;
};

type Answer = {
  query?: string;
  thread_id?: string;
  conversation_id?: string;
  session_id?: string;
  answer: string;
  status: AnswerStatus;
  guardrail_status?: string;
  guardrail_warnings?: string[];
  citations?: Citation[];
  provenance?: { receipt_id?: string; receipt_hash?: string; index_version?: string };
  payment?: { scheme?: string; network?: string; transaction?: string; success?: boolean };
};

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
  answer?: Answer;
  error?: boolean;
  failedQuery?: string;
};

type ConversationSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string | null;
};

type StoredMessage = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  citations?: Citation[];
  status?: AnswerStatus | null;
  created_at: string;
};

function generateConversationTitle(query: string): string {
  const cleaned = query.replace(/\s+/g, " ").trim();
  if (cleaned.length <= 40) return cleaned || "Cuộc trò chuyện mới";
  return cleaned.slice(0, 37).trim() + "...";
}

function sortConversations(items: ConversationSummary[]): ConversationSummary[] {
  return [...items].sort((left, right) => {
    const updatedDifference =
      new Date(right.updated_at || right.created_at).getTime() -
      new Date(left.updated_at || left.created_at).getTime();
    if (updatedDifference !== 0) return updatedDifference;
    return right.id.localeCompare(left.id);
  });
}

function storedMessageToMessage(item: StoredMessage): Message | null {
  if (item.role !== "user" && item.role !== "assistant") return null;
  const role = item.role;
  return {
    id: item.id,
    role,
    text: item.content,
    createdAt: item.created_at,
    ...(role === "assistant"
      ? {
          answer: {
            answer: item.content,
            status: item.status || "insufficient_evidence",
            citations: item.citations || [],
          },
        }
      : {}),
  };
}

const suggestions = [
  "Người lao động được nghỉ phép năm bao nhiêu ngày?",
  "Mức phạt nồng độ cồn khi lái xe máy là bao nhiêu?",
  "Thuế thu nhập cá nhân được tính thế nào?",
];

function statusLabel(status: string) {
  switch (status) {
    case "verified":
      return "Có căn cứ";
    case "needs_clarification":
      return "Cần làm rõ";
    case "provider_error":
      return "Lỗi dịch vụ";
    case "unverified":
      return "Chưa xác thực";
    case "out_of_scope":
      return "Ngoài phạm vi";
    case "greeting":
      return "Chào hỏi";
    case "insufficient_evidence":
    default:
      return "Chưa đủ căn cứ";
  }
}

function isSafeUrl(url?: string | null): boolean {
  if (!url || typeof url !== "string") return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <details className="sources">
      <summary>
        <span className="source-icon">↗</span> Căn cứ tham khảo{" "}
        <span className="source-count">{citations.length}</span>
      </summary>
      <div className="source-list">
        {citations.map((item, index) => (
          <article
            className="source-card"
            key={`${item.document_id || item.so_hieu || "cit"}-${index}`}
          >
            <span className="source-index">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{item.ten_van_ban || "Văn bản pháp luật"}</strong>
              <p>
                {[item.so_hieu, item.chuong, item.dieu, item.khoan]
                  .filter(Boolean)
                  .join(" · ") || "Chưa có thông tin điều khoản"}
              </p>
              {isSafeUrl(item.source) && (
                <a
                  href={item.source!}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Mở nguồn văn bản <span>↗</span>
                </a>
              )}
            </div>
          </article>
        ))}
      </div>
    </details>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [conversationError, setConversationError] = useState<string | null>(null);
  const [editingConversationId, setEditingConversationId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [deletingConversationId, setDeletingConversationId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [walletBusy, setWalletBusy] = useState(false);
  const [walletNotice, setWalletNotice] = useState<string | null>(null);

  const textarea = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const historyControllerRef = useRef<AbortController | null>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    void (async () => {
      const items = await refreshConversations();
      const rememberedId = window.localStorage.getItem("trust-agent-active-conversation");
      if (rememberedId && items.some((item) => item.id === rememberedId)) {
        await selectConversation(rememberedId);
      }
    })();

    return () => {
      abortControllerRef.current?.abort();
      historyControllerRef.current?.abort();
    };
  }, []);

  function responseError(data: unknown, fallback: string): string {
    if (!data || typeof data !== "object" || !("detail" in data)) return fallback;
    const detail = (data as { detail: unknown }).detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item: unknown) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return typeof item === "string" ? item : JSON.stringify(item);
        })
        .join(", ");
    }
    return typeof detail === "string" ? detail : String(detail ?? fallback);
  }

  async function connectWallet() {
    setWalletBusy(true);
    setWalletNotice(null);
    try {
      const address = await connectAvalancheFujiWallet();
      setWalletAddress(address);
      setWalletNotice("Ví đã kết nối trên Avalanche Fuji. API trả phí chỉ ký khi bạn xác nhận.");
    } catch (error: unknown) {
      setWalletNotice(error instanceof Error ? error.message : "Không thể kết nối ví.");
    } finally {
      setWalletBusy(false);
    }
  }

  function shortAddress(address: string): string {
    return `${address.slice(0, 6)}…${address.slice(-4)}`;
  }

  async function refreshConversations(): Promise<ConversationSummary[]> {
    try {
      const response = await fetch("/api/conversations", { cache: "no-store" });
      const data = await response.json().catch(() => null);
      if (!response.ok || !Array.isArray(data)) {
        throw new Error(responseError(data, "Không thể tải danh sách cuộc trò chuyện."));
      }
      const sorted = sortConversations(data as ConversationSummary[]);
      setConversations(sorted);
      setConversationError(null);
      return sorted;
    } catch (error: unknown) {
      setConversationError(
        error instanceof Error ? error.message : "Không thể tải danh sách cuộc trò chuyện.",
      );
      return [];
    } finally {
      setLoadingConversations(false);
    }
  }

  async function selectConversation(conversationId: string) {
    if (loading || conversationId === threadId) {
      setSidebarOpen(false);
      return;
    }

    abortControllerRef.current?.abort();
    historyControllerRef.current?.abort();
    const controller = new AbortController();
    historyControllerRef.current = controller;

    setThreadId(conversationId);
    setMessages([]);
    setLoadingHistory(true);
    setConversationError(null);
    setEditingConversationId(null);
    setDeletingConversationId(null);
    window.localStorage.setItem("trust-agent-active-conversation", conversationId);

    try {
      const response = await fetch(
        "/api/conversations/" + encodeURIComponent(conversationId) + "/messages",
        { cache: "no-store", signal: controller.signal },
      );
      const data = await response.json().catch(() => null);
      if (!response.ok || !Array.isArray(data)) {
        throw new Error(responseError(data, "Không thể tải lịch sử cuộc trò chuyện."));
      }
      const restored = (data as StoredMessage[])
        .map(storedMessageToMessage)
        .filter((item): item is Message => item !== null);
      setMessages(restored);
      setSidebarOpen(false);
      requestAnimationFrame(() =>
        bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }),
      );
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") return;
      setConversationError(
        error instanceof Error ? error.message : "Không thể tải lịch sử cuộc trò chuyện.",
      );
    } finally {
      if (!controller.signal.aborted) setLoadingHistory(false);
    }
  }

  function resizeTextarea() {
    if (textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.style.height = Math.min(textarea.current.scrollHeight, 130) + "px";
    }
  }

  function handleDraftChange(event: ChangeEvent<HTMLTextAreaElement>) {
    setDraft(event.target.value);
    resizeTextarea();
  }

  async function createConversation(query: string, signal: AbortSignal): Promise<ConversationSummary> {
    const response = await fetch("/api/conversations", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title: generateConversationTitle(query) }),
      signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok || !data || typeof data !== "object" || !("id" in data)) {
      throw new Error(responseError(data, "Không thể tạo cuộc trò chuyện."));
    }
    const created = data as ConversationSummary;
    setConversations((current) => sortConversations([created, ...current]));
    setThreadId(created.id);
    window.localStorage.setItem("trust-agent-active-conversation", created.id);
    return created;
  }

  async function submitQuestion(value: string, paid = false) {
    const query = value.trim();
    if (query.length < 2 || loading || loadingHistory) return;
    if (paid && !walletAddress) {
      setWalletNotice("Hãy kết nối ví trước khi gửi câu hỏi trả phí.");
      return;
    }

    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const createdAt = new Date().toISOString();
    const userMessage: Message = {
      id: "client-user-" + Date.now(),
      role: "user",
      text: query,
      createdAt,
    };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    if (textarea.current) textarea.current.style.height = "auto";
    setLoading(true);
    setConversationError(null);
    let pendingAssistantMessageId: string | null = null;
    requestAnimationFrame(() =>
      bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }),
    );

    try {
      let conversationId = threadId;
      if (!conversationId) {
        const created = await createConversation(query, controller.signal);
        conversationId = created.id;
      }

      let response: Response;
      let paidClient: Awaited<ReturnType<typeof createPaidX402Client>> | null = null;
      if (paid) {
        const validationResponse = await fetch("/api/paid/validate", {
          method: "POST",
          headers: { "content-type": "application/json", accept: "application/json" },
          body: JSON.stringify({ query, conversation_id: conversationId }),
          signal: controller.signal,
        });
        const validation = await validationResponse.json().catch(() => null);
        if (!validationResponse.ok) {
          throw new Error(responseError(validation, "Không thể kiểm tra câu hỏi trả phí."));
        }
        if (validation?.allowed === false) {
          const rejectedAnswer: Answer = {
            answer: validation.answer || "Hãy nhập câu hỏi pháp luật cụ thể.",
            status: validation.status || "needs_clarification",
            citations: [],
          };
          setMessages((current) => [
            ...current,
            {
              id: "client-assistant-" + Date.now(),
              role: "assistant",
              text: rejectedAnswer.answer,
              createdAt: new Date().toISOString(),
              answer: rejectedAnswer,
            },
          ]);
          const resolvedConversationId =
            validation.conversation_id || validation.thread_id || validation.session_id || conversationId;
          if (resolvedConversationId) {
            setThreadId(resolvedConversationId);
            window.localStorage.setItem(
              "trust-agent-active-conversation",
              resolvedConversationId,
            );
          }
          void refreshConversations();
          return;
        }
        paidClient = await createPaidX402Client(walletAddress as `0x${string}`);
        response = await paidClient.fetchWithPayment("/api/paid/ask", {
          method: "POST",
          headers: { "content-type": "application/json", accept: "application/json" },
          body: JSON.stringify({ query, conversation_id: conversationId }),
          signal: controller.signal,
        });
      } else {
        response = await fetch("/api/ask", {
          method: "POST",
          headers: {
            "content-type": "application/json",
            accept: "text/event-stream, application/json",
          },
          body: JSON.stringify({ query, thread_id: conversationId, stream: true }),
          signal: controller.signal,
        });
      }

      const contentType = response.headers.get("content-type") || "";

      if (response.ok && contentType.includes("text/event-stream") && response.body) {
        const assistantMessageId = "client-assistant-" + Date.now();
        pendingAssistantMessageId = assistantMessageId;
        let accumulatedText = "";
        let finalAnswer: Answer | null = null;
        let streamError: string | null = null;

        // Place placeholder message in UI
        setMessages((current) => [
          ...current,
          {
            id: assistantMessageId,
            role: "assistant",
            text: "",
            createdAt: new Date().toISOString(),
          },
        ]);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";

          for (const block of blocks) {
            if (!block.trim()) continue;
            let eventType = "message";
            let eventData = "";
            for (const rawLine of block.split("\n")) {
              const line = rawLine.trimEnd();
              if (line.startsWith("event:")) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                eventData = line.slice(5).trim();
              }
            }

            if (eventType === "token") {
              try {
                const parsed = JSON.parse(eventData);
                if (parsed.delta) {
                  accumulatedText += parsed.delta;
                  setMessages((current) =>
                    current.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, text: accumulatedText }
                        : msg
                    )
                  );
                }
              } catch {
                // Ignore parse errors on partial frames
              }
            } else if (eventType === "final") {
              try {
                finalAnswer = JSON.parse(eventData) as Answer;
              } catch {
                // Ignore parse error
              }
            } else if (eventType === "error") {
              try {
                const parsed = JSON.parse(eventData) as { detail?: unknown };
                streamError = typeof parsed.detail === "string" ? parsed.detail : "Trust Agent stream error.";
              } catch {
                streamError = eventData || "Trust Agent stream error.";
              }
            }
          }
        }

        if (streamError) throw new Error(streamError);

        const resolvedConversationId =
          finalAnswer?.conversation_id || finalAnswer?.thread_id || conversationId;
        if (resolvedConversationId) {
          setThreadId(resolvedConversationId);
          window.localStorage.setItem(
            "trust-agent-active-conversation",
            resolvedConversationId,
          );
        }

        setMessages((current) =>
          current.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  text: finalAnswer?.answer || accumulatedText || "Chưa nhận được câu trả lời.",
                  answer: finalAnswer || {
                    answer: accumulatedText,
                    status: "verified",
                  },
                }
              : msg
          )
        );
        void refreshConversations();
        return;
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const fallback =
          response.status >= 502 && response.status <= 504
            ? "Hệ thống tạm thời gián đoạn (mã HTTP " + response.status + "). Vui lòng thử lại sau giây lát."
            : "Đã xảy ra lỗi. Vui lòng thử lại.";
        throw new Error(responseError(data, fallback));
      }
      if (!data || typeof data !== "object") {
        throw new Error("Phản hồi từ máy chủ không đúng định dạng.");
      }

      const answer = data as Answer;
      if (paid && paidClient) {
        try {
          const settlement = paidClient.getSettlement(response);
          if (settlement.success) {
            answer.payment = {
              ...answer.payment,
              success: true,
              transaction: settlement.transaction,
              network: settlement.network,
            };
          }
        } catch {
          // The API response can still be useful if a facilitator omits its receipt header.
        }
      }
      const resolvedConversationId =
        answer.conversation_id || answer.thread_id || answer.session_id || conversationId;
      if (resolvedConversationId) {
        setThreadId(resolvedConversationId);
        window.localStorage.setItem(
          "trust-agent-active-conversation",
          resolvedConversationId,
        );
      }

      setMessages((current) => [
        ...current,
        {
          id: "client-assistant-" + Date.now(),
          role: "assistant",
          text: answer.answer || "Chưa nhận được câu trả lời.",
          createdAt: new Date().toISOString(),
          answer,
        },
      ]);
      void refreshConversations();
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        if (!pendingAssistantMessageId) return;
        error = new Error("Request timed out. Please try again.");
      }
      const errorText =
        error instanceof Error ? error.message : "Không thể gửi câu hỏi lúc này.";
      setMessages((current) => [
        ...current,
        {
          id: "client-error-" + Date.now(),
          role: "assistant",
          text: errorText,
          createdAt: new Date().toISOString(),
          error: true,
          failedQuery: query,
        },
      ]);
      if (pendingAssistantMessageId) {
        setMessages((current) => current.filter((message) => message.id !== pendingAssistantMessageId));
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
      requestAnimationFrame(() =>
        bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }),
      );
    }
  }

  function startNewConversation() {
    abortControllerRef.current?.abort();
    historyControllerRef.current?.abort();
    abortControllerRef.current = null;
    historyControllerRef.current = null;
    setMessages([]);
    setThreadId(null);
    setDraft("");
    setLoading(false);
    setLoadingHistory(false);
    setEditingConversationId(null);
    setDeletingConversationId(null);
    setSidebarOpen(false);
    window.localStorage.removeItem("trust-agent-active-conversation");
    if (textarea.current) {
      textarea.current.style.height = "auto";
      textarea.current.focus();
    }
  }

  function beginRename(item: ConversationSummary) {
    setEditingConversationId(item.id);
    setEditingTitle(item.title);
    setDeletingConversationId(null);
  }

  async function commitRename(conversationId: string) {
    const title = editingTitle.trim();
    if (!title) return;
    try {
      const response = await fetch("/api/conversations/" + encodeURIComponent(conversationId), {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ title }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(responseError(data, "Không thể đổi tên cuộc trò chuyện."));
      }
      setConversations((current) =>
        sortConversations(
          current.map((item) =>
            item.id === conversationId
              ? { ...item, title, updated_at: new Date().toISOString() }
              : item,
          ),
        ),
      );
      setEditingConversationId(null);
      setEditingTitle("");
      setConversationError(null);
    } catch (error: unknown) {
      setConversationError(
        error instanceof Error ? error.message : "Không thể đổi tên cuộc trò chuyện.",
      );
    }
  }

  async function confirmDelete(conversationId: string) {
    try {
      const response = await fetch("/api/conversations/" + encodeURIComponent(conversationId), {
        method: "DELETE",
      });
      const data = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(responseError(data, "Không thể xóa cuộc trò chuyện."));
      }
      setConversations((current) => current.filter((item) => item.id !== conversationId));
      if (threadId === conversationId) startNewConversation();
      setDeletingConversationId(null);
      setConversationError(null);
    } catch (error: unknown) {
      setConversationError(
        error instanceof Error ? error.message : "Không thể xóa cuộc trò chuyện.",
      );
    }
  }

  async function clearHistory() {
    if (!conversations.length || !window.confirm("Xóa toàn bộ lịch sử tra cứu?")) return;
    try {
      const response = await fetch("/api/conversations", { method: "DELETE" });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(responseError(data, "Không thể xóa lịch sử tra cứu."));
      }
      startNewConversation();
      setConversations([]);
      setConversationError(null);
    } catch (error: unknown) {
      setConversationError(
        error instanceof Error ? error.message : "Không thể xóa lịch sử tra cứu.",
      );
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuestion(draft);
    }
  }

  const activeConversation = conversations.find((item) => item.id === threadId);
  const isEmpty = messages.length === 0;

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand-mark" aria-label="Trust Agent">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="rail-rule" />
        <button
          type="button"
          className="rail-button active"
          title="Tra cứu pháp luật"
          aria-label="Mở lịch sử tra cứu"
          onClick={() => setSidebarOpen((current) => !current)}
        >
          <span className="search-glyph" />
        </button>
        <button
          type="button"
          className="rail-button new-chat-button"
          title="Cuộc hội thoại mới"
          aria-label="Cuộc hội thoại mới"
          disabled={loading || loadingHistory}
          onClick={startNewConversation}
        >
          <span className="plus-glyph">+</span>
        </button>
        <div className="rail-bottom">
          <span className="rail-status-dot" title="Sẵn sàng" />
        </div>
      </aside>

      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-scrim"
          aria-label="Đóng lịch sử hội thoại"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={"history-sidebar " + (sidebarOpen ? "history-sidebar-open" : "")}>
        <div className="history-header">
          <div>
            <span className="history-kicker">TRUST AGENT</span>
            <h2>Lịch sử tra cứu</h2>
          </div>
          <button
            type="button"
            className="history-close"
            aria-label="Đóng lịch sử"
            onClick={() => setSidebarOpen(false)}
          >
            ×
          </button>
        </div>

        <button
          type="button"
          className="history-new-chat"
          onClick={startNewConversation}
        >
          <span>＋</span>
          Cuộc trò chuyện mới
        </button>

        <div className="history-list-label">GẦN ĐÂY</div>
        {conversations.length > 0 && (
          <button
            type="button"
            className="history-clear"
            onClick={() => void clearHistory()}
            aria-label="Xóa toàn bộ lịch sử tra cứu"
          >
            <svg aria-hidden="true" viewBox="0 0 16 16" fill="none">
              <path d="M3.5 5h9M6 5V3.5h4V5m1.5 0-.55 7.15a1 1 0 0 1-1 .85h-4a1 1 0 0 1-1-.85L4.5 5m2 2v4m3-4v4" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Xóa toàn bộ lịch sử
          </button>
        )}
        <div className="history-list">
          {loadingConversations ? (
            <div className="history-state">Đang tải lịch sử...</div>
          ) : conversations.length === 0 ? (
            <div className="history-state">Chưa có cuộc trò chuyện nào</div>
          ) : (
            conversations.map((item) => (
              <div
                className={"history-item " + (threadId === item.id ? "history-item-active" : "")}
                key={item.id}
              >
                {editingConversationId === item.id ? (
                  <form
                    className="history-rename"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void commitRename(item.id);
                    }}
                  >
                    <input
                      value={editingTitle}
                      onChange={(event) => setEditingTitle(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          setEditingConversationId(null);
                          setEditingTitle("");
                        }
                      }}
                      maxLength={255}
                      autoFocus
                      aria-label="Tên cuộc trò chuyện"
                    />
                    <button type="submit" disabled={!editingTitle.trim()} title="Lưu">
                      ✓
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingConversationId(null);
                        setEditingTitle("");
                      }}
                      title="Hủy"
                    >
                      ×
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      type="button"
                      className="history-item-main"
                      onClick={() => void selectConversation(item.id)}
                      disabled={loading || loadingHistory}
                    >
                      <strong>{item.title}</strong>
                      <span>
                        {item.last_message || item.message_count + " tin nhắn"}
                      </span>
                    </button>
                    <div className="history-item-actions">
                      <button
                        type="button"
                        onClick={() => beginRename(item)}
                        title="Đổi tên"
                        aria-label={"Đổi tên " + item.title}
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setDeletingConversationId(item.id);
                          setEditingConversationId(null);
                        }}
                        title="Xóa"
                        aria-label={"Xóa " + item.title}
                      >
                        ×
                      </button>
                    </div>
                  </>
                )}

                {deletingConversationId === item.id && (
                  <div className="history-delete-confirm">
                    <span>Xóa cuộc trò chuyện này?</span>
                    <button type="button" onClick={() => void confirmDelete(item.id)}>
                      Xóa
                    </button>
                    <button type="button" onClick={() => setDeletingConversationId(null)}>
                      Hủy
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {conversationError && (
          <div className="history-error" role="alert">
            {conversationError}
            <button type="button" onClick={() => void refreshConversations()}>
              Thử lại
            </button>
          </div>
        )}
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="topbar-title-group">
            <button
              type="button"
              className="history-toggle"
              aria-label="Mở lịch sử cuộc trò chuyện"
              onClick={() => setSidebarOpen(true)}
            >
              ☰
            </button>
            <div>
              <div className="brand-wordmark">
                <span>TRUST</span>
                <span className="wordmark-light">AGENT</span>
              </div>
              {activeConversation && (
                <div className="active-conversation-title">{activeConversation.title}</div>
              )}
            </div>
          </div>
          <div className="topbar-right">
            <span className="api-status">
              <i aria-hidden="true" />
              TRA CỨU PHÁP LUẬT
            </span>
            <span className="topbar-divider" />
            <button
              type="button"
              className={`wallet-connect ${walletAddress ? "wallet-connected" : ""}`}
              onClick={() => void connectWallet()}
              disabled={walletBusy}
              title={walletAddress || "Kết nối ví Avalanche Fuji để gọi API x402"}
            >
              {walletBusy ? "ĐANG KẾT NỐI…" : walletAddress ? shortAddress(walletAddress) : "KẾT NỐI VÍ"}
            </button>
            <button
              type="button"
              className="help-button"
              title="Thông tin trợ lý"
              aria-label="Thông tin trợ lý pháp luật"
              onClick={() => setShowHelp(true)}
            >
              ?
            </button>
          </div>
        </header>

        <section
          className={`conversation ${isEmpty ? "conversation-empty" : ""}`}
          aria-live="polite"
        >
          {loadingHistory ? (
            <div className="history-loading" role="status">
              <span className="button-spinner" aria-hidden="true" />
              Đang tải cuộc trò chuyện...
            </div>
          ) : isEmpty ? (
            <div className="welcome">
              <div className="eyebrow">
                <span className="eyebrow-line" /> TRỢ LÝ PHÁP LUẬT VIỆT NAM
              </div>
              <h1>
                Hiểu luật,
                <br />
                <em>vững lựa chọn.</em>
              </h1>
              <p className="welcome-copy">
                Đặt câu hỏi để tra cứu quy định pháp luật, kèm căn cứ từ văn bản liên quan.
              </p>
              <div className="suggestion-label">BẮT ĐẦU VỚI MỘT CÂU HỎI</div>
              <div className="suggestions">
                {suggestions.map((suggestion, index) => (
                  <button
                    type="button"
                    className="suggestion"
                    key={suggestion}
                    disabled={loading || loadingHistory}
                    onClick={() => void submitQuestion(suggestion)}
                  >
                    <span className="suggestion-number">0{index + 1}</span>
                    <span>{suggestion}</span>
                    <span className="suggestion-arrow">↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="thread">
              <div className="thread-heading">
                <span className="thread-dot" /> {activeConversation?.title || "CUỘC TRA CỨU"}{" "}
                <span className="thread-count">
                  {Math.ceil(messages.length / 2).toString().padStart(2, "0")}
                </span>
              </div>
              {messages.map((message) => (
                <article className={`message message-${message.role}`} key={message.id}>
                  {message.role === "user" ? (
                    <>
                      <div className="message-label">
                        BẠN{" "}
                        <span>
                          {new Date(message.createdAt).toLocaleTimeString("vi-VN", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <div className="user-bubble">{message.text}</div>
                    </>
                  ) : (
                    <>
                      <div className="assistant-heading">
                        <div className="mini-mark">
                          <span />
                          <span />
                          <span />
                          <span />
                        </div>
                        <span className="message-label">TRUST AGENT</span>
                        {message.answer && (
                          <span className={`answer-status ${message.answer.status}`}>
                            {statusLabel(message.answer.status)}
                          </span>
                        )}
                      </div>
                      <div className={`answer-copy ${message.error ? "error-copy" : ""}`}>
                        {message.text}
                      </div>
                      {message.failedQuery && (
                        <button
                          type="button"
                          className="retry-button"
                          disabled={loading || loadingHistory}
                          onClick={() => void submitQuestion(message.failedQuery!)}
                        >
                          ↻ Thử lại câu hỏi này
                        </button>
                      )}
                      {message.answer?.citations && (
                        <CitationList citations={message.answer.citations} />
                      )}
                      {message.answer && (
                        <div className="answer-note">
                          <span>i</span> Thông tin mang tính tham khảo, được tạo từ tài liệu hiện có.
                        </div>
                      )}
                      {message.answer?.payment?.transaction && (
                        <div className="x402-receipt">
                          <span>Đã thanh toán 0.01 USDC · Avalanche Fuji</span>
                          <a
                            href={`https://testnet.snowtrace.io/tx/${message.answer.payment.transaction}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Xem giao dịch ↗
                          </a>
                          {message.answer.provenance?.receipt_id && (
                            <span>Mã bằng chứng: {message.answer.provenance.receipt_id}</span>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </article>
              ))}
              {loading && (
                <div className="message message-assistant">
                  <div className="assistant-heading">
                    <div className="mini-mark">
                      <span />
                      <span />
                      <span />
                      <span />
                    </div>
                    <span className="message-label">TRUST AGENT</span>
                    <span className="thinking-label">ĐANG TRA CỨU</span>
                  </div>
                  <div className="typing" role="status" aria-label="Đang xử lý câu trả lời">
                    <i />
                    <i />
                    <i />
                  </div>
                </div>
              )}
              <div ref={bottom} />
            </div>
          )}
        </section>

        <footer className="composer-wrap">
          <form className="composer" onSubmit={onSubmit}>
            <textarea
              ref={textarea}
              value={draft}
              onChange={handleDraftChange}
              onKeyDown={onKeyDown}
              placeholder={loading ? "Đang xử lý câu hỏi..." : loadingHistory ? "Đang tải lịch sử..." : "Mô tả điều bạn muốn tìm hiểu..."}
              rows={1}
              maxLength={2000}
              disabled={loading || loadingHistory}
              aria-label="Câu hỏi pháp luật"
            />
            <div className="composer-bottom">
              <span className="composer-hint">
                <kbd>↵</kbd> gửi <span>·</span> <kbd>shift ↵</kbd> xuống dòng
              </span>
              <span className="composer-actions">
                <span className="char-count">
                  {draft.length > 0 ? `${draft.length}/2000` : ""}
                </span>
                <button
                  className="send-button"
                  type="submit"
                  disabled={draft.trim().length < 2 || loading || loadingHistory}
                  aria-label={loading ? "Đang gửi câu hỏi" : "Gửi câu hỏi"}
                >
                  {loading ? (
                    <>
                      <span>ĐANG GỬI</span>
                      <span className="button-spinner" aria-hidden="true" />
                    </>
                  ) : (
                    <>
                      <span>GỬI CÂU HỎI</span>
                      <b>↗</b>
                    </>
                  )}
                </button>
                <button
                  className="paid-send-button"
                  type="button"
                  onClick={() => void submitQuestion(draft, true)}
                  disabled={draft.trim().length < 2 || loading || loadingHistory || !walletAddress}
                  title="Gọi paid API pháp luật bằng x402; giá 0.01 USDC trên Avalanche Fuji"
                >
                  {loading ? "ĐANG XỬ LÝ" : "X402 · 0.01 USDC"}
                </button>
              </span>
            </div>
          </form>
          <div className="x402-note" role="status">
            <span>TRẢ PHÍ CHO TRA CỨU PHÁP LUẬT</span>
            <span>0.01 USDC · Avalanche Fuji</span>
            {walletAddress && <span>Ví {shortAddress(walletAddress)}</span>}
            {walletNotice && <span className="x402-wallet-notice">{walletNotice}</span>}
            <span className="x402-history-note">Câu hỏi x402 được lưu vào lịch sử tra cứu của bạn.</span>
          </div>
          <div className="footer-note">
            TRUST AGENT <span>·</span> TRA CỨU CÓ NGUỒN{" "}
            <span className="footer-right">PHÁP LUẬT VIỆT NAM</span>
          </div>
        </footer>
      </section>

      {showHelp && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="help-modal-title"
          onClick={() => setShowHelp(false)}
        >
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 id="help-modal-title" className="modal-title">
                Về Trợ Lý Pháp Luật Trust-AGENT
              </h2>
              <button
                type="button"
                className="modal-close"
                onClick={() => setShowHelp(false)}
                aria-label="Đóng"
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              <p>
                <strong>Trust-AGENT</strong> là hệ thống hỗ trợ tra cứu văn bản quy phạm pháp luật
                Việt Nam ứng dụng công nghệ RAG (Retrieval-Augmented Generation) đa lĩnh vực:
              </p>
              <ul>
                <li>
                  <strong>Giao thông đường bộ:</strong> Luật Trật tự ATGT đường bộ 2024, Luật Đường bộ
                  2024, Nghị định 168/2024/NĐ-CP, Nghị định 100/2019/NĐ-CP.
                </li>
                <li>
                  <strong>Lao động & Tiền lương:</strong> Bộ luật Lao động 2019, các nghị định về tiền
                  lương và bảo hiểm xã hội.
                </li>
                <li>
                  <strong>Thuế:</strong> Luật Quản lý thuế, thuế TNCN, thuế GTGT.
                </li>
              </ul>
              <p>
                <strong>Ý nghĩa các trạng thái câu trả lời:</strong>
              </p>
              <ul>
                <li>
                  <em>Có căn cứ:</em> Trả lời được đối chiếu và trích xuất trực tiếp từ điều khoản văn
                  bản pháp luật hiện hành.
                </li>
                <li>
                  <em>Cần làm rõ:</em> Câu hỏi có nhiều tình huống pháp lý hoặc cần thêm chi tiết để
                  trả lời chính xác.
                </li>
                <li>
                  <em>Chưa đủ căn cứ / Chưa xác thực:</em> Dữ liệu trích xuất chưa đủ cơ sở để khẳng
                  định một cách chắc chắn.
                </li>
                <li>
                  <em>Ngoài phạm vi:</em> Câu hỏi nằm ngoài các lĩnh vực pháp lý mà hệ thống hỗ trợ.
                </li>
              </ul>
              <p>
                <em>Lưu ý quan trọng:</em> Toàn bộ thông tin do AI tổng hợp từ văn bản quy phạm pháp
                luật hiện hành nhằm mục đích tham khảo, không thay thế văn bản pháp lý chính thức
                hoặc ý kiến tư vấn từ luật sư/cơ quan có thẩm quyền.
              </p>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="modal-button"
                onClick={() => setShowHelp(false)}
              >
                Đã hiểu
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
