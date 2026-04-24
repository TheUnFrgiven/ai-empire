import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from .providers.gemini import GeminiProvider
    from .providers.grok import GrokProvider
    from .providers.ollama import OllamaProvider
    from .providers.openrouter import OpenRouterProvider
except ImportError:
    from providers.gemini import GeminiProvider
    from providers.grok import GrokProvider
    from providers.ollama import OllamaProvider
    from providers.openrouter import OpenRouterProvider


DIRECT_PROVIDERS = [
    GeminiProvider(),
    GrokProvider(),
    OllamaProvider(),
]

OPENROUTER_PROVIDERS = [
    OpenRouterProvider("OpenRouter OpenAI", os.getenv("OPENROUTER_OPENAI_MODEL", "openai/gpt-4o-mini")),
    OpenRouterProvider("OpenRouter Mistral", os.getenv("OPENROUTER_MISTRAL_MODEL", "mistralai/mistral-small-2603")),
    OpenRouterProvider("OpenRouter Llama", os.getenv("OPENROUTER_LLAMA_MODEL", "meta-llama/llama-4-scout")),
]


def council_providers() -> list:
    """
    Prefer reliable OpenRouter-backed diversity plus local Ollama.
    Direct vendor providers can be enabled once their keys/quotas are healthy.
    """
    providers = []
    if os.getenv("OPENROUTER_API_KEY", "").strip():
        providers.extend(OPENROUTER_PROVIDERS)

    providers.append(OllamaProvider())

    if os.getenv("ENABLE_DIRECT_PROVIDERS", "").lower() in {"1", "true", "yes"}:
        providers.extend([GeminiProvider(), GrokProvider()])

    return providers


COUNCIL_PROVIDERS = council_providers()

ROLE_CATALOG = [
    "Strategist",
    "Critic",
    "Risk Analyst",
    "Domain Expert",
    "Pragmatist",
    "Creative",
    "Implementation Planner",
    "User Advocate",
    "Evidence Reviewer",
]


def _provider_map() -> dict:
    return {provider.provider_name: provider for provider in council_providers()}


def _call_provider(provider, prompt: str) -> dict:
    """Call a single provider with a prompt. Returns structured result."""
    try:
        response = provider.call(prompt)
        return {
            "provider": response.provider,
            "model": response.model,
            "text": response.text,
            "error": response.error,
        }
    except Exception as e:
        return {
            "provider": getattr(provider, "provider_name", provider.__class__.__name__),
            "model": getattr(provider, "model_name", "unknown"),
            "text": "",
            "error": str(e),
        }


def provider_health() -> list:
    """Return lightweight provider availability without making model calls."""
    health = []
    for provider in council_providers():
        missing = []
        if provider.provider_name == "Gemini":
            missing = ["GEMINI_API_KEY"] if not os.getenv("GEMINI_API_KEY") else []
        elif provider.provider_name == "Grok":
            missing = ["XAI_API_KEY"] if not os.getenv("XAI_API_KEY") else []
        elif provider.provider_name.startswith("OpenRouter"):
            missing = ["OPENROUTER_API_KEY"] if not os.getenv("OPENROUTER_API_KEY") else []

        health.append({
            "provider": provider.provider_name,
            "model": provider.model_name,
            "configured": not missing,
            "missing": missing,
            "local": provider.provider_name == "Ollama",
        })
    return health


def _fallback_role(prompt: str, provider_name: str) -> str:
    text = prompt.lower()
    if any(word in text for word in ["risk", "security", "legal", "medical", "privacy", "safety"]):
        defaults = ["Risk Analyst", "Critic", "Pragmatist", "Evidence Reviewer"]
    elif any(word in text for word in ["build", "app", "code", "architecture", "system", "iphone"]):
        defaults = ["Implementation Planner", "Strategist", "Critic", "User Advocate"]
    elif any(word in text for word in ["idea", "creative", "brand", "design"]):
        defaults = ["Creative", "Strategist", "Critic", "Pragmatist"]
    else:
        defaults = ["Strategist", "Critic", "Pragmatist", "Domain Expert"]

    names = [provider.provider_name for provider in council_providers()]
    index = names.index(provider_name) if provider_name in names else 0
    return defaults[index % len(defaults)]


def _parse_role_response(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        return "", ""

    cleaned = text.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
        role = str(data.get("role", "")).strip()
        reason = str(data.get("reason", "")).strip()
    except (TypeError, ValueError):
        first_line = cleaned.splitlines()[0].strip().strip("-:*# ")
        role = first_line[:40]
        reason = ""

    if len(role) > 40:
        role = role[:40].strip()
    return role or "", reason


def _negotiate_roles(prompt: str) -> tuple[dict, list]:
    """
    Autonomous Round 0: each available provider proposes the role it should play.
    The system sanitizes duplicates and falls back only when a provider cannot answer.
    """
    role_prompt = f"""You are joining an autonomous AI council.

The user's task:
{prompt}

Choose the single role YOU should play to make the council most useful.
Do not choose randomly. Choose based on the task and your strengths.

Allowed examples: {", ".join(ROLE_CATALOG)}
You may create a short custom role if it is more appropriate.

Return only JSON:
{{"role":"short role name","reason":"one short reason"}}
"""
    proposals = []

    providers = council_providers()
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {
            executor.submit(_call_provider, provider, role_prompt): provider
            for provider in providers
        }
        for future in as_completed(futures):
            provider = futures[future]
            result = future.result()
            role, reason = _parse_role_response(result.get("text", ""))
            if result.get("error") or not role:
                role = _fallback_role(prompt, provider.provider_name)
                reason = "Fallback role selected because this provider could not propose one."

            proposals.append({
                "provider": provider.provider_name,
                "model": provider.model_name,
                "role": role,
                "reason": reason,
                "error": result.get("error"),
                "autonomous": not bool(result.get("error")),
            })

    used = set()
    roles = {}
    for proposal in proposals:
        role_key = proposal["role"].lower()
        if role_key in used:
            proposal["role"] = _fallback_role(prompt, proposal["provider"])
            role_key = proposal["role"].lower()
        used.add(role_key)
        roles[proposal["provider"]] = proposal["role"]

    return roles, proposals


def _run_round_1(prompt: str, roles: dict | None = None) -> list:
    """ROUND 1: providers answer independently from their autonomous role."""
    roles = roles or {}
    results = []

    def _call(provider):
        role = roles.get(provider.provider_name, _fallback_role(prompt, provider.provider_name))
        role_prompt = f"""Original question:
{prompt}

Your autonomous role: {role}

Answer independently through this role. Be useful, concrete, and non-generic.
Do not mention internal council mechanics."""
        result = _call_provider(provider, role_prompt)
        result["role"] = role
        return result

    providers = council_providers()
    with ThreadPoolExecutor(max_workers=len(providers)) as executor:
        futures = {executor.submit(_call, provider): provider for provider in providers}
        for future in as_completed(futures):
            results.append(future.result())

    return results


def run_parallel_answers(prompt: str) -> dict:
    """Run a fast one-round council for side-by-side answers."""
    roles, proposals = _negotiate_roles(prompt)
    round1_results = _run_round_1(prompt, roles)
    return {
        "mode": "council",
        "role_proposals": proposals,
        "round0_roles": roles,
        "answer": round1_results,
        "round1": round1_results,
        "stages": [
            {"id": "roles", "label": "Autonomous role negotiation", "status": "complete"},
            {"id": "round1", "label": "Independent answers", "status": "complete"},
        ],
    }


def _run_round_2(prompt: str, round1_results: list, roles: dict) -> list:
    """ROUND 2: successful providers critique and improve from their role."""
    successful = [result for result in round1_results if result["text"] and not result["error"]]
    if not successful:
        return []

    provider_by_name = _provider_map()
    results = []

    def _round2_call(provider, provider_result):
        other_answers = "\n\n".join([
            f"**{result['provider']}** as {roles.get(result['provider'], 'Analyst')}:\n{result['text']}"
            for result in successful
            if result["provider"] != provider_result["provider"]
        ])
        role = roles.get(provider.provider_name, "Analyst")
        round2_prompt = f"""Original question:
{prompt}

Your autonomous role: {role}

Your Round 1 answer:
{provider_result['text']}

Other council answers:
{other_answers}

Now improve your answer from your role:
1. Identify the most important gap or weak assumption.
2. Explain what your role sees that others may miss.
3. Provide a stronger revised answer.

Return only the improved answer."""
        result = _call_provider(provider, round2_prompt)
        result["role"] = role
        return result

    with ThreadPoolExecutor(max_workers=len(successful)) as executor:
        futures = {}
        for result in successful:
            provider = provider_by_name.get(result["provider"])
            if provider:
                futures[executor.submit(_round2_call, provider, result)] = provider

        for future in as_completed(futures):
            results.append(future.result())

    return results


def _synthesize(prompt: str, round2_results: list, roles: dict) -> str:
    """ROUND 3: synthesize all improved answers into one final answer."""
    answers_text = "\n\n".join([
        f"**{result['provider']}** as {roles.get(result['provider'], 'Analyst')}:\n{result['text']}"
        for result in round2_results
        if result["text"] and not result["error"]
    ])

    if not answers_text.strip():
        return "No valid responses to synthesize."

    synthesis_prompt = f"""You are synthesizing an autonomous AI council debate.

Original question:
{prompt}

Improved answers:
{answers_text}

Generate a single final answer that:
1. Combines the strongest points.
2. Resolves disagreements intelligently.
3. Is practical and clear.
4. Does not mention providers, model names, or internal mechanics.

Return only the final answer."""

    for provider in council_providers():
        result = _call_provider(provider, synthesis_prompt)
        if result["text"] and not result["error"]:
            return result["text"]

    return answers_text


def _confidence(final_answer: str, round1_results: list, round2_results: list) -> tuple[str, str]:
    successful_round1 = len([result for result in round1_results if result["text"] and not result["error"]])
    successful_round2 = len([result for result in round2_results if result["text"] and not result["error"]])
    if not final_answer or "No valid" in final_answer:
        return "Low", "No provider produced a usable synthesis."
    if successful_round2 >= 3:
        return "High", "At least three providers completed critique and revision."
    if successful_round2 >= 1:
        return "Medium", "Synthesized from the providers that completed critique and revision."
    if successful_round1 >= 1:
        return "Low", "Only independent answers were available; critique did not complete."
    return "Low", "No provider produced a usable answer."


def run_council(prompt: str, mode: str = "council_debate") -> dict:
    """Run autonomous role negotiation, independent answers, critique, and synthesis."""
    roles, proposals = _negotiate_roles(prompt)
    round1_results = _run_round_1(prompt, roles)
    round2_results = _run_round_2(prompt, round1_results, roles)
    final_answer = _synthesize(prompt, round2_results, roles)
    confidence, confidence_reason = _confidence(final_answer, round1_results, round2_results)

    return {
        "mode": mode,
        "round0_roles": roles,
        "role_proposals": proposals,
        "round1": round1_results,
        "round2": round2_results,
        "final": final_answer,
        "final_answer": final_answer,
        "confidence": confidence,
        "confidence_reason": confidence_reason,
        "stages": [
            {"id": "roles", "label": "Autonomous role negotiation", "status": "complete"},
            {"id": "round1", "label": "Independent answers", "status": "complete"},
            {"id": "round2", "label": "Critique and revision", "status": "complete" if round2_results else "partial"},
            {"id": "synthesis", "label": "Final synthesis", "status": "complete" if final_answer else "partial"},
        ],
    }
