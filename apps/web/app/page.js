"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import "./globals.css";
import { ModeSelector } from "./components/ModeSelector";
import { PromptBox } from "./components/PromptBox";
import { Results } from "./components/Results";
import { SmartRecommendation } from "./components/SmartRecommendation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEBATE_STEPS = [
  { label: "Collecting independent answers", sub: "Providers answer without seeing each other" },
  { label: "Critiques and revisions", sub: "Successful providers challenge and improve the answers" },
  { label: "Synthesizing final answer", sub: "The strongest points are combined into one response" },
];

const STEP_DELAYS = [0, 7000, 16000];

export default function Page() {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState("cloud");
  const [answer, setAnswer] = useState(null);
  const [smart, setSmart] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [debateStep, setDebateStep] = useState(-1);
  const [copied, setCopied] = useState(false);
  const [providers, setProviders] = useState([]);
  const [history, setHistory] = useState(() => {
    if (typeof window === "undefined") return [];
    const saved = window.localStorage.getItem("ai-council-history");
    if (!saved) return [];
    try {
      return JSON.parse(saved).slice(0, 8);
    } catch {
      return [];
    }
  });
  const stepTimers = useRef([]);
  const abortRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/providers`)
      .then((res) => res.json())
      .then((data) => setProviders(data.providers || []))
      .catch(() => setProviders([]));
  }, []);

  const persistHistory = useCallback((item) => {
    setHistory((prev) => {
      const next = [item, ...prev].slice(0, 8);
      window.localStorage.setItem("ai-council-history", JSON.stringify(next));
      return next;
    });
  }, []);

  const clearDebateSteps = useCallback(() => {
    stepTimers.current.forEach(clearTimeout);
    stepTimers.current = [];
    setDebateStep(-1);
  }, []);

  const startDebateSteps = useCallback(() => {
    clearDebateSteps();
    STEP_DELAYS.forEach((delay, i) => {
      const timer = setTimeout(() => setDebateStep(i), delay);
      stepTimers.current.push(timer);
    });
  }, [clearDebateSteps]);

  const cancelRequest = useCallback(() => {
    abortRef.current?.abort();
    clearDebateSteps();
    setLoading(false);
    setError("Request cancelled.");
  }, [clearDebateSteps]);

  const requestJson = useCallback(async (path, payload) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Request failed");
    }
    return data;
  }, []);

  const analyzeSmart = useCallback(async () => {
    if (!prompt.trim()) {
      setError("Please write a prompt first.");
      return;
    }

    setError("");
    setAnswer(null);
    setSmart(null);
    setLoading(true);
    try {
      const data = await requestJson("/chat/smart/analyze", { prompt });
      setSmart(data);
      setMode(data.suggested_mode);
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Smart analysis failed.");
      }
    } finally {
      setLoading(false);
    }
  }, [prompt, requestJson]);

  const handleSend = useCallback(async (overrideMode) => {
    const selectedMode = overrideMode || mode;
    if (!prompt.trim()) {
      setError("Please write a prompt first.");
      return;
    }

    const urls = {
      cloud: "/chat/cloud",
      council: "/chat/council",
      debate: "/chat/council/debate",
    };

    setError("");
    setAnswer(null);
    setSmart(null);
    setLoading(true);
    if (selectedMode === "debate") {
      startDebateSteps();
    }

    try {
      const data = await requestJson(urls[selectedMode], { prompt });
      setAnswer(data);
      persistHistory({
        prompt,
        mode: selectedMode,
        at: new Date().toISOString(),
      });
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
      clearDebateSteps();
    }
  }, [clearDebateSteps, mode, persistHistory, prompt, requestJson, startDebateSteps]);

  useEffect(() => {
    const handler = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !loading && prompt.trim()) {
        handleSend();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleSend, loading, prompt]);

  function copyAnswer() {
    const text = answer?.final_answer || answer?.answer || JSON.stringify(answer, null, 2);
    navigator.clipboard.writeText(typeof text === "string" ? text : JSON.stringify(text, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <main className="page">
      <section className="card">
        <header className="cardHeader">
          <div>
            <h1 className="title">AI Council</h1>
            <p className="subtitle">Multi-model reasoning. Less bias, better answers.</p>
          </div>
          <div className="headerDot" />
        </header>

        <ModeSelector mode={mode} onChange={(nextMode) => { setMode(nextMode); setSmart(null); }} />

        <PromptBox
          prompt={prompt}
          mode={mode}
          loading={loading}
          onPromptChange={setPrompt}
          onSend={() => handleSend()}
          onSmartAnalyze={analyzeSmart}
          onCancel={cancelRequest}
        />

        {providers.length > 0 && (
          <div className="providerStrip">
            {providers.map((provider) => (
              <span
                key={`${provider.provider}-${provider.model}`}
                className={`providerPill ${provider.configured ? "providerPill--ready" : "providerPill--missing"}`}
                title={provider.missing?.length ? `Missing ${provider.missing.join(", ")}` : provider.model}
              >
                {provider.provider}
              </span>
            ))}
          </div>
        )}

        {error && <div className="error">{error}</div>}

        {loading && (
          <div className="loadingBox">
            {debateStep >= 0 ? (
              <div className="stepsContainer">
                {DEBATE_STEPS.map((step, index) => {
                  const state = index < debateStep ? "done" : index === debateStep ? "active" : "pending";
                  return (
                    <div key={step.label} className={`step step--${state}`}>
                      <div className="stepDot">{state === "done" ? "✓" : index + 1}</div>
                      <div className="stepInfo">
                        <div className="stepLabel">{step.label}</div>
                        <div className="stepSub">{step.sub}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="loadingBox--simple">
                <div className="spinner" />
                <span className="loadingText">Thinking...</span>
              </div>
            )}
          </div>
        )}

        <SmartRecommendation smart={smart} onUseMode={handleSend} />

        {answer && !loading && (
          <Results answer={answer} copied={copied} onCopy={copyAnswer} />
        )}

        {history.length > 0 && (
          <div className="historyBox">
            <div className="historyTitle">Recent prompts</div>
            {history.map((item) => (
              <button
                key={`${item.at}-${item.prompt}`}
                className="historyItem"
                onClick={() => {
                  setPrompt(item.prompt);
                  setMode(item.mode);
                }}
              >
                <span>{item.mode}</span>
                {item.prompt}
              </button>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
