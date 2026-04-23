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
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        OPENROUTER_URL,
        json=payload,
        headers=headers,
        timeout=120,
    )

    data = response.json()

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
        try:
            result = call_openrouter(req.prompt, model)
            results[model] = {
                "answer": result["answer"],
                "error": result["error"],
            }
        except Exception as e:
            results[model] = {
                "answer": "",
                "error": str(e),
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

        round1[model] = {
            "answer": result["answer"],
            "error": result["error"],
        }

    combined_answers = "\n\n".join(
        [
            f"Model: {model}\nAnswer: {data['answer']}"
            for model, data in round1.items()
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
1. Compare the answers.
2. Notice missing points or weak parts.
3. Revise your own answer into a stronger final answer.
4. Do not reveal hidden reasoning.
5. Return only the improved answer.
"""

        result = call_openrouter(revision_prompt, model)

        round2[model] = {
            "answer": result["answer"],
            "error": result["error"],
        }

    return {
        "mode": "council_debate",
        "round1": round1,
        "round2": round2,
    }