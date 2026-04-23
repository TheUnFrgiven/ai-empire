import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Empire API")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

class ChatRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "AI Empire API running"}

@app.get("/providers")
def providers():
    return {
        "openrouter": True,
        "ollama": False,
        "claude_direct": False
    }

@app.post("/chat/cloud")
def chat_cloud(req: ChatRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"error": "Missing OPENROUTER_API_KEY in .env"}

    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": req.message}]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    return r.json()

@app.post("/chat/council")
def chat_council(req: ChatRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"error": "Missing OPENROUTER_API_KEY in .env"}

    models = [
        "openai/gpt-4o-mini",
        "google/gemini-flash-1.5",
    ]

    results = {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for model in models:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": req.message}]
        }
        try:
            r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
            results[model] = r.json()
        except Exception as e:
            results[model] = {"error": str(e)}

    return results