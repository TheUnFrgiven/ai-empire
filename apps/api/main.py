import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

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
REQUEST_TIMEOUT = 65

DEFAULT_MODEL = "openai/gpt-4o-mini"

COUNCIL_MODELS = [
    "openai/gpt-4o-mini",
    "openrouter/free",
]


class ChatRequest(BaseModel):
    prompt: str


def get_openrouter_key():
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing OPENROUTER_API_KEY in .env",
        )

    return api_key


def call_openrouter(prompt: str, model: str):
    api_key = get_openrouter_key()

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            OPENROUTER_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            data = response.json()
        except Exception:
            return {
                "answer": "",
                "error": "OpenRouter returned a non-JSON response.",
            }

        if not response.ok:
            return {
                "answer": "",
                "error": data,
            }

        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        return {
            "answer": answer,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return {
            "answer": "",
            "error": f"Request timed out after {REQUEST_TIMEOUT} seconds.",
        }
    except requests.exceptions.RequestException as e:
        return {
            "answer": "",
            "error": f"Network error: {str(e)}",
        }
    except Exception as e:
        return {
            "answer": "",
            "error": str(e),
        }


CLOUD_KEYWORDS = [
    "hi", "hello", "hey", "bye", "thanks", "thank you", "what is", "define",
    "meaning", "explain", "simple", "quick", "short", "basic", "beginner",
    "easy", "example", "give me", "show me", "list", "summarize", "translate",
    "convert", "syntax", "code snippet", "small", "fix", "debug", "how to",
    "where is", "when is", "who is", "single answer", "one sentence",
    "briefly", "simple explanation", "easy words", "step by step"
]

COUNCIL_KEYWORDS = [
    "compare", "comparison", "better", "best", "vs", "versus", "pros",
    "cons", "advantages", "disadvantages", "review", "opinion",
    "recommend", "recommendation", "which should", "choose", "choice",
    "options", "alternative", "alternatives", "difference", "differences",
    "evaluate", "ranking", "rank", "top", "worth it", "is it worth",
    "should i", "tradeoff", "tradeoffs", "performance", "efficiency",
    "reliability", "quality", "price", "value", "decision", "selection",
    "pick", "suggest", "compare them", "which one", "what should i buy"
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
    "law", "privacy", "safety", "compare deeply", "deep comparison"
]


@app.post("/chat/smart/analyze")
def smart_analyze(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    text = req.prompt.lower()

    scores = {
        "cloud": 0,
        "council": 0,
        "debate": 0,
    }

    matches = {
        "cloud": [],
        "council": [],
        "debate": [],
    }

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

    if scores[suggested_mode] == 0:
        suggested_mode = "cloud"

    return {
        "suggested_mode": suggested_mode,
        "scores": scores,
        "matches": matches,
        "message": f"Smart Mode recommends {suggested_mode} based on the prompt length and detected keywords.",
    }


@app.get("/")
def root():
    return {"message": "AI Empire API running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/providers")
def providers():
    return {
        "openrouter": True,
        "ollama": False,
        "claude_direct": False,
    }


@app.post("/chat/cloud")
def chat_cloud(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    result = call_openrouter(req.prompt, DEFAULT_MODEL)

    return {
        "mode": "cloud",
        "model": DEFAULT_MODEL,
        "answer": result["answer"],
        "error": result["error"],
    }


@app.post("/chat/council")
def chat_council(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    results = {}

    for model in COUNCIL_MODELS:
        result = call_openrouter(req.prompt, model)

        if result["answer"] or result["error"]:
            results[model] = {
                "answer": result["answer"],
                "error": result["error"],
            }

    return {
        "mode": "council",
        "answer": results,
    }


@app.post("/chat/council/debate")
def chat_council_debate(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    round1 = {}

    for model in COUNCIL_MODELS:
        first_prompt = f"""
User question:
{req.prompt}

Answer independently. Be clear, useful, and concise.
Do not mention other models.
"""

        result = call_openrouter(first_prompt, model)

        if result["answer"] or result["error"]:
            round1[model] = {
                "answer": result["answer"],
                "error": result["error"],
            }

    if not any(data["answer"] for data in round1.values()):
        return {
            "mode": "council_debate",
            "final_answer": "No valid responses from models.",
            "round1": round1,
            "round2": {},
        }

    combined_answers = "\n\n".join(
        [
            f"Model: {model}\nAnswer: {data['answer']}"
            for model, data in round1.items()
            if data["answer"]
        ]
    )

    round2 = {}

    for model in COUNCIL_MODELS:
        revision_prompt = f"""
User question:
{req.prompt}

Here are the first-round answers from the council:

{combined_answers}

Your task:
You are part of an AI council. Your goal is NOT to agree.

1. Identify weaknesses, mistakes, or missing points in the other answers.
2. Challenge assumptions if they are unclear or incorrect.
3. Point out anything that is too vague, generic, or incomplete.
4. Improve your answer by fixing these issues.

Rules:
- Be critical, but constructive.
- Do NOT just agree or repeat.
- Do NOT mention "other models" explicitly.
- Focus on making the best possible answer.

Return ONLY your improved answer.
"""

        result = call_openrouter(revision_prompt, model)

        if result["answer"]:
            round2[model] = {
                "answer": result["answer"],
                "error": result["error"],
            }

    if round2:
        revised_answers = "\n\n".join(
            [
                f"Model: {model}\nRevised Answer: {data['answer']}"
                for model, data in round2.items()
                if data["answer"]
            ]
        )

        final_prompt = f"""
User question:
{req.prompt}

Here are the revised answers from the AI council:

{revised_answers}

Your task:
Create one final answer that combines the strongest points.
Remove repetition.
Keep it clear, useful, and practical.
Do not mention the internal debate process.
Return only the final answer.
"""

        final_result = call_openrouter(final_prompt, DEFAULT_MODEL)
        final_answer = final_result["answer"] or "Final answer could not be generated."
    else:
        final_answer = "No valid revised responses from models."

    return {
        "mode": "council_debate",
        "final_answer": final_answer,
        "round1": round1,
        "round2": round2,
    }