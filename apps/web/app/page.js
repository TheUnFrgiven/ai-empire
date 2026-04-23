"use client";

import { useState } from "react";
import "./globals.css";

export default function Page() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("cloud");
  const [answer, setAnswer] = useState(null);
  const [smartSuggestion, setSmartSuggestion] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const endpoints = {
    cloud: "http://localhost:8000/chat/cloud",
    council: "http://localhost:8000/chat/council",
    debate: "http://localhost:8000/chat/council/debate"
  };

  async function analyzeSmartMode() {
    setError("");
    setAnswer(null);
    setSmartSuggestion(null);

    if (!prompt.trim()) {
      setError("Please write a prompt first.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat/smart/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.error || "Smart analysis failed");
      }

      setSmartSuggestion(data);
      setMode(data.suggested_mode);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function sendPrompt(selectedMode = mode) {
    setError("");
    setAnswer(null);

    if (!prompt.trim()) {
      setError("Please write a prompt first.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(endpoints[selectedMode], {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ prompt })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.error || "Request failed");
      }

      setAnswer(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function renderModelResult(model, result) {
    return (
      <div key={model} style={{ marginBottom: "18px" }}>
        <strong>{model}</strong>
        <p>
          {typeof result === "string"
            ? result || "No response"
            : result.answer || JSON.stringify(result, null, 2)}
        </p>
      </div>
    );
  }

  function renderSmartSuggestion() {
  if (!smartSuggestion) return null;

  const matches = smartSuggestion.matches || {};
  const selectedMatches = matches[smartSuggestion.suggested_mode] || [];
  const topReasons = selectedMatches.slice(0, 4);

  return (
    <div className="answerBox">
      <h2>Smart Recommendation</h2>

      <p>
        Recommended mode: <strong>{smartSuggestion.suggested_mode}</strong>
      </p>

      <p>
  Based on your prompt, this looks like a{" "}
  <strong>{smartSuggestion.suggested_mode}</strong> type task.
</p>

      {topReasons.length > 0 && (
        <>
          <h3>Main signals found</h3>
          <ul>
            {topReasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      )}

      <div className="modeRow">
        <button onClick={() => sendPrompt(smartSuggestion.suggested_mode)}>
          Use {smartSuggestion.suggested_mode}
        </button>

        <button onClick={() => sendPrompt("cloud")}>Use Cloud</button>
        <button onClick={() => sendPrompt("council")}>Use Council</button>
        <button onClick={() => sendPrompt("debate")}>Use Debate</button>
      </div>
    </div>
  );
}

  function renderAnswer() {
    if (!answer) return null;

    if (answer.mode === "cloud") {
      return <pre>{answer.answer}</pre>;
    }

    if (answer.mode === "council") {
      return Object.entries(answer.answer || {}).map(([model, result]) =>
        renderModelResult(model, result)
      );
    }

   if (answer.mode === "council_debate") {
  return (
    <>
      {answer.final_answer && (
        <>
          <h3>Final Answer</h3>
          <pre>{answer.final_answer}</pre>
        </>
      )}

      <h3>Round 1: Independent Answers</h3>
      {Object.entries(answer.round1 || {}).map(([model, result]) =>
        renderModelResult(model, result)
      )}

      <h3>Round 2: Revised Answers</h3>
      {Object.entries(answer.round2 || {}).map(([model, result]) =>
        renderModelResult(model, result)
      )}
    </>
  );
}

    return <pre>{JSON.stringify(answer, null, 2)}</pre>;
  }

  return (
    <main className="page">
      <section className="card">
        <h1>AI Council</h1>
        <p className="subtitle">
          Send manually, or use Smart Mode to get a recommendation first.
        </p>

        <div className="modeRow">
          <button
            className={mode === "cloud" ? "active" : ""}
            onClick={() => setMode("cloud")}
          >
            Chat Cloud
          </button>

          <button
            className={mode === "council" ? "active" : ""}
            onClick={() => setMode("council")}
          >
            Chat Council
          </button>

          <button
            className={mode === "debate" ? "active" : ""}
            onClick={() => setMode("debate")}
          >
            Chat Debate
          </button>
        </div>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Write your prompt here..."
        />

        <button className="sendBtn" onClick={() => sendPrompt()} disabled={loading}>
          {loading ? "Working..." : `Send with ${mode}`}
        </button>

        <button className="sendBtn" onClick={analyzeSmartMode} disabled={loading}>
          Smart Analyze First
        </button>

        {error && <div className="error">{error}</div>}

        {renderSmartSuggestion()}

        {answer && (
          <div className="answerBox">
            <h2>Answer</h2>
            {renderAnswer()}
          </div>
        )}
      </section>
    </main>
  );
}