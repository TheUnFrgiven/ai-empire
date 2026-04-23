"use client";

import { useState } from "react";
import "./globals.css";

export default function Page() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("cloud");
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendPrompt() {
    setError("");
    setAnswer(null);

    if (!prompt.trim()) {
      setError("Please write a prompt first.");
      return;
    }

    setLoading(true);

    try {
      const endpoint =
        mode === "cloud"
          ? "http://localhost:8000/chat/cloud"
          : "http://localhost:8000/chat/council";

      const res = await fetch(endpoint, {
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

      setAnswer(data.answer || data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function renderAnswer() {
    if (typeof answer === "string") {
      return <pre>{answer}</pre>;
    }

    return Object.entries(answer).map(([model, result]) => (
      <div key={model} style={{ marginBottom: "18px" }}>
        <strong>{model}</strong>
        <p>
          {typeof result === "string"
            ? result || "No response"
            : result.answer || JSON.stringify(result, null, 2)}
        </p>
      </div>
    ));
  }

  return (
    <main className="page">
      <section className="card">
        <h1>AI Council</h1>
        <p className="subtitle">Send a prompt to Cloud or Council mode.</p>

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
        </div>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Write your prompt here..."
        />

        <button className="sendBtn" onClick={sendPrompt} disabled={loading}>
          {loading ? "Thinking..." : "Send"}
        </button>

        {error && <div className="error">{error}</div>}

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