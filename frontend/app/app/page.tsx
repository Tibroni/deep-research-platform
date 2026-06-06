"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import AppNav from "@/components/AppNav";
import { getApiBase } from "@/lib/config";

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

  const API_BASE = getApiBase();

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
    <>
      <AppNav title="Dashboard" />

      <div className="app-page">
        <header className="app-page__header">
          <p className="app-eyebrow">Dashboard</p>
          <h1>Start a research investigation</h1>
          <p>
            Submit a question and the agent team will plan, search, verify, and
            draft a cited report. You approve the plan and final draft before
            publication.
          </p>
        </header>

        <section className="app-section glass-panel-glow">
          <p className="app-section__title">New investigation</p>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div>
              <label className="form-label" htmlFor="prompt">
                Research prompt
              </label>
              <textarea
                id="prompt"
                className="form-input"
                style={{ minHeight: "120px", resize: "vertical" }}
                placeholder="What topic or question would you like to investigate?"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", gap: "1.25rem", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div>
                <span className="form-label">Search depth</span>
                <div className="form-toggle-group">
                  <button
                    type="button"
                    className={depth === "basic" ? "form-button form-toggle" : "form-button-secondary form-toggle"}
                    onClick={() => setDepth("basic")}
                  >
                    Basic
                  </button>
                  <button
                    type="button"
                    className={depth === "deep" ? "form-button form-toggle" : "form-button-secondary form-toggle"}
                    onClick={() => setDepth("deep")}
                  >
                    Deep
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="form-button"
                style={{ marginLeft: "auto" }}
                disabled={loading || !prompt.trim()}
              >
                {loading ? "Starting..." : "Start Research"}
              </button>
            </div>
          </form>
        </section>

        <section className="app-section glass-panel">
          <p className="app-section__title">Previous investigations</p>

          {fetching ? (
            <div className="app-empty">Loading...</div>
          ) : jobs.length === 0 ? (
            <div className="app-empty">No investigations yet.</div>
          ) : (
            <div>
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="app-job-row"
                  onClick={() => router.push(`/research/${job.id}`)}
                >
                  <div>
                    <p className="app-job-row__title">{job.title}</p>
                    <p className="app-job-row__meta">
                      {new Date(job.created_at).toLocaleString()}
                    </p>
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
    </>
  );
}
