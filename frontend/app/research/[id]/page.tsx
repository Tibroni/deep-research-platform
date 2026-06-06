"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import AppNav from "@/components/AppNav";
import { getApiBase, getWsBase } from "@/lib/config";

interface PlanItem {
  id: number;
  topic: string;
  queries: string[];
  completed: boolean;
}

interface SourceItem {
  id: string;
  title: string;
  url: string;
  snippet: string;
}

interface FactCheckItem {
  claim: string;
  source_id: string;
  status: string;
  notes: string;
}

export default function ResearchWorkspace() {
  const { id } = useParams() as { id: string };
  const router = useRouter();

  // State values from API & WS
  const [status, setStatus] = useState<string>("planning");
  const [prompt, setPrompt] = useState<string>("");
  const [title, setTitle] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [draftReport, setDraftReport] = useState<string>("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [factReport, setFactReport] = useState<FactCheckItem[]>([]);
  
  // Interactive UI values
  const [selectedSource, setSelectedSource] = useState<SourceItem | null>(null);
  const [feedback, setFeedback] = useState<string>("");
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [connected, setConnected] = useState<boolean>(false);

  const consoleEndRef = useRef<HTMLDivElement>(null);

  const API_BASE = getApiBase();
  const WS_BASE = getWsBase();

  // Fetch initial details
  const fetchJobDetails = async () => {
    try {
      const res = await fetch(`${API_BASE}/research/${id}`);
      if (res.ok) {
        const data = await res.json();
        setTitle(data.title);
        setPrompt(data.prompt);
        setStatus(data.status);
        setPlan(data.plan || []);
        setDraftReport(data.draft_report || "");
        setSources(data.sources || []);
        setFactReport(data.fact_checking_report || []);
        setLogs(data.logs || []);
      }
    } catch (e) {
      console.error("Failed to load job details:", e);
    }
  };

  // Connect WebSocket for real-time log and state broadcasts
  useEffect(() => {
    fetchJobDetails();

    const ws = new WebSocket(`${WS_BASE}/research/${id}`);
    
    ws.onopen = () => {
      setConnected(true);
      logger("WebSocket connection established");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "state_update") {
          setLogs(msg.logs || []);
          setPlan(msg.plan || []);
          setDraftReport(msg.draft_report || "");
          setSources(msg.sources || []);
          setFactReport(msg.fact_checking_report || []);
        } else if (msg.type === "status_update") {
          setStatus(msg.status);
          fetchJobDetails(); // Sync complete details
        }
      } catch (e) {
        console.error("WS parse error:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      logger("WebSocket connection lost, attempting reconnect in 3s...");
      setTimeout(() => {
        // Re-trigger useEffect connection loop
        fetchJobDetails();
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [id]);

  // Autoscroll terminal window on new logs
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const logger = (msg: string) => {
    setLogs((prev) => [...prev, `System: ${msg}`]);
  };

  // Handle plan approval
  const handleApprovePlan = async (approved: boolean) => {
    setSubmittingDecision(true);
    try {
      const res = await fetch(`${API_BASE}/research/${id}/approve-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved,
          feedback: approved ? null : feedback,
          plan: approved ? plan : null, // send the plan (in case user edited textboxes)
        }),
      });

      if (res.ok) {
        setStatus("executing");
        setFeedback("");
        fetchJobDetails();
      } else {
        alert("Failed to submit plan decision");
      }
    } catch (e) {
      console.error(e);
      alert("Error submitting plan decision");
    } finally {
      setSubmittingDecision(false);
    }
  };

  // Handle report approval
  const handleApproveReport = async (approved: boolean) => {
    setSubmittingDecision(true);
    try {
      const res = await fetch(`${API_BASE}/research/${id}/approve-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved,
          feedback: approved ? null : feedback,
        }),
      });

      if (res.ok) {
        setStatus("executing");
        setFeedback("");
        fetchJobDetails();
      } else {
        alert("Failed to submit report decision");
      }
    } catch (e) {
      console.error(e);
      alert("Error submitting report decision");
    } finally {
      setSubmittingDecision(false);
    }
  };

  // Render HTML nodes representing agent workflow state
  const renderFlowGraph = () => {
    const steps = [
      { name: "Planner", id: "planner_node", label: "PLAN" },
      { name: "Research", id: "research_node", label: "RETRIEVE" },
      { name: "Fact Checker", id: "fact_checker_node", label: "VERIFY" },
      { name: "Writer", id: "writer_node", label: "WRITE" },
      { name: "Reviewer", id: "reviewer_node", label: "REVIEW" }
    ];

    const getStepState = (stepId: string) => {
      // Completed checks
      if (status === "completed") return "completed";
      if (status === "failed") return "failed";
      
      // Node interrupts / pauses
      if (status === "awaiting_plan_approval" && stepId === "research_node") return "paused";
      if (status === "awaiting_final_approval" && stepId === "reviewer_node") return "paused";

      // Match running node status
      if (status === "planning" && stepId === "planner_node") return "active";
      
      // If we are executing, estimate based on log items or logs status
      if (status === "executing") {
        const lastLog = logs.length ? logs[logs.length - 1].toLowerCase() : "";
        if (lastLog.includes("planner")) return stepId === "planner_node" ? "active" : (stepId === "research_node" ? "pending" : "completed");
        if (lastLog.includes("research") || lastLog.includes("retrieval")) return stepId === "research_node" ? "active" : (stepId === "planner_node" ? "completed" : "pending");
        if (lastLog.includes("fact checker") || lastLog.includes("audit") || lastLog.includes("validation")) return stepId === "fact_checker_node" ? "active" : (["planner_node", "research_node"].includes(stepId) ? "completed" : "pending");
        if (lastLog.includes("writer") || lastLog.includes("report draft")) return stepId === "writer_node" ? "active" : (["planner_node", "research_node", "fact_checker_node"].includes(stepId) ? "completed" : "pending");
        if (lastLog.includes("reviewer") || lastLog.includes("editorial")) return stepId === "reviewer_node" ? "active" : "completed";
      }

      // Estimate order
      const stepIndex = steps.findIndex(s => s.id === stepId);
      if (status === "awaiting_plan_approval" && stepIndex === 0) return "completed";
      if (status === "awaiting_final_approval" && stepIndex < 4) return "completed";

      return "pending";
    };

    return (
      <div style={{ display: "flex", width: "100%", justifyContent: "space-between", alignItems: "center", margin: "20px 0 35px 0", padding: "10px 0" }}>
        {steps.map((step, idx) => {
          const state = getStepState(step.id);
          let color = "var(--text-muted)";
          let borderColor = "var(--border-color)";
          let pulseClass = "";
          
          if (state === "completed") {
            color = "var(--success)";
            borderColor = "var(--success)";
          } else if (state === "active") {
            color = "var(--primary-accent)";
            borderColor = "var(--primary-accent)";
            pulseClass = "node-pulse-active";
          } else if (state === "paused") {
            color = "var(--primary-accent)";
            borderColor = "var(--primary-accent)";
            pulseClass = "node-pulse-active";
          } else if (state === "failed") {
            color = "var(--danger)";
            borderColor = "var(--danger)";
          }

          return (
            <React.Fragment key={step.id}>
              {/* Step Circle */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px", position: "relative" }}>
                <div 
                  className={`glass-panel ${pulseClass}`}
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: `2px solid ${borderColor}`,
                    fontWeight: 700,
                    fontSize: "0.85rem",
                    color: color,
                    background: "var(--ds-zinc-950)",
                    transition: "var(--transition-smooth)",
                  }}
                >
                  {idx + 1}
                </div>
                <span style={{ fontSize: "0.75rem", fontWeight: 600, color: color, letterSpacing: "0.02em" }}>
                  {step.label}
                </span>
                <span style={{ fontSize: "0.6rem", color: "var(--text-muted)", marginTop: "-4px" }}>
                  {step.name}
                </span>
              </div>

              {/* Connector Arrow */}
              {idx < steps.length - 1 && (
                <div style={{ flex: 1, height: "2px", background: state === "completed" ? "var(--success)" : "var(--border-color)", margin: "0 10px", marginTop: "-20px", transition: "var(--transition-smooth)" }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  // Helper to parse citations e.g. [Source S1] or [S1] and render links
  const renderMarkdownWithCitations = (md: string) => {
    if (!md) return null;

    // Preprocess lines: remove empty lines that are sandwiched between table lines
    const rawLines = md.split("\n");
    const lines: string[] = [];
    for (let i = 0; i < rawLines.length; i++) {
      const current = rawLines[i].trim();
      if (current === "") {
        const prevIsTable = i > 0 && rawLines[i - 1].trim().startsWith("|");
        const nextIsTable = i < rawLines.length - 1 && rawLines[i + 1].trim().startsWith("|");
        if (prevIsTable && nextIsTable) {
          continue; // Skip the intermediate empty line
        }
      }
      lines.push(rawLines[i]);
    }

    let inList = false;
    let listItems: string[] = [];
    
    let inTable = false;
    let tableRows: string[][] = [];
    
    const elements: React.ReactNode[] = [];

    const flushList = (keyPrefix: number) => {
      if (listItems.length > 0) {
        elements.push(
          <ul key={`list-${keyPrefix}`} style={{ marginLeft: "20px", marginBottom: "16px" }}>
            {listItems.map((item, itemIdx) => (
              <li key={`li-${keyPrefix}-${itemIdx}`} style={{ marginBottom: "6px", color: "var(--text-secondary)" }}>
                {parseInlineText(item)}
              </li>
            ))}
          </ul>
        );
        listItems = [];
        inList = false;
      }
    };

    const flushTable = (keyPrefix: number) => {
      if (tableRows.length > 0) {
        // Delimiter row filter (e.g. |---|---|)
        const cleanRows = tableRows.filter(row => {
          const rowStr = row.join("").trim();
          return !/^[:\-\s]+$/.test(rowStr);
        });

        if (cleanRows.length > 0) {
          const header = cleanRows[0];
          const body = cleanRows.slice(1);

          elements.push(
            <div key={`table-container-${keyPrefix}`} style={{ overflowX: "auto", marginBottom: "20px" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", margin: "10px 0" }}>
                <thead>
                  <tr style={{ background: "var(--ds-zinc-900)" }}>
                    {header.map((col, cidx) => (
                      <th key={`th-${keyPrefix}-${cidx}`} style={{ padding: "10px 14px", border: "1px solid var(--border-color)", textAlign: "left", fontWeight: 600 }}>
                        {parseInlineText(col)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {body.map((row, ridx) => (
                    <tr key={`tr-${keyPrefix}-${ridx}`} style={{ background: ridx % 2 === 1 ? "rgba(255,255,255,0.02)" : "transparent" }}>
                      {row.map((col, cidx) => (
                        <td key={`td-${keyPrefix}-${ridx}-${cidx}`} style={{ padding: "10px 14px", border: "1px solid var(--border-color)", color: "var(--text-secondary)" }}>
                          {parseInlineText(col)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        tableRows = [];
        inTable = false;
      }
    };

    const parseInlineText = (text: string) => {
      // Replace bold text **text**
      const boldRegex = /\*\*(.*?)\*\*/g;
      
      // Match [Source S1](url) or [S1] citations
      // We map source string e.g. [Source S1] or [S1] or [1] to our sources mapping
      const citationRegex = /\[(Source\s+S\d+|S\d+)\]/g;
      
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      
      // Combine regex checks by manual scan
      // Let's check for citations first as they are most important
      while ((match = citationRegex.exec(text)) !== null) {
        const matchIndex = match.index;
        const fullMatch = match[0];
        const sourceLabel = match[1]; // S1, Source S1
        const sourceId = sourceLabel.includes("S") ? sourceLabel.substring(sourceLabel.indexOf("S")) : sourceLabel;
        
        // Add preceding text
        if (matchIndex > lastIndex) {
          parts.push(parseBoldText(text.substring(lastIndex, matchIndex)));
        }
        
        // Find matching source url
        const targetSource = sources.find(s => s.id === sourceId);
        
        if (targetSource) {
          parts.push(
            <a
              key={`cite-${matchIndex}`}
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setSelectedSource(targetSource);
              }}
              className="citation-link"
            >
              [{sourceId}]
            </a>
          );
        } else {
          parts.push(<span key={`cite-text-${matchIndex}`}>[{sourceLabel}]</span>);
        }
        
        lastIndex = citationRegex.lastIndex;
      }
      
      if (lastIndex < text.length) {
        parts.push(parseBoldText(text.substring(lastIndex)));
      }
      
      return parts.length ? parts : text;
    };

    const parseBoldText = (text: string) => {
      const parts = text.split(/\*\*/g);
      return parts.map((part, idx) => {
        if (idx % 2 === 1) {
          return <strong key={`bold-${idx}`} style={{ color: "var(--text-primary)", fontWeight: 600 }}>{part}</strong>;
        }
        return part;
      });
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();
      
      // Handle table rows
      if (trimmed.startsWith("|")) {
        flushList(idx);
        inTable = true;
        const cols = trimmed.split("|").slice(1, -1).map(c => c.trim());
        tableRows.push(cols);
        return;
      }

      // Non-table line triggers a flush of accumulated table rows
      flushTable(idx);

      // Handle empty lines
      if (!trimmed) {
        flushList(idx);
        return;
      }

      // Handle Headers
      if (trimmed.startsWith("### ")) {
        flushList(idx);
        elements.push(<h3 key={`h3-${idx}`} style={{ fontSize: "1.2rem", marginTop: "24px", marginBottom: "10px", fontWeight: 600 }}>{parseInlineText(trimmed.substring(4))}</h3>);
      } else if (trimmed.startsWith("## ")) {
        flushList(idx);
        elements.push(<h2 key={`h2-${idx}`} style={{ fontSize: "1.5rem", marginTop: "30px", marginBottom: "12px", borderBottom: "1px solid var(--border-color)", paddingBottom: "4px", fontWeight: 700 }}>{parseInlineText(trimmed.substring(3))}</h2>);
      } else if (trimmed.startsWith("# ")) {
        flushList(idx);
        elements.push(<h1 key={`h1-${idx}`} style={{ fontSize: "2rem", marginBottom: "20px", fontWeight: 800 }}>{parseInlineText(trimmed.substring(2))}</h1>);
      } 
      // Handle list items
      else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        inList = true;
        listItems.push(trimmed.substring(2));
      } 
      // Handle normal paragraphs
      else {
        flushList(idx);
        elements.push(
          <p key={`p-${idx}`} style={{ marginBottom: "14px", color: "var(--text-secondary)", fontSize: "1rem", lineHeight: 1.7 }}>
            {parseInlineText(line)}
          </p>
        );
      }
    });

    flushList(lines.length);
    flushTable(lines.length);
    return <div className="markdown-body">{elements}</div>;
  };

  return (
    <div className="workspace">
      <AppNav
        title={title || "Investigation"}
        trailing={
          <>
            <span className="workspace__status">
              <span className={`workspace__status-dot ${connected ? "workspace__status-dot--live" : "workspace__status-dot--off"}`} />
              {connected ? "Live" : "Offline"}
            </span>
            <span className={`badge ${status === "completed" ? "badge-completed" : status === "executing" ? "badge-running" : "badge-paused"}`}>
              {status.replace(/_/g, " ")}
            </span>
          </>
        }
      />

      <div className="workspace__split">
        <div className="workspace__sidebar">
          <p className="workspace__section-label">Agent graph</p>
          {renderFlowGraph()}

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem", marginTop: "1.5rem" }}>
            <p className="workspace__section-label" style={{ marginBottom: 0 }}>Console</p>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {logs.length} lines
            </span>
          </div>

          <div className="terminal-window" style={{ flex: 1, padding: "1rem", minHeight: "200px", maxHeight: "50vh", display: "flex", flexDirection: "column", gap: "6px" }}>
            {logs.map((log, idx) => (
              <div 
                key={idx} 
                style={{ 
                  color: log.startsWith("System:") ? "hsl(199, 89%, 70%)" : (log.startsWith("User:") ? "hsl(38, 92%, 75%)" : "hsl(120, 60%, 75%)") 
                }}
              >
                {log}
              </div>
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>

        <div className="workspace__main">
          <div className="workspace__content">
            
            {/* 1. Planning interruption phase */}
            {status === "awaiting_plan_approval" && (
              <div className="glass-panel workspace__alert">
                <h2>Plan approval required</h2>
                <p>
                  The Planner agent has proposed a research outline. Review the topics and
                  queries below. You can edit search keywords before approving.
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "30px" }}>
                  {plan.map((item, idx) => (
                    <div key={item.id} className="glass-panel" style={{ padding: "1rem", background: "var(--ds-zinc-950)" }}>
                      <div style={{ display: "flex", gap: "10px", alignItems: "center", marginBottom: "8px" }}>
                        <span className="workspace__plan-num">{item.id}</span>
                        <input
                          className="form-input"
                          style={{ padding: "8px 12px", fontSize: "0.95rem", flex: 1 }}
                          value={item.topic}
                          onChange={(e) => {
                            const newPlan = [...plan];
                            newPlan[idx].topic = e.target.value;
                            setPlan(newPlan);
                          }}
                        />
                      </div>
                      
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginLeft: "34px" }}>
                        <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600 }}>Target Queries:</label>
                        {item.queries.map((query, queryIdx) => (
                          <input
                            key={queryIdx}
                            className="form-input"
                            style={{ padding: "6px 12px", fontSize: "0.85rem", background: "rgba(0,0,0,0.15)" }}
                            value={query}
                            onChange={(e) => {
                              const newPlan = [...plan];
                              newPlan[idx].queries[queryIdx] = e.target.value;
                              setPlan(newPlan);
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "12px", borderTop: "1px solid var(--border-color)", paddingTop: "20px" }}>
                  <label style={{ fontWeight: 600, color: "var(--text-secondary)", fontSize: "0.95rem" }}>
                    Add revision instruction feedback (optional, required if rejecting plan):
                  </label>
                  <textarea
                    className="form-input"
                    placeholder="Enter instructions for what queries to add, modify or delete..."
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                  />
                  
                  <div style={{ display: "flex", gap: "12px", marginTop: "10px" }}>
                    <button
                      className="form-button"
                      disabled={submittingDecision}
                      onClick={() => handleApprovePlan(true)}
                    >
                      {submittingDecision ? "Submitting..." : "✓ Approve Plan & Execute Search"}
                    </button>
                    
                    <button
                      className="form-button-secondary form-button-secondary--danger"
                      disabled={submittingDecision || !feedback.trim()}
                      onClick={() => handleApprovePlan(false)}
                    >
                      {submittingDecision ? "Submitting..." : "✗ Reject & Plan Revision"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Review report draft interruption phase */}
            {status === "awaiting_final_approval" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                <div className="glass-panel workspace__alert">
                  <h2>Report approval required</h2>
                  <p>
                    The Writer has drafted the report and the Fact Checker has audited
                    the claims. Review the draft below.
                  </p>
                  
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
                    <textarea
                      className="form-input"
                      style={{ minHeight: "80px" }}
                      placeholder="Add revision commands (e.g., 'Elaborate more on section 3, add more detail about gRPC...')"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                    />
                    <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                      <button className="form-button" onClick={() => handleApproveReport(true)} disabled={submittingDecision}>
                        {submittingDecision ? "Approving..." : "✓ Approve & Finalize Report"}
                      </button>
                      <button className="form-button-secondary form-button-secondary--danger" onClick={() => handleApproveReport(false)} disabled={submittingDecision || !feedback.trim()}>
                        {submittingDecision ? "Submitting..." : "✗ Request Modifications"}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="glass-panel" style={{ padding: "2.5rem" }}>
                  {renderMarkdownWithCitations(draftReport)}
                </div>
              </div>
            )}

            {/* 3. Executing/Running placeholder */}
            {(status === "planning" || status === "executing") && (
              <div className="workspace__empty-state">
                <div className="workspace__spinner" />
                <div>
                  <h2>Agents running</h2>
                  <p>
                    The agent team is working through the investigation. Watch the
                    console on the left for status updates.
                  </p>
                </div>
              </div>
            )}

            {/* 4. Complete final view */}
            {(status === "completed" || (status === "failed" && draftReport)) && (
              <div className="glass-panel" style={{ padding: "2.5rem 3rem" }}>
                {renderMarkdownWithCitations(draftReport)}
              </div>
            )}

            {status === "failed" && !draftReport && (
              <div className="glass-panel workspace__alert">
                <h2>Investigation failed</h2>
                <p>
                  The agent team encountered an error. Review the console logs on the
                  left for details.
                </p>
                <button className="form-button" onClick={() => router.push("/app")}>
                  Return to Dashboard
                </button>
              </div>
            )}

          </div>

          {/* Source popup panel sidebar */}
          {selectedSource && (
            <div className="source-panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="badge badge-accent">Citation {selectedSource.id}</span>
                <button className="source-panel__close" onClick={() => setSelectedSource(null)} aria-label="Close">
                  ×
                </button>
              </div>

              <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                  {selectedSource.title}
                </h3>
                <a
                  href={selectedSource.url}
                  target="_blank"
                  rel="noreferrer"
                  className="source-panel__url"
                >
                  {selectedSource.url}
                </a>
              </div>

              <div style={{ flex: 1, borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                <p className="form-label">Retrieved passage</p>
                <p className="source-panel__snippet">
                  {selectedSource.snippet || "No snippet text recorded."}
                </p>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
