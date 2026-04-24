"use client";

import { useState, useEffect, useRef } from "react";
import "./globals.css";

// ─── Config ────────────────────────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEBATE_STEPS = [
  { label: "Negotiating roles", sub: "Each model proposes its own lens for this prompt" },
  { label: "Round 1 — Independent answers", sub: "Models answer without seeing each other" },
  { label: "Round 2 — Critiques & revisions", sub: "Models challenge and improve each other" },
  { label: "Synthesizing final answer", sub: "Strongest points combined into one response" },
];

// Cumulative delays in ms — tuned to realistic backend timing
const STEP_DELAYS = [0, 4000, 13000, 22000];

const CONFIDENCE_STYLE = {
  High:   { bg: "#052e16", color: "#4ade80", border: "#166534" },
  Medium: { bg: "#431407", color: "#fb923c", border: "#9a3412" },
  Low:    { bg: "#450a0a", color: "#f87171", border: "#991b1b" },
};

const PROVIDER_COLOR = {
  OpenAI:      "#10a37f",
  "Mistral AI": "#ff7000",
  Meta:         "#0866ff",
};

const MODE_DESC = {
  cloud:   "Single model. Fast, direct answers.",
  council: "Three models from different AI companies answer side by side.",
  debate:  "Role negotiation → parallel debate → auditable synthesis. ~30s, highest quality.",
};

// ─── Main Component ─────────────────────────────────────────────────────────
export default function Page() {
  const [prompt, setPrompt]       = useState("");
  const [mode, setMode]           = useState("cloud");
  const [answer, setAnswer]       = useState(null);
  const [smart, setSmart]         = useState(null);
  const [error, setError]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [debateStep, setDebateStep] = useState(-1);
  const [expanded, setExpanded]   = useState({});
  const [copied, setCopied]       = useState(false);
  const stepTimers = useRef([]);

  // Ctrl/Cmd + Enter to send
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !loading && prompt.trim()) {
        handleSend();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [prompt, mode, loading]);

  function startDebateSteps() {
    clearDebateSteps();
    STEP_DELAYS.forEach((delay, i) => {
      const t = setTimeout(() => setDebateStep(i), delay);
      stepTimers.current.push(t);
    });
  }

  function clearDebateSteps() {
    stepTimers.current.forEach(clearTimeout);
    stepTimers.current = [];
    setDebateStep(-1);
  }

  // ─── API calls ─────────────────────────────────────────────────────────

  async function analyzeSmart() {
    if (!prompt.trim()) { setError("Please write a prompt first."); return; }
    setError(""); setAnswer(null); setSmart(null); setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/chat/smart/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Smart analysis failed");
      setSmart(data);
      setMode(data.suggested_mode);
    } catch (e) {
      setError(e.message || "Smart analysis failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(overrideMode) {
    const m = overrideMode || mode;
    if (!prompt.trim()) { setError("Please write a prompt first."); return; }

    setError(""); setAnswer(null); setSmart(null);
    setExpanded({}); setLoading(true);
    if (m === "debate") startDebateSteps();

    const urls = {
      cloud:   `${API_BASE}/chat/cloud`,
      council: `${API_BASE}/chat/council`,
      debate:  `${API_BASE}/chat/council/debate`,
    };

    try {
      const res = await fetch(urls[m], {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setAnswer(data);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setLoading(false);
      clearDebateSteps();
    }
  }

  function copyAnswer() {
    const text = answer?.final_answer || answer?.answer || JSON.stringify(answer, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function toggle(key) {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  }

  // ─── Sub-components ────────────────────────────────────────────────────

  function ModelCard({ modelId, data, role }) {
    if (!data) return null;
    const pc = PROVIDER_COLOR[data.provider] || "#475569";
    return (
      <div className="modelCard">
        <div className="modelCardHeader">
          <span className="modelName">{data.label || modelId}</span>
          <div className="modelBadges">
            {data.provider && (
              <span
                className="badge providerBadge"
                style={{ background: pc + "20", color: pc, borderColor: pc + "40" }}
              >
                {data.provider}
              </span>
            )}
            {role && <span className="badge roleBadge">{role}</span>}
          </div>
        </div>
        {data.error ? (
          <p className="modelError">
            ⚠ {typeof data.error === "string" ? data.error : "An error occurred"}
          </p>
        ) : (
          <p className="modelText">{data.answer || "No response"}</p>
        )}
      </div>
    );
  }

  function Collapsible({ id, title, count, children }) {
    const isOpen = expanded[id];
    return (
      <div className="collapsible">
        <button className="collapsibleTrigger" onClick={() => toggle(id)}>
          <span className="collapsibleTitle">{title}</span>
          <span className="collapsibleMeta">
            {count} model{count !== 1 ? "s" : ""}&nbsp;
            <span className="chevron">{isOpen ? "▲" : "▼"}</span>
          </span>
        </button>
        {isOpen && <div className="collapsibleBody">{children}</div>}
      </div>
    );
  }

  // ─── Answer renderers ──────────────────────────────────────────────────

  function renderCloud() {
    return <p className="answerText">{answer.answer}</p>;
  }

  function renderCouncil() {
    return (
      <div className="councilGrid">
        {Object.entries(answer.answer || {}).map(([id, data]) => (
          <ModelCard key={id} modelId={id} data={data} />
        ))}
      </div>
    );
  }

  function renderDebate() {
    const roles = answer.round0_roles || {};
    const r1    = answer.round1 || {};
    const r2    = answer.round2 || {};
    const conf  = answer.confidence;
    const cs    = CONFIDENCE_STYLE[conf] || CONFIDENCE_STYLE.Medium;

    return (
      <div className="debateLayout">

        {/* Round 0 — Role cards */}
        {Object.keys(roles).length > 0 && (
          <div className="debateSection">
            <div className="debateSectionLabel">Round 0 — Role Negotiation</div>
            <div className="rolesRow">
              {Object.entries(roles).map(([id, role]) => {
                const m  = r1[id];
                const pc = PROVIDER_COLOR[m?.provider] || "#64748b";
                return (
                  <div key={id} className="roleCard">
                    <span className="roleCardProvider" style={{ color: pc }}>
                      {m?.provider || "Unknown"}
                    </span>
                    <span className="roleCardName">{m?.label || id}</span>
                    <span className="roleCardRole">{role}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Final answer — most prominent */}
        <div className="finalSection">
          <div className="finalSectionHeader">
            <span className="debateSectionLabel">Final Synthesized Answer</span>
            {conf && (
              <span
                className="confBadge"
                style={{ background: cs.bg, color: cs.color, borderColor: cs.border }}
              >
                {conf} Confidence
              </span>
            )}
          </div>
          {answer.confidence_reason && (
            <p className="confReason">{answer.confidence_reason}</p>
          )}
          <p className="finalText">{answer.final_answer}</p>
        </div>

        {/* Disagreements & Consensus */}
        {(answer.disagreements?.length > 0 || answer.consensus_points?.length > 0) && (
          <div className="insightsRow">
            {answer.disagreements?.length > 0 && (
              <div className="insightBox insightBox--disagree">
                <div className="insightTitle">⚡ Points of Disagreement</div>
                <ul className="insightList">
                  {answer.disagreements.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              </div>
            )}
            {answer.consensus_points?.length > 0 && (
              <div className="insightBox insightBox--consensus">
                <div className="insightTitle">✓ Points of Consensus</div>
                <ul className="insightList">
                  {answer.consensus_points.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Collapsible round sections */}
        <Collapsible id="r1" title="Round 1 — Independent Answers" count={Object.keys(r1).length}>
          {Object.entries(r1).map(([id, data]) => (
            <ModelCard key={id} modelId={id} data={data} role={roles[id]} />
          ))}
        </Collapsible>

        <Collapsible id="r2" title="Round 2 — Critiques & Revisions" count={Object.keys(r2).length}>
          {Object.entries(r2).map(([id, data]) => (
            <ModelCard key={id} modelId={id} data={data} role={roles[id]} />
          ))}
        </Collapsible>

      </div>
    );
  }

  function renderAnswer() {
    if (!answer) return null;
    if (answer.mode === "cloud")          return renderCloud();
    if (answer.mode === "council")        return renderCouncil();
    if (answer.mode === "council_debate") return renderDebate();
    return <pre style={{ whiteSpace: "pre-wrap", fontSize: "13px" }}>{JSON.stringify(answer, null, 2)}</pre>;
  }

  // ─── Loading states ────────────────────────────────────────────────────

  function renderLoading() {
    if (!loading) return null;

    if (debateStep >= 0) {
      return (
        <div className="loadingBox">
          <div className="stepsContainer">
            {DEBATE_STEPS.map((step, i) => {
              const state = i < debateStep ? "done" : i === debateStep ? "active" : "pending";
              return (
                <div key={i} className={`step step--${state}`}>
                  <div className="stepDot">
                    {state === "done" ? "✓" : i + 1}
                  </div>
                  <div className="stepInfo">
                    <div className="stepLabel">{step.label}</div>
                    <div className="stepSub">{step.sub}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return (
      <div className="loadingBox loadingBox--simple">
        <div className="spinner" />
        <span className="loadingText">Thinking...</span>
      </div>
    );
  }

  // ─── Smart suggestion ──────────────────────────────────────────────────

  function renderSmart() {
    if (!smart) return null;
    const modeAccent = { cloud: "#3b82f6", council: "#8b5cf6", debate: "#f59e0b" };
    const accent = modeAccent[smart.suggested_mode] || "#3b82f6";
    const signals = (smart.matches?.[smart.suggested_mode] || []).slice(0, 5);
    const others  = ["cloud", "council", "debate"].filter(m => m !== smart.suggested_mode);

    return (
      <div className="smartBox">
        <div className="smartHeader">
          <span className="smartTitle">Smart Recommendation</span>
          <span className="modeBadge" style={{ background: accent + "22", color: accent, borderColor: accent + "55" }}>
            {smart.suggested_mode}
          </span>
        </div>
        {signals.length > 0 && (
          <div className="signalsRow">
            <span className="signalsLabel">Detected signals:</span>
            {signals.map(s => (
              <span key={s} className="signal">{s}</span>
            ))}
          </div>
        )}
        <div className="smartActions">
          <button
            className="recommendBtn"
            style={{ background: accent }}
            onClick={() => handleSend(smart.suggested_mode)}
          >
            Use {smart.suggested_mode} (recommended)
          </button>
          {others.map(m => (
            <button key={m} className="altBtn" onClick={() => handleSend(m)}>
              Use {m}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ─── Render ────────────────────────────────────────────────────────────

  const activeAccent = { cloud: "#3b82f6", council: "#8b5cf6", debate: "#f59e0b" }[mode];

  return (
    <main className="page">
      <section className="card">

        {/* Header */}
        <header className="cardHeader">
          <div>
            <h1 className="title">AI Council</h1>
            <p className="subtitle">Multi-model reasoning. Less bias, better answers.</p>
          </div>
          <div className="headerDot" />
        </header>

        {/* Mode tabs */}
        <div className="modeRow">
          {["cloud", "council", "debate"].map(m => {
            const acc = { cloud: "#3b82f6", council: "#8b5cf6", debate: "#f59e0b" }[m];
            return (
              <button
                key={m}
                className={`modeBtn ${mode === m ? "modeBtn--active" : ""}`}
                style={mode === m ? { borderColor: acc, color: acc } : {}}
                onClick={() => { setMode(m); setSmart(null); }}
              >
                {m === "cloud" && "⚡ Cloud"}
                {m === "council" && "🏛 Council"}
                {m === "debate" && "⚔️ Debate"}
              </button>
            );
          })}
        </div>
        <p className="modeDesc">{MODE_DESC[mode]}</p>

        {/* Textarea */}
        <div className="inputWrapper">
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Write your prompt here..."
            disabled={loading}
            style={{ borderColor: prompt.length > 0 ? activeAccent + "55" : undefined }}
          />
          <span className={`charCount ${prompt.length > 800 ? "charCount--warn" : ""}`}>
            {prompt.length}
          </span>
        </div>

        {/* Actions */}
        <div className="actionRow">
          <button
            className="sendBtn"
            style={{ background: activeAccent }}
            onClick={() => handleSend()}
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Working..." : `Send (${mode})`}
          </button>
          <button
            className="smartBtn"
            onClick={analyzeSmart}
            disabled={loading || !prompt.trim()}
          >
            🧠 Smart Analyze
          </button>
        </div>
        <p className="hint">Ctrl + Enter to send</p>

        {/* Error */}
        {error && <div className="error">⚠ {error}</div>}

        {/* Loading */}
        {renderLoading()}

        {/* Smart suggestion */}
        {renderSmart()}

        {/* Answer */}
        {answer && !loading && (
          <div className="answerBox">
            <div className="answerBoxHeader">
              <h2 className="answerTitle">Answer</h2>
              <button className="copyBtn" onClick={copyAnswer}>
                {copied ? "✓ Copied" : "Copy"}
              </button>
            </div>
            {renderAnswer()}
          </div>
        )}

      </section>
    </main>
  );
}