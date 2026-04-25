import json
import os
from typing import Any, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .config import load_environment
except ImportError:
    from config import load_environment


load_environment()

try:
    from .council import provider_health, run_council, run_parallel_answers
except ImportError:
    from council import provider_health, run_council, run_parallel_answers


app = FastAPI(title="AI Empire API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "65"))

CLOUD_KEYWORDS = [
    "hi", "hello", "hey", "bye", "thanks", "thank you", "what is", "define",
    "meaning", "explain", "simple", "quick", "short", "basic", "beginner",
    "easy", "example", "give me", "show me", "list", "summarize", "translate",
    "convert", "syntax", "code snippet", "small", "fix", "debug", "how to",
    "where is", "when is", "who is", "single answer", "one sentence",
    "briefly", "simple explanation", "easy words", "step by step",
]

COUNCIL_KEYWORDS = [
    "compare", "comparison", "better", "best", "vs", "versus", "pros",
    "cons", "advantages", "disadvantages", "review", "opinion",
    "recommend", "recommendation", "which should", "choose", "choice",
    "options", "alternative", "alternatives", "difference", "differences",
    "evaluate", "ranking", "rank", "top", "worth it", "is it worth",
    "should i", "tradeoff", "tradeoffs", "performance", "efficiency",
    "reliability", "quality", "price", "value", "decision", "selection",
    "pick", "suggest", "compare them", "which one", "what should i buy",
]

DEBATE_KEYWORDS = [
    "strategy", "plan", "architecture", "system design", "analyze deeply",
    "deep analysis", "critique", "challenge", "argue", "debate", "reasoning",
    "justify", "optimize", "long term", "risk", "risks", "investment",
    "legal", "medical", "security", "ethical", "complex", "multi-step",
    "build a system", "design a solution", "find flaws", "improve",
    "refine", "research", "research-level", "decision making", "roadmap",
    "ecosystem", "business model", "scalable", "scalability", "failure",
    "limitations", "weaknesses", "opposing views", "both sides",
    "argue both sides", "critical thinking", "full analysis", "professional",
    "production", "production-ready", "high stakes", "financial",
    "law", "privacy", "safety", "compare deeply", "deep comparison",
]


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20000)


def _clean_prompt(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    return cleaned


def _openrouter_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not configured")
    return api_key


def call_openrouter(prompt: str, model: str = DEFAULT_MODEL, system_prompt: Optional[str] = None) -> dict:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = requests.post(
            OPENROUTER_URL,
            json={"model": model, "messages": messages},
            headers={
                "Authorization": f"Bearer {_openrouter_key()}",
                "Content-Type": "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return {"answer": "", "error": f"Request timed out after {REQUEST_TIMEOUT}s."}
    except requests.exceptions.RequestException as exc:
        return {"answer": "", "error": f"Network error: {exc}"}

    try:
        data: dict[str, Any] = response.json()
    except ValueError:
        return {"answer": "", "error": "OpenRouter returned a non-JSON response."}

    if not response.ok:
        message = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        return {"answer": "", "error": message or f"OpenRouter error {response.status_code}"}

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {"answer": answer or "", "error": None}


def keyword_smart_analyze(prompt: str) -> dict:
    text = prompt.lower()
    scores = {"cloud": 0, "council": 0, "debate": 0}
    matches = {"cloud": [], "council": [], "debate": []}

    for keyword in CLOUD_KEYWORDS:
        if keyword in text:
            scores["cloud"] += 1
            matches["cloud"].append(keyword)

    for keyword in COUNCIL_KEYWORDS:
        if keyword in text:
            scores["council"] += 2
            matches["council"].append(keyword)

    for keyword in DEBATE_KEYWORDS:
        if keyword in text:
            scores["debate"] += 3
            matches["debate"].append(keyword)

    word_count = len(text.split())
    if word_count <= 8:
        scores["cloud"] += 2
    elif word_count <= 30:
        scores["council"] += 1
    else:
        scores["debate"] += 2

    suggested_mode = max(scores, key=scores.get)
    return {
        "suggested_mode": suggested_mode,
        "scores": scores,
        "matches": matches,
        "task_type": "unknown",
        "complexity": "low" if suggested_mode == "cloud" else "medium" if suggested_mode == "council" else "high",
        "risk_level": "low",
        "reason": f"Keyword fallback recommends {suggested_mode} based on prompt length and detected keywords.",
        "needs_tools": [],
        "fallback_mode": "cloud" if suggested_mode != "cloud" else "council",
        "classifier": "keyword_fallback",
        "message": f"Smart Mode recommends {suggested_mode} using fallback keyword analysis.",
    }


def normalize_smart_mode(data: dict, fallback: dict) -> dict:
    allowed_modes = {"cloud", "council", "debate"}
    allowed_complexity = {"low", "medium", "high"}
    allowed_risk = {"low", "medium", "high"}

    suggested_mode = str(data.get("suggested_mode", "")).lower().strip()
    if suggested_mode not in allowed_modes:
        suggested_mode = fallback["suggested_mode"]

    fallback_mode = str(data.get("fallback_mode", fallback.get("fallback_mode", "cloud"))).lower().strip()
    if fallback_mode not in allowed_modes:
        fallback_mode = fallback.get("fallback_mode", "cloud")

    complexity = str(data.get("complexity", fallback.get("complexity", "medium"))).lower().strip()
    if complexity not in allowed_complexity:
        complexity = fallback.get("complexity", "medium")

    risk_level = str(data.get("risk_level", fallback.get("risk_level", "low"))).lower().strip()
    if risk_level not in allowed_risk:
        risk_level = fallback.get("risk_level", "low")

    needs_tools = data.get("needs_tools", [])
    if not isinstance(needs_tools, list):
        needs_tools = []

    reason = str(data.get("reason", fallback.get("reason", ""))).strip()
    if not reason:
        reason = fallback.get("reason", "Smart Mode selected the most suitable mode.")

    return {
        "suggested_mode": suggested_mode,
        "scores": fallback["scores"],
        "matches": fallback["matches"],
        "task_type": str(data.get("task_type", fallback.get("task_type", "unknown"))).strip() or "unknown",
        "complexity": complexity,
        "risk_level": risk_level,
        "reason": reason,
        "needs_tools": [str(tool).strip() for tool in needs_tools if str(tool).strip()][:6],
        "fallback_mode": fallback_mode,
        "classifier": "ai",
        "message": f"Smart Mode recommends {suggested_mode}: {reason}",
    }


@app.get("/")
def root():
    return {"message": "AI Empire API running"}


@app.get("/health")
def health():
    return {"status": "ok", "providers": provider_health()}


@app.get("/providers")
def providers():
    return {
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
        "openrouter_model": DEFAULT_MODEL,
        "providers": provider_health(),
    }


@app.post("/chat/smart/analyze")
def smart_analyze(req: ChatRequest):
    prompt = _clean_prompt(req.prompt)
    fallback = keyword_smart_analyze(prompt)

    classifier_prompt = f"""Classify this prompt for an AI Council app.

Modes:
- cloud: simple, fast, direct answers.
- council: comparisons, recommendations, reviews, multi-perspective answers.
- debate: complex planning, architecture, risk, strategy, or high-stakes decisions.

Return only valid JSON:
{{
  "suggested_mode": "cloud" | "council" | "debate",
  "task_type": "short_label",
  "complexity": "low" | "medium" | "high",
  "risk_level": "low" | "medium" | "high",
  "reason": "one short sentence",
  "needs_tools": [],
  "fallback_mode": "cloud" | "council" | "debate"
}}

Prompt:
{prompt}
"""
    system_prompt = "You classify prompts. Do not answer the prompt. Return strict JSON only."

    try:
        result = call_openrouter(classifier_prompt, DEFAULT_MODEL, system_prompt)
    except HTTPException:
        return fallback

    raw = (result.get("answer") or "").strip()
    if result.get("error") or not raw:
        return fallback

    try:
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return normalize_smart_mode(json.loads(cleaned), fallback)
    except (ValueError, TypeError):
        return fallback


@app.post("/chat/cloud")
def chat_cloud(req: ChatRequest):
    prompt = _clean_prompt(req.prompt)
    result = call_openrouter(prompt)
    return {
        "mode": "cloud",
        "model": DEFAULT_MODEL,
        "answer": result["answer"],
        "error": result["error"],
    }


@app.post("/chat/council")
def chat_council(req: ChatRequest):
    prompt = _clean_prompt(req.prompt)
    return run_parallel_answers(prompt)


@app.post("/council")
def council(req: ChatRequest):
    prompt = _clean_prompt(req.prompt)
    return run_council(prompt)


@app.post("/chat/council/debate")
def chat_council_debate(req: ChatRequest):
    prompt = _clean_prompt(req.prompt)
    return run_council(prompt)
