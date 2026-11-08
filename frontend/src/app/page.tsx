"use client";

import { useEffect, useState } from "react";
import AuthPanel from "../components/auth-panel";

type Provider = {
  id: string;
  name: string;
  credential_configured: boolean;
  capabilities_status: string;
  integration_status: string;
};

type ProviderResponse = { items: Provider[]; count: number };

export default function HomePage() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [providerError, setProviderError] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/health")
      .then((response) => {
        if (!response.ok) throw new Error("API health check failed");
        if (active) setApiStatus("online");
      })
      .catch(() => {
        if (active) setApiStatus("offline");
      });

    fetch("/api/v1/providers")
      .then(async (response) => {
        if (!response.ok) throw new Error("Provider catalogue unavailable");
        return (await response.json()) as ProviderResponse;
      })
      .then((data) => {
        if (active) setProviders(data.items);
      })
      .catch((error: Error) => {
        if (active) setProviderError(error.message);
      });

    return () => {
      active = false;
    };
  }, []);

  const statusLabel = apiStatus === "checking" ? "Checking API" : apiStatus === "online" ? "API connected" : "API offline";

  return (
    <main className="shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="AI Power Hub home">
          <span className="brand-mark">AI</span>
          <span><strong>POWER HUB</strong><small>One platform. All AI.</small></span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="#overview">Overview</a>
        <a className="nav-item" href="#providers">AI Providers</a>
        <a className="nav-item" href="#capabilities">Capabilities</a>
        <div className="sidebar-note">
          <span className="eyebrow">EARLY FOUNDATION</span>
          <p>Core services are being built and verified in public.</p>
        </div>
        <div className="sidebar-footer">AI POWER HUB · 0.2.0</div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div><span className="eyebrow">YOUR AI WORKSPACE</span><h1>Overview</h1></div>
          <div className={`status-pill ${apiStatus}`}><span className="status-dot" />{statusLabel}</div>
        </header>
        <AuthPanel />

        <section className="hero" id="overview">
          <div className="hero-copy">
            <span className="eyebrow light">WELCOME TO AI POWER HUB</span>
            <h2>All your AI capabilities.<br /><em>One connected workspace.</em></h2>
            <p>A unified platform for AI chat, creation, research, coding, and business workflows. Features will become available as real integrations pass testing.</p>
            <a className="primary-link" href="#capabilities">Explore platform <span aria-hidden="true">→</span></a>
          </div>
          <div className="hero-orbit" aria-hidden="true"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><div className="orbit-core">AI<span>+</span></div><i className="orbit-node node-one" /><i className="orbit-node node-two" /><i className="orbit-node node-three" /></div>
        </section>

        <section className="metrics" aria-label="Platform summary">
          <article className="metric-card"><span className="metric-label">AI PROVIDERS CATALOGUED</span><strong>{providers.length || "—"}</strong><small>Metadata only · adapters pending</small></article>
          <article className="metric-card"><span className="metric-label">API STATUS</span><strong className={apiStatus === "online" ? "metric-good" : ""}>{apiStatus === "online" ? "Online" : apiStatus === "offline" ? "Offline" : "…"}</strong><small>Live health endpoint</small></article>
          <article className="metric-card"><span className="metric-label">ENTRY PLAN TARGET</span><strong>Rs. 100</strong><small>Proposed monthly starting price</small></article>
        </section>

        <section className="section" id="providers">
          <div className="section-heading"><div><span className="eyebrow">INTEGRATION LAYER</span><h2>AI provider registry</h2></div><span className="section-caption">Live configuration status</span></div>
          {providerError ? <div className="notice">{providerError}. Start the backend and refresh this page.</div> : null}
          <div className="provider-grid">
            {providers.length ? providers.map((provider) => (
              <article className="provider-card" key={provider.id}>
                <div className="provider-icon">{provider.name.slice(0, 1)}</div>
                <div className="provider-info"><strong>{provider.name}</strong><small>{provider.credential_configured ? "Credential detected" : "Credential not configured"}</small></div>
                <span className="pending-tag">Adapter pending</span>
              </article>
            )) : !providerError ? <div className="empty-state">Loading provider registry…</div> : null}
          </div>
        </section>

        <section className="section" id="capabilities">
          <div className="section-heading"><div><span className="eyebrow">PRODUCT ROADMAP</span><h2>Explore capabilities</h2></div><span className="section-caption">Availability is shown honestly</span></div>
          <div className="capability-grid">
            {[
              ["01", "AI Chat & Reasoning", "Unified model access", "In development"],
              ["02", "Image Studio", "Generate and edit images", "Planned"],
              ["03", "Video Studio", "Create AI-assisted video", "Planned"],
              ["04", "Audio & Voice", "Speech, transcription, and voice", "Planned"],
              ["05", "Coding Assistant", "Build, explain, and review code", "Planned"],
              ["06", "Research & Documents", "Search and understand information", "Planned"],
              ["07", "AI Agents", "Controlled multi-step workflows", "Planned"],
              ["08", "Business Automation", "Operational AI workflows", "Planned"],
            ].map(([number, title, description, state]) => (
              <article className="capability-card" key={number}>
                <span className="capability-number">{number}</span>
                <div><strong>{title}</strong><p>{description}</p></div>
                <span className="roadmap-state">{state}</span>
              </article>
            ))}
          </div>
        </section>

        <footer className="footer"><span>AI POWER HUB</span><span>Built in public · Production readiness not yet claimed</span></footer>
      </section>
    </main>
  );
}
