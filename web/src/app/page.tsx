"use client";

import { FormEvent, KeyboardEvent, useRef, useState } from "react";

type Citation = {
  document_id?: string;
  ten_van_ban?: string | null;
  so_hieu?: string | null;
  chuong?: string | null;
  dieu?: string | null;
  khoan?: string | null;
  source?: string | null;
};

type Answer = {
  query?: string;
  answer: string;
  status: "verified" | "insufficient_evidence" | "needs_clarification" | "provider_error" | string;
  citations?: Citation[];
};

type Message = { id: number; role: "user" | "assistant"; text: string; answer?: Answer; error?: boolean };

const suggestions = [
  "Người lao động được nghỉ phép năm bao nhiêu ngày?",
  "Mức phạt nồng độ cồn khi lái xe máy là bao nhiêu?",
  "Thuế thu nhập cá nhân được tính thế nào?",
];

function statusLabel(status: string) {
  if (status === "verified") return "Có căn cứ";
  if (status === "needs_clarification") return "Cần làm rõ";
  if (status === "provider_error") return "Lỗi dịch vụ";
  return "Chưa đủ căn cứ";
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <details className="sources">
      <summary><span className="source-icon">↗</span> Căn cứ tham khảo <span className="source-count">{citations.length}</span></summary>
      <div className="source-list">
        {citations.map((item, index) => (
          <article className="source-card" key={item.document_id ?? `${item.so_hieu}-${index}`}>
            <span className="source-index">{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{item.ten_van_ban || "Văn bản pháp luật"}</strong>
              <p>{[item.so_hieu, item.chuong, item.dieu, item.khoan].filter(Boolean).join(" · ") || "Chưa có thông tin điều khoản"}</p>
              {item.source && <a href={item.source} target="_blank" rel="noreferrer">Mở nguồn văn bản <span>↗</span></a>}
            </div>
          </article>
        ))}
      </div>
    </details>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);

  async function submitQuestion(value: string) {
    const query = value.trim();
    if (!query || loading) return;
    const userMessage: Message = { id: Date.now(), role: "user", text: query };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setLoading(true);
    requestAnimationFrame(() => bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Đã xảy ra lỗi. Vui lòng thử lại.");
      const answer = data as Answer;
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: "assistant",
        text: answer.answer || "Chưa nhận được câu trả lời.",
        answer,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        role: "assistant",
        text: error instanceof Error ? error.message : "Không thể gửi câu hỏi lúc này.",
        error: true,
      }]);
    } finally {
      setLoading(false);
      requestAnimationFrame(() => bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }));
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitQuestion(draft);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <main className="app-shell">
      <aside className="rail">
        <div className="brand-mark" aria-label="Trust Agent"><span /><span /><span /><span /></div>
        <div className="rail-rule" />
        <button className="rail-button active" title="Tra cứu pháp luật" aria-label="Tra cứu pháp luật"><span className="search-glyph" /></button>
        <div className="rail-bottom"><span className="rail-status-dot" title="Sẵn sàng" /></div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="brand-wordmark"><span>TRUST</span><span className="wordmark-light">AGENT</span></div>
          <div className="topbar-right"><span className="api-status">TRA CỨU PHÁP LUẬT</span><span className="topbar-divider" /><button className="help-button" title="Thông tin">?</button></div>
        </header>

        <section className={`conversation ${isEmpty ? "conversation-empty" : ""}`} aria-live="polite">
          {isEmpty ? (
            <div className="welcome">
              <div className="eyebrow"><span className="eyebrow-line" /> TRỢ LÝ PHÁP LUẬT VIỆT NAM</div>
              <h1>Hiểu luật,<br /><em>vững lựa chọn.</em></h1>
              <p className="welcome-copy">Đặt câu hỏi để tra cứu quy định pháp luật, kèm căn cứ từ văn bản liên quan.</p>
              <div className="suggestion-label">BẮT ĐẦU VỚI MỘT CÂU HỎI</div>
              <div className="suggestions">
                {suggestions.map((suggestion, index) => (
                  <button className="suggestion" key={suggestion} onClick={() => void submitQuestion(suggestion)}>
                    <span className="suggestion-number">0{index + 1}</span><span>{suggestion}</span><span className="suggestion-arrow">↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="thread">
              <div className="thread-heading"><span className="thread-dot" /> CUỘC TRA CỨU <span className="thread-count">{Math.ceil(messages.length / 2).toString().padStart(2, "0")}</span></div>
              {messages.map((message) => (
                <article className={`message message-${message.role}`} key={message.id}>
                  {message.role === "user" ? (
                    <><div className="message-label">BẠN <span>{new Date(message.id).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}</span></div><div className="user-bubble">{message.text}</div></>
                  ) : (
                    <><div className="assistant-heading"><div className="mini-mark"><span /><span /><span /><span /></div><span className="message-label">TRUST AGENT</span>{message.answer && <span className={`answer-status ${message.answer.status}`}>{statusLabel(message.answer.status)}</span>}</div>
                      <div className={`answer-copy ${message.error ? "error-copy" : ""}`}>{message.text}</div>
                      {message.answer?.citations && <CitationList citations={message.answer.citations} />}
                      {message.answer && <div className="answer-note"><span>i</span> Thông tin mang tính tham khảo, được tạo từ tài liệu hiện có.</div>}
                    </>
                  )}
                </article>
              ))}
              {loading && <div className="message message-assistant"><div className="assistant-heading"><div className="mini-mark"><span /><span /><span /><span /></div><span className="message-label">TRUST AGENT</span><span className="thinking-label">ĐANG TRA CỨU</span></div><div className="typing"><i /><i /><i /></div></div>}
              <div ref={bottom} />
            </div>
          )}
        </section>

        <footer className="composer-wrap">
          <form className="composer" onSubmit={onSubmit}>
            <textarea ref={textarea} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={onKeyDown} placeholder="Mô tả điều bạn muốn tìm hiểu..." rows={1} maxLength={2000} aria-label="Câu hỏi pháp luật" />
            <div className="composer-bottom"><span className="composer-hint"><kbd>↵</kbd> gửi <span>·</span> <kbd>shift ↵</kbd> xuống dòng</span><span className="composer-actions"><span className="char-count">{draft.length > 0 ? `${draft.length}/2000` : ""}</span><button className="send-button" type="submit" disabled={!draft.trim() || loading} aria-label="Gửi câu hỏi"><span>GỬI CÂU HỎI</span><b>↗</b></button></span></div>
          </form>
          <div className="footer-note">TRUST AGENT <span>·</span> TRA CỨU CÓ NGUỒN <span className="footer-right">PHÁP LUẬT VIỆT NAM</span></div>
        </footer>
      </section>
    </main>
  );
}
