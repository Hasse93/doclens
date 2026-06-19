"use client";

import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { Citation } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  streaming?: boolean;
}

export default function ChatPanel({ documentId }: { documentId: number }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load any persisted conversation for this document.
  useEffect(() => {
    api.getMessages(documentId).then((history) =>
      setMessages(
        history.map((m) => ({
          role: m.role,
          content: m.content,
          citations: m.citations ?? undefined,
        })),
      ),
    );
  }, [documentId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    setQuestion("");
    setError(null);
    setPending(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed },
      { role: "assistant", content: "", streaming: true },
    ]);

    const updateAssistant = (mutate: (m: Message) => Message) =>
      setMessages((prev) => {
        const next = [...prev];
        const last = next.length - 1;
        next[last] = mutate(next[last]);
        return next;
      });

    try {
      const citations = await api.streamChat(documentId, trimmed, (text) =>
        updateAssistant((m) => ({ ...m, content: m.content + text })),
      );
      updateAssistant((m) => ({ ...m, citations, streaming: false }));
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Couldn't answer that. Please try again.";
      updateAssistant((m) => ({
        ...m,
        content: m.content || message,
        streaming: false,
      }));
      setError(message);
    } finally {
      setPending(false);
    }
  }

  async function clearChat() {
    await api.clearMessages(documentId);
    setMessages([]);
  }

  return (
    <div className="flex h-full flex-col rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
        <div>
          <h2 className="font-semibold text-slate-900">Ask this document</h2>
          <p className="text-xs text-slate-400">Answers cite the pages they come from.</p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            className="text-xs text-slate-400 transition hover:text-red-600"
          >
            Clear
          </button>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Try “What problem does this paper address?” or “Summarise the results.”
          </p>
        )}

        {messages.map((message, i) =>
          message.role === "user" ? (
            <p
              key={i}
              className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-3 py-2 text-sm text-white"
            >
              {message.content}
            </p>
          ) : (
            <div key={i} className="max-w-[90%] space-y-2">
              <p className="whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-slate-100 px-3 py-2 text-sm text-slate-800">
                {message.content || (message.streaming ? "…" : "")}
                {message.streaming && message.content && (
                  <span className="ml-0.5 inline-block animate-pulse">▍</span>
                )}
              </p>
              {message.citations && message.citations.length > 0 && (
                <div className="space-y-1.5">
                  {message.citations.map((c) => (
                    <div
                      key={c.marker}
                      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600"
                    >
                      <span className="font-semibold text-brand-700">
                        [{c.marker}] page {c.page_number}
                      </span>{" "}
                      — {c.snippet}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ),
        )}
      </div>

      {error && <p className="px-5 text-sm text-red-600">{error}</p>}

      <form onSubmit={ask} className="flex gap-2 border-t border-slate-200 p-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
        <button
          type="submit"
          disabled={pending || !question.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
