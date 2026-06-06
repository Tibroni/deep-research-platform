"use client";

import { useEffect } from "react";
import FloatingNav from "@/components/landing/FloatingNav";
import MagneticButton from "@/components/landing/MagneticButton";
import WorkflowAccordion from "@/components/landing/WorkflowAccordion";
import "./landing.css";

const STEPS = [
  {
    title: "Submit a question",
    description:
      "Enter a research prompt on the dashboard. Choose basic or deep search depth.",
  },
  {
    title: "Review the plan",
    description:
      "The Planner agent proposes topics and search queries. You approve or edit them before any web search runs.",
  },
  {
    title: "Research and verify",
    description:
      "The Researcher searches the web and scrapes sources. The Fact Checker cross-references claims against the raw text.",
  },
  {
    title: "Draft and review",
    description:
      "The Writer produces a Markdown report with citations. The Reviewer evaluates coverage and may request another pass.",
  },
  {
    title: "Approve the report",
    description:
      "You read the draft and approve it or send feedback. The finished report is saved to the database.",
  },
];

const AGENTS = [
  { name: "Planner", role: "Breaks the question into topics and search queries." },
  { name: "Researcher", role: "Runs web searches, scrapes pages, and extracts findings." },
  { name: "Fact Checker", role: "Checks claims against source text and flags contradictions." },
  { name: "Writer", role: "Drafts the report in Markdown with inline citations." },
  { name: "Reviewer", role: "Assesses report quality and routes to revision or completion." },
];

const STACK = [
  { label: "Backend", value: "FastAPI, LangGraph, SQLAlchemy" },
  { label: "Frontend", value: "Next.js with live WebSocket updates" },
  { label: "Search", value: "Tavily or DuckDuckGo, with page scraping" },
  { label: "Storage", value: "PostgreSQL or local SQLite" },
];

export default function LandingPage() {
  useEffect(() => {
    document.body.classList.add("landing-page-active");
    return () => document.body.classList.remove("landing-page-active");
  }, []);

  return (
    <div className="landing">
      <FloatingNav />

      <section className="landing-hero">
        <div className="landing-hero__inner">
          <p className="landing-eyebrow">Deep Research Platform</p>
          <h1 className="landing-hero__title">
            Automated research
            <span>with human oversight</span>
          </h1>
          <p className="landing-hero__desc">
            A multi-agent system that plans investigations, searches the web, verifies
            claims against sources, and writes cited reports. Workflows pause at two
            approval points so you stay in control.
          </p>
          <MagneticButton href="/app">Launch App</MagneticButton>
        </div>
      </section>

      <section id="how-it-works" className="landing-panel">
        <div className="landing-panel__inner">
          <p className="landing-eyebrow">Workflow</p>
          <h2 className="landing-heading">How it works</h2>
          <WorkflowAccordion steps={STEPS} />
        </div>
      </section>

      <section id="agents" className="landing-section">
        <div className="landing-section__inner">
          <p className="landing-eyebrow">Architecture</p>
          <h2 className="landing-heading">Agents</h2>
          <p className="landing-lead">
            Five agents run in sequence via a LangGraph workflow. State is checkpointed
            to SQLite or PostgreSQL so runs survive restarts.
          </p>
          <ul className="landing-agents">
            {AGENTS.map((agent) => (
              <li key={agent.name} className="landing-agents__row">
                <span className="landing-agents__name">{agent.name}</span>
                <span className="landing-agents__role">{agent.role}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="stack" className="landing-panel">
        <div className="landing-panel__inner">
          <p className="landing-eyebrow">Infrastructure</p>
          <h2 className="landing-heading">Stack</h2>
          <dl className="landing-stack">
            {STACK.map((item) => (
              <div key={item.label} className="landing-stack__item">
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <footer className="landing-footer">
        <MagneticButton href="/app" variant="secondary">
          Launch App
        </MagneticButton>
      </footer>
    </div>
  );
}
