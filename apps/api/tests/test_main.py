from fastapi.testclient import TestClient

from apps.api import council
from apps.api import main


client = TestClient(main.app)


def test_keyword_smart_analyze_routes_comparison_to_council():
    result = main.keyword_smart_analyze("compare two laptops and recommend the best one")

    assert result["suggested_mode"] == "council"
    assert result["scores"]["council"] > result["scores"]["cloud"]


def test_keyword_smart_analyze_routes_architecture_to_debate():
    result = main.keyword_smart_analyze("design a scalable architecture and identify the risks")

    assert result["suggested_mode"] == "debate"
    assert result["complexity"] == "high"


def test_normalize_smart_mode_falls_back_on_bad_mode():
    fallback = main.keyword_smart_analyze("hello")

    result = main.normalize_smart_mode(
        {
            "suggested_mode": "sidequest",
            "complexity": "huge",
            "risk_level": "wild",
            "needs_tools": "browser",
            "reason": "",
        },
        fallback,
    )

    assert result["suggested_mode"] == fallback["suggested_mode"]
    assert result["complexity"] == fallback["complexity"]
    assert result["risk_level"] == fallback["risk_level"]
    assert result["needs_tools"] == []


def test_chat_council_uses_stable_shape(monkeypatch):
    def fake_parallel_answers(prompt):
        return {
            "mode": "council",
            "answer": [
                {
                    "provider": "Fake",
                    "model": "fake-model",
                    "text": f"answer to {prompt}",
                    "error": None,
                }
            ],
            "round1": [],
        }

    monkeypatch.setattr(main, "run_parallel_answers", fake_parallel_answers)

    response = client.post("/chat/council", json={"prompt": "compare options"})

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "council"
    assert data["answer"][0]["provider"] == "Fake"


def test_autonomous_role_fallback_is_task_sensitive():
    role = council._fallback_role("build an iphone app with a secure architecture", "Gemini")

    assert role == "Implementation Planner"


def test_parse_role_response_accepts_json():
    role, reason = council._parse_role_response('{"role":"Market Skeptic","reason":"Stress-test demand."}')

    assert role == "Market Skeptic"
    assert reason == "Stress-test demand."


def test_run_council_includes_autonomous_roles(monkeypatch):
    monkeypatch.setattr(
        council,
        "_negotiate_roles",
        lambda prompt: (
            {"Fake": "Critic"},
            [{
                "provider": "Fake",
                "model": "fake-model",
                "role": "Critic",
                "reason": "Challenge assumptions.",
                "error": None,
                "autonomous": True,
            }],
        ),
    )
    monkeypatch.setattr(
        council,
        "_run_round_1",
        lambda prompt, roles: [{"provider": "Fake", "model": "fake-model", "text": "round one", "error": None, "role": "Critic"}],
    )
    monkeypatch.setattr(
        council,
        "_run_round_2",
        lambda prompt, round1, roles: [{"provider": "Fake", "model": "fake-model", "text": "round two", "error": None, "role": "Critic"}],
    )
    monkeypatch.setattr(council, "_synthesize", lambda prompt, round2, roles: "final answer")

    result = council.run_council("is this worth building?")

    assert result["round0_roles"]["Fake"] == "Critic"
    assert result["role_proposals"][0]["autonomous"] is True
    assert result["stages"][0]["id"] == "roles"
    assert result["final_answer"] == "final answer"


def test_empty_prompt_rejected():
    response = client.post("/chat/council", json={"prompt": "   "})

    assert response.status_code == 400
