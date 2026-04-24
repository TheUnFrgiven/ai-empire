import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
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

# ─────────────────────────────────────────────────────────────────────────────
# COUNCIL MODELS
# Three models from genuinely different providers/architectures.
# Previously: 2 OpenAI models (same lab, same values, minimal real disagreement).
# Now: OpenAI + Mistral AI + Meta — different training, different perspectives.
# All three are available on OpenRouter. The free-tier variants are used for
# Mistral and LLaMA to keep costs low; swap to paid versions for better quality.
# ─────────────────────────────────────────────────────────────────────────────
COUNCIL_MODELS = [
    {
        "id": "openai/gpt-4o-mini",
        "label": "GPT-4o Mini",
        "provider": "OpenAI",
    },
    {
        "id": "mistralai/mistral-7b-instruct:free",
        "label": "Mistral 7B",
        "provider": "Mistral AI",
    },
    {
        "id": "meta-llama/llama-3.1-8b-instruct:free",
        "label": "LLaMA 3.1 8B",
        "provider": "Meta",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# AVAILABLE ROLES FOR ROUND 0 NEGOTIATION
# Each model proposes its own role based on the user's prompt.
# This list is a suggestion set — models may also propose custom roles.
# ─────────────────────────────────────────────────────────────────────────────
AVAILABLE_ROLES = [
    "Analyst",        # logical, evidence-based, data-driven
    "Critic",         # finds flaws, challenges assumptions, devil's advocate
    "Strategist",     # long-term thinking, systems, planning
    "Creative",       # unconventional angles, novel solutions
    "Risk Analyst",   # identifies dangers, downsides, edge cases
    "Pragmatist",     # practical, cost-aware, real-world constraints
    "Domain Expert",  # deep knowledge, technical precision
]


# ─────────────────────────────────────────────────────────────────────────────
# SMART MODE KEYWORDS (unchanged from original)
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# CORE API CALL
# Now accepts an optional system_prompt — this is what gives each model
# its identity and role in council/debate mode.
# ─────────────────────────────────────────────────────────────────────────────
def get_openrouter_key():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing OPENROUTER_API_KEY in .env",
        )
    return api_key


def call_openrouter(
    prompt: str,
    model: str,
    system_prompt: Optional[str] = None,
):
    api_key = get_openrouter_key()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {"model": model, "messages": messages}
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
            return {"answer": "", "error": "OpenRouter returned a non-JSON response."}

        if not response.ok:
            return {"answer": "", "error": data}

        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        return {"answer": answer, "error": None}

    except requests.exceptions.Timeout:
        return {"answer": "", "error": f"Request timed out after {REQUEST_TIMEOUT}s."}
    except requests.exceptions.RequestException as e:
        return {"answer": "", "error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"answer": "", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# PARALLEL COUNCIL CALL
# Previously all models were called sequentially. This was the biggest latency
# problem — 3 models × 2 rounds = potentially 6 serial API calls.
#
# Now all models in a round are called simultaneously with ThreadPoolExecutor.
# Round 1 (3 models): ~same time as 1 call instead of 3x.
# Round 2 (3 models): same gain.
# Rough time saving: ~60-70% reduction in total debate latency.
#
# system_prompts: {model_id: system_prompt_string} — optional per-model prompts
# ─────────────────────────────────────────────────────────────────────────────
def parallel_council_call(
    prompt: str,
    system_prompts: Optional[dict] = None,
    max_workers: int = 3,
) -> dict:
    results = {}

    def _call(model_info: dict):
        sys_prompt = (system_prompts or {}).get(model_info["id"])
        result = call_openrouter(prompt, model_info["id"], sys_prompt)
        return model_info["id"], result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_call, model_info): model_info
            for model_info in COUNCIL_MODELS
        }
        for future in as_completed(futures):
            model_info = futures[future]
            try:
                model_id, result = future.result()
                results[model_id] = {
                    "answer": result["answer"],
                    "error": result["error"],
                    "label": model_info["label"],
                    "provider": model_info["provider"],
                }
            except Exception as e:
                results[model_info["id"]] = {
                    "answer": "",
                    "error": str(e),
                    "label": model_info["label"],
                    "provider": model_info["provider"],
                }

    return results


# ─────────────────────────────────────────────────────────────────────────────
# ROUND 0: ROLE NEGOTIATION
# This is the "autonomous council" feature. Instead of manually assigning
# roles, each model reads the prompt and proposes the role it would be
# most useful playing.
#
# Why this matters: a question about security risks should organically produce
# a Risk Analyst, not have one forced by static config. The role each model
# chooses reveals what it "sees" in the prompt — which is itself informative.
#
# Returns: {model_id: role_string}
# ─────────────────────────────────────────────────────────────────────────────
def negotiate_roles(prompt: str) -> dict:
    role_prompt = f"""You are about to join an AI reasoning council to answer a question.

The question is:
{prompt}

Available roles: {", ".join(AVAILABLE_ROLES)}

Choose the single role YOU would be most useful playing for this specific question.
You may propose a custom role (2-3 words max) if none of the above fit well.

Rules:
- Respond with ONLY the role name. Nothing else.
- No explanation, no punctuation, no quotes.
- Example valid responses: "Risk Analyst" or "Critic" or "Domain Expert"
"""

    raw_roles = parallel_council_call(role_prompt)
    negotiated = {}

    for model_id, data in raw_roles.items():
        raw = (data.get("answer") or "").strip().strip('"').strip("'").strip()
        # Sanitize: if empty or suspiciously long, fall back to Analyst
        if not raw or len(raw) > 35:
            raw = "Analyst"
        # Capitalize cleanly
        negotiated[model_id] = raw.title()

    return negotiated


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHESIS PARSER
# The synthesis prompt asks the model to return structured sections.
# This function extracts those sections cleanly so the frontend can
# display disagreements and consensus separately — making the debate auditable.
# ─────────────────────────────────────────────────────────────────────────────
def parse_synthesis(raw: str) -> dict:
    disagreements = []
    consensus_points = []
    final_answer = raw
    confidence = "Medium"
    confidence_reason = ""

    try:
        if "POINTS OF GENUINE DISAGREEMENT:" in raw:
            block = raw.split("POINTS OF GENUINE DISAGREEMENT:")[1]
            if "POINTS OF CONSENSUS:" in block:
                disagreement_text = block.split("POINTS OF CONSENSUS:")[0]
                disagreements = [
                    line.strip().lstrip("-").strip()
                    for line in disagreement_text.strip().splitlines()
                    if line.strip() and line.strip() not in ("-", "")
                ]

        if "POINTS OF CONSENSUS:" in raw:
            block = raw.split("POINTS OF CONSENSUS:")[1]
            if "FINAL ANSWER:" in block:
                consensus_text = block.split("FINAL ANSWER:")[0]
                consensus_points = [
                    line.strip().lstrip("-").strip()
                    for line in consensus_text.strip().splitlines()
                    if line.strip() and line.strip() not in ("-", "")
                ]

        if "FINAL ANSWER:" in raw:
            answer_block = raw.split("FINAL ANSWER:")[1]
            if "CONFIDENCE:" in answer_block:
                final_answer = answer_block.split("CONFIDENCE:")[0].strip()
                confidence_block = answer_block.split("CONFIDENCE:")[1]
                conf_line = confidence_block.strip().splitlines()[0].strip()
                confidence = conf_line.split("/")[0].strip()
                if "CONFIDENCE REASON:" in confidence_block:
                    confidence_reason = (
                        confidence_block.split("CONFIDENCE REASON:")[1]
                        .strip()
                        .splitlines()[0]
                        .strip()
                    )
            else:
                final_answer = answer_block.strip()

    except Exception:
        pass  # Parsing failed — return raw as final_answer

    return {
        "final_answer": final_answer or raw,
        "disagreements": [d for d in disagreements if d],
        "consensus_points": [c for c in consensus_points if c],
        "confidence": confidence,
        "confidence_reason": confidence_reason,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str


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
        "models": [
            {
                "id": m["id"],
                "label": m["label"],
                "provider": m["provider"],
            }
            for m in COUNCIL_MODELS
        ],
    }


@app.post("/chat/smart/analyze")
def smart_analyze(req: ChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    text = req.prompt.lower()
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
    if scores[suggested_mode] == 0:
        suggested_mode = "cloud"

    return {
        "suggested_mode": suggested_mode,
        "scores": scores,
        "matches": matches,
        "message": f"Smart Mode recommends {suggested_mode} based on prompt length and detected keywords.",
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
    """
    Council Mode: All models answer the same prompt in parallel.
    Now includes provider/label metadata and runs in parallel (not sequential).
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    results = parallel_council_call(req.prompt)
    return {
        "mode": "council",
        "answer": results,
    }


@app.post("/chat/council/debate")
def chat_council_debate(req: ChatRequest):
    """
    Debate Mode — Full 3-round autonomous council:

    ROUND 0 — Role Negotiation:
      Each model reads the prompt and proposes its own role.
      Roles are injected into subsequent system prompts.

    ROUND 1 — Independent Answers (parallel):
      Each model answers from its negotiated role perspective.
      Models do not see each other's answers yet.

    ROUND 2 — Critique and Revision (parallel):
      Each model receives ALL Round 1 answers with attribution.
      Each model must: identify gaps, challenge an assumption,
      then produce an improved answer from its role's lens.

    SYNTHESIS — Auditable Final Answer:
      A structured synthesis that surfaces genuine disagreements,
      points of consensus, and a confidence-rated final answer.
      The human can see exactly where models diverged.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # ── ROUND 0: Role Negotiation ────────────────────────────────────────────
    negotiated_roles = negotiate_roles(req.prompt)

    # ── ROUND 1: Independent Answers ─────────────────────────────────────────
    # Each model gets a system prompt with its negotiated role baked in.
    # This is what makes the role real — without this injection, role
    # negotiation is theater. The role must constrain actual behavior.
    round1_system_prompts = {
        model_info["id"]: (
            f"You are a {negotiated_roles.get(model_info['id'], 'Analyst')} "
            f"in a multi-model AI reasoning council.\n"
            f"Approach this question specifically through the lens of a "
            f"{negotiated_roles.get(model_info['id'], 'Analyst')}.\n"
            f"Be direct, specific, and substantive. Avoid generic platitudes.\n"
            f"Do not mention that you are part of a council or that other models exist."
        )
        for model_info in COUNCIL_MODELS
    }

    round1_prompt = (
        f"Question: {req.prompt}\n\n"
        f"Answer from your role's perspective. Be clear and specific."
    )

    round1 = parallel_council_call(round1_prompt, round1_system_prompts)

    # Bail out early if all models failed
    if not any(data["answer"] for data in round1.values()):
        return {
            "mode": "council_debate",
            "final_answer": "No valid responses from any council model.",
            "full_synthesis": "",
            "disagreements": [],
            "consensus_points": [],
            "confidence": "Low",
            "confidence_reason": "All models failed to respond.",
            "round0_roles": negotiated_roles,
            "round1": round1,
            "round2": {},
        }

    # Build structured Round 1 context for Round 2.
    # Attribution is explicit: each block shows which model said what,
    # and what role they were playing. This is what enables real critique —
    # models know who said what and can target specific claims.
    round1_context = "\n\n".join([
        (
            f"[{data['label']} ({data['provider']}) — "
            f"Role: {negotiated_roles.get(mid, 'Analyst')}]\n"
            f"{data['answer']}"
        )
        for mid, data in round1.items()
        if data["answer"]
    ])

    # ── ROUND 2: Critique and Revision ───────────────────────────────────────
    round2_system_prompts = {
        model_info["id"]: (
            f"You are a {negotiated_roles.get(model_info['id'], 'Analyst')} "
            f"in an AI reasoning council.\n"
            f"You have now seen what the other council members said in Round 1.\n"
            f"Your job is NOT to agree or synthesize — it is to critique and improve.\n"
            f"Stay in your role as {negotiated_roles.get(model_info['id'], 'Analyst')}. "
            f"Find what others missed through your specific lens.\n"
            f"Intellectual disagreement is expected and valuable here."
        )
        for model_info in COUNCIL_MODELS
    }

    round2_prompt = (
        f"Original question: {req.prompt}\n\n"
        f"━━━ ROUND 1 COUNCIL ANSWERS ━━━\n"
        f"{round1_context}\n"
        f"━━━ END ROUND 1 ━━━\n\n"
        f"Your tasks as your assigned role:\n"
        f"1. Identify the single most important gap, error, or overlooked angle "
        f"in the other answers above. Be specific — name what was missed.\n"
        f"2. Challenge at least one assumption present across the answers.\n"
        f"3. Write your IMPROVED answer that addresses what others missed.\n\n"
        f"Be direct. Softening your critique makes the council weaker.\n"
        f"Return only your improved answer — no preamble."
    )

    round2 = parallel_council_call(round2_prompt, round2_system_prompts)

    # ── SYNTHESIS ─────────────────────────────────────────────────────────────
    valid_round2 = {mid: data for mid, data in round2.items() if data["answer"]}

    if valid_round2:
        revised_context = "\n\n".join([
            (
                f"[{data['label']} ({data['provider']}) — "
                f"Role: {negotiated_roles.get(mid, 'Analyst')}]\n"
                f"{data['answer']}"
            )
            for mid, data in valid_round2.items()
        ])

        synthesis_prompt = (
            f"You are synthesizing the output of an AI reasoning council.\n\n"
            f"Original question:\n{req.prompt}\n\n"
            f"━━━ ROUND 2 COUNCIL ANSWERS ━━━\n"
            f"{revised_context}\n"
            f"━━━ END ROUND 2 ━━━\n\n"
            f"Produce a structured synthesis in this EXACT format. "
            f"Do not skip any section.\n\n"
            f"POINTS OF GENUINE DISAGREEMENT:\n"
            f"- [Each real point where council members disagreed — be specific]\n\n"
            f"POINTS OF CONSENSUS:\n"
            f"- [What all or most members agreed on]\n\n"
            f"FINAL ANSWER:\n"
            f"[The best possible answer combining the strongest points. "
            f"Be comprehensive and practical. "
            f"Do not mention the council, the debate, or the models.]\n\n"
            f"CONFIDENCE: [Low / Medium / High]\n"
            f"CONFIDENCE REASON: [One sentence explaining the confidence level]"
        )

        synthesis_result = call_openrouter(synthesis_prompt, DEFAULT_MODEL)
        raw_synthesis = synthesis_result["answer"] or ""
        parsed = parse_synthesis(raw_synthesis)

    else:
        raw_synthesis = ""
        parsed = {
            "final_answer": "No valid revised responses from council models.",
            "disagreements": [],
            "consensus_points": [],
            "confidence": "Low",
            "confidence_reason": "Round 2 produced no valid responses.",
        }

    return {
        "mode": "council_debate",
        # Primary answer — clean, ready for display
        "final_answer": parsed["final_answer"],
        # Audit trail — shows the reasoning behind the final answer
        "disagreements": parsed["disagreements"],
        "consensus_points": parsed["consensus_points"],
        "confidence": parsed["confidence"],
        "confidence_reason": parsed["confidence_reason"],
        # Full raw synthesis — useful for debugging or advanced UI
        "full_synthesis": raw_synthesis,
        # Round data — full transparency into the debate
        "round0_roles": negotiated_roles,
        "round1": round1,
        "round2": round2,
    }