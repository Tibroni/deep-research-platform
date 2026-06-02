"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface ResearchJob {
  id: string;
  title: string;
  prompt: string;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const [prompt, setPrompt] = useState("");
  const [depth, setDepth] = useState("basic");
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const router = useRouter();

  // API base URL - can fall back to localhost
  const API_BASE = "http://localhost:8000/api";

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/research`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (e) {
      console.error("Failed to fetch jobs:", e);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // Poll for list updates every 5 seconds
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, depth }),
      });

      if (res.ok) {
        const data = await res.json();
        // Route directly to the new job's workspace!
        router.push(`/research/${data.job_id}`);
      } else {
        alert("Failed to start research job");
      }
    } catch (e) {
      console.error(e);
      alert("Error starting research task");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "pending":
      case "planning":
        return "badge-pending";
      case "executing":
        return "badge-running";
      case "awaiting_plan_approval":
      case "awaiting_final_approval":
        return "badge-paused";
      case "completed":
        return "badge-completed";
      case "failed":
        return "badge-failed";
      default:
        return "badge-pending";
    }
  };

  const formatStatusText = (status: string) => {
    return status.replace(/_/g, " ").toUpperCase();
  };

  return (
    <div style={{ maxWidth: "1200px", width: "100%", margin: "0 auto", padding: "40px 20px" }}>
      {/* Header Banner */}
      <header style={{ marginBottom: "50px", textAlign: "center" }}>
        <h1 style={{ 
          fontSize: "3rem", 
          marginBottom: "12px", 
          background: "linear-gradient(to right, #fff 30%, hsl(260, 85%, 65%) 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          fontWeight: 800
        }}>
          Deep Research Agent Platform
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "1.2rem", fontWeight: 400 }}>
          Durable, multi-agent automated investigations with human-in-the-loop controls.
        </p>
      </header>

      {/* Main Grid Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "40px" }}>
        
        {/* Input Card */}
        <section className="glass-panel-glow" style={{ padding: "30px" }}>
          <h2 style={{ fontSize: "1.5rem", marginBottom: "20px" }}>Initiate Research Investigation</h2>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: 500, color: "var(--text-secondary)" }}>
                Research Prompt / Core Question
              </label>
              <textarea
                className="form-input"
                style={{ minHeight: "120px", resize: "vertical" }}
                placeholder="What topic or question would you like to investigate in-depth? E.g., 'Analyze the current state of WebAssembly in edge computing in 2026'"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", gap: "20px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "0.9rem", color: "var(--text-secondary)", fontWeight: 500 }}>
                  Search Strategy depth
                </span>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    className={depth === "basic" ? "form-button" : "form-button-secondary"}
                    style={{ padding: "10px 20px", fontSize: "0.9rem" }}
                    onClick={() => setDepth("basic")}
                  >
                    ⚡ Basic (Fast)
                  </button>
                  <button
                    type="button"
                    className={depth === "deep" ? "form-button" : "form-button-secondary"}
                    style={{ padding: "10px 20px", fontSize: "0.9rem" }}
                    onClick={() => setDepth("deep")}
                  >
                    🔍 Deep (Thorough)
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="form-button"
                style={{ marginLeft: "auto", alignSelf: "flex-end", height: "46px", padding: "0 30px" }}
                disabled={loading || !prompt.trim()}
              >
                {loading ? "Launching Agents..." : "Start Research →"}
              </button>
            </div>
          </form>
        </section>

        {/* Previous Jobs List */}
        <section className="glass-panel" style={{ padding: "30px" }}>
          <h2 style={{ fontSize: "1.5rem", marginBottom: "20px" }}>Previous Investigations</h2>
          
          {fetching ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "40px" }}>
              Loading previous jobs...
            </div>
          ) : jobs.length === 0 ? (
            <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "40px" }}>
              No research investigations started yet. Submit a prompt above to launch your first run!
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px" }}>
              {jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => router.push(`/research/${job.id}`)}
                  className="glass-panel"
                  style={{
                    padding: "20px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    cursor: "pointer",
                    border: "1px solid hsla(220, 20%, 30%, 0.1)",
                    borderRadius: "12px",
                    background: "hsla(220, 12%, 14%, 0.35)",
                    transition: "var(--transition-smooth)"
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--border-glow)";
                    e.currentTarget.style.transform = "translateX(5px)";
                    e.currentTarget.style.background = "var(--card-bg-hover)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "hsla(220, 20%, 30%, 0.1)";
                    e.currentTarget.style.transform = "translateX(0)";
                    e.currentTarget.style.background = "hsla(220, 12%, 14%, 0.35)";
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>{job.title}</h3>
                    <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                      Investigation launched on: {new Date(job.created_at).toLocaleString()}
                    </span>
                  </div>
                  
                  <span className={`badge ${getStatusBadgeClass(job.status)}`}>
                    {formatStatusText(job.status)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
