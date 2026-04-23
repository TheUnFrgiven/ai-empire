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
    "google/gemini-flash-1.5",
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
            "raw": data,
        }

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    return {
        "answer": answer,
        "error": None,
        "raw": data,
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