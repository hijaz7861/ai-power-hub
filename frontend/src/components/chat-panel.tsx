"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type ChatModel = {
  provider: "openai" | "mistral";
  model: string;
  credential_configured: boolean;
};

type ChatResult = {
  request_id: number;
  provider: string;
  model: string;
  content: string;
  prompt_tokens: number;
  completion_tokens: number;
  credits_charged: number;
  credits_refunded: number;
  balance: number;
};

export default function ChatPanel() {
  const [models, setModels] = useState<ChatModel[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState<ChatResult | null>(null);
  const [error, setError] = useState("");
  const [loadingModels, setLoadingModels] = useState(true);
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
    return () => {
      active = false;
    };
  }, []);

  const selected = useMemo(
    () => models.find((item) => item.provider + ":" + item.model === selectedKey),
    [models, selectedKey],
  );

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      setError("No fully configured model is available yet.");
      return;
    }
    if (!prompt.trim()) {
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
          messages: [{ role: "user", content: prompt.trim() }],
          max_tokens: 512,
          idempotency_key: crypto.randomUUID(),
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "AI request failed");
      setAnswer(result as ChatResult);
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
          <p>Credits are reserved before the provider call and settled from reported token usage.</p>
        </div>
        <span className="chat-mode">Metered · secure</span>
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
              rows={5}
              placeholder="Ask a question…"
              required
            />
          </label>
          <div className="chat-actions">
            <small>Maximum response: 512 tokens · Your balance must cover the estimated maximum cost.</small>
            <button className="account-button" type="submit" disabled={sending || !selected}>
              {sending ? "Thinking…" : "Send message"}
            </button>
          </div>
        </form>
      )}

      {error ? <p className="chat-error" role="alert">{error}</p> : null}
      {answer ? (
        <div className="chat-answer">
          <div className="chat-answer-meta">
            <strong>{answer.provider} · {answer.model}</strong>
            <span>{answer.prompt_tokens + answer.completion_tokens} tokens</span>
          </div>
          <p>{answer.content}</p>
          <div className="chat-accounting">
            <span>Charged: <strong>{answer.credits_charged} credits</strong></span>
            <span>Released: <strong>{answer.credits_refunded} credits</strong></span>
            <span>Balance: <strong>{answer.balance} credits</strong></span>
          </div>
        </div>
      ) : null}
    </section>
  );
}
