"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type ChatModel = {
  provider: "openai" | "mistral";
  model: string;
  credential_configured: boolean;
};

type ConversationSummary = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
};

type ConversationMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  provider: string | null;
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  credits_charged: number;
};

type ChatResult = {
  request_id: number;
  conversation_id: number;
  provider: string;
  model: string;
  content: string;
  prompt_tokens: number;
  completion_tokens: number;
  credits_charged: number;
  credits_refunded: number;
  balance: number;
};

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "aiph-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
}

export default function ChatPanel() {
  const [models, setModels] = useState<ChatModel[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [history, setHistory] = useState<ConversationMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState<ChatResult | null>(null);
  const [error, setError] = useState("");
  const [loadingModels, setLoadingModels] = useState(true);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/chat/models", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load available models");
        return (await response.json()) as { items: ChatModel[] };
      })
      .then((data) => {
        if (!active) return;
        setModels(data.items);
        if (data.items.length) {
          setSelectedKey(data.items[0].provider + ":" + data.items[0].model);
        }
      })
      .catch((cause: Error) => {
        if (active) setError(cause.message);
      })
      .finally(() => {
        if (active) setLoadingModels(false);
      });

    fetch("/api/chat/conversations", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return [];
        return (await response.json()) as ConversationSummary[];
      })
      .then(async (items) => {
        if (!active || !items.length) return;
        setConversations(items);
        const response = await fetch("/api/chat/conversations/" + items[0].id, { cache: "no-store" });
        if (!response.ok) return;
        const detail = await response.json();
        if (!active) return;
        setConversationId(detail.conversation.id);
        setHistory(detail.messages as ConversationMessage[]);
      })
      .catch(() => {
        // Chat can still start a new conversation if history is temporarily unavailable.
      });

    return () => {
      active = false;
    };
  }, []);

  const selected = useMemo(
    () => models.find((item) => item.provider + ":" + item.model === selectedKey),
    [models, selectedKey],
  );

  async function openConversation(id: number) {
    setLoadingConversation(true);
    setError("");
    setAnswer(null);
    try {
      const response = await fetch("/api/chat/conversations/" + id, { cache: "no-store" });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not load conversation");
      setConversationId(id);
      setHistory(result.messages as ConversationMessage[]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Conversation unavailable");
    } finally {
      setLoadingConversation(false);
    }
  }

  function startNewConversation() {
    setConversationId(null);
    setHistory([]);
    setAnswer(null);
    setPrompt("");
    setError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      setError("No fully configured model is available yet.");
      return;
    }
    const message = prompt.trim();
    if (!message) {
      setError("Enter a message first.");
      return;
    }
    setSending(true);
    setError("");
    setAnswer(null);
    try {
      const response = await fetch("/api/chat/completions", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          provider: selected.provider,
          model: selected.model,
          messages: [{ role: "user", content: message }],
          conversation_id: conversationId ?? undefined,
          max_tokens: 512,
          idempotency_key: createIdempotencyKey(),
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "AI request failed");
      const completed = result as ChatResult;
      const now = new Date().toISOString();
      setConversationId(completed.conversation_id);
      setHistory((current) => [
        ...current,
        {
          id: -Date.now(),
          role: "user",
          content: message,
          provider: null,
          model: null,
          prompt_tokens: null,
          completion_tokens: null,
          credits_charged: 0,
        },
        {
          id: -Date.now() - 1,
          role: "assistant",
          content: completed.content,
          provider: completed.provider,
          model: completed.model,
          prompt_tokens: completed.prompt_tokens,
          completion_tokens: completed.completion_tokens,
          credits_charged: completed.credits_charged,
        },
      ]);
      setConversations((current) => {
        const existing = current.find((item) => item.id === completed.conversation_id);
        const summary: ConversationSummary = existing
          ? { ...existing, updated_at: now }
          : {
              id: completed.conversation_id,
              title: message.slice(0, 157) || "New conversation",
              created_at: now,
              updated_at: now,
            };
        return [summary, ...current.filter((item) => item.id !== completed.conversation_id)];
      });
      setAnswer(completed);
      setPrompt("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "AI request failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="chat-panel" id="chat">
      <div className="chat-heading">
        <div>
          <span className="eyebrow">PREPAID AI WORKSPACE</span>
          <h2>AI Chat</h2>
          <p>Conversation history is private to your account. Credits are reserved before provider calls.</p>
        </div>
        <button className="account-button secondary" type="button" onClick={startNewConversation} disabled={sending}>
          New conversation
        </button>
      </div>

      {conversations.length > 0 ? (
        <label className="chat-conversation-select">
          Conversation history
          <select
            value={conversationId ?? ""}
            disabled={loadingConversation || sending}
            onChange={(event) => {
              if (event.target.value) void openConversation(Number(event.target.value));
            }}
          >
            {conversations.map((item) => (
              <option key={item.id} value={item.id}>{item.title}</option>
            ))}
          </select>
        </label>
      ) : null}

      <div className="chat-history" aria-live="polite">
        {history.length ? history.map((item) => (
          <article className={"chat-message " + item.role} key={item.id}>
            <small>{item.role === "user" ? "YOU" : (item.provider || "AI").toUpperCase()}</small>
            <p>{item.content}</p>
          </article>
        )) : (
          <div className="chat-empty">
            {loadingConversation ? "Loading conversation…" : "Start a new conversation by sending a message."}
          </div>
        )}
      </div>

      {loadingModels ? (
        <div className="chat-empty">Loading verified model catalogue…</div>
      ) : models.length === 0 ? (
        <div className="chat-empty">
          No model is enabled yet. An administrator must configure server-side provider credentials and a verified PKR input/output rate pair.
        </div>
      ) : (
        <form className="chat-form" onSubmit={submit}>
          <label>
            Model
            <select value={selectedKey} onChange={(event) => setSelectedKey(event.target.value)}>
              {models.map((item) => (
                <option key={item.provider + ":" + item.model} value={item.provider + ":" + item.model}>
                  {item.provider} · {item.model}
                </option>
              ))}
            </select>
          </label>
          <label>
            Your message
            <textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              maxLength={32768}
              rows={4}
              placeholder="Ask a question…"
              required
            />
          </label>
          <div className="chat-actions">
            <small>Maximum response: 512 tokens · Your balance must cover the estimated maximum cost.</small>
            <button className="account-button" type="submit" disabled={sending || loadingConversation || !selected}>
              {sending ? "Thinking…" : "Send message"}
            </button>
          </div>
        </form>
      )}

      {error ? <p className="chat-error" role="alert">{error}</p> : null}
      {answer ? (
        <div className="chat-accounting">
          <span>Charged: <strong>{answer.credits_charged} credits</strong></span>
          <span>Released: <strong>{answer.credits_refunded} credits</strong></span>
          <span>Balance: <strong>{answer.balance} credits</strong></span>
        </div>
      ) : null}
    </section>
  );
}
