"""Generates code from a student's one-shot prompt for the training module.

Backend is selectable via core.settings.Settings.LLM_PROVIDER:
  - "ollama"    (default) — local, free. Point OLLAMA_BASE_URL at your
    Ollama install (default http://localhost:11434) and make sure
    OLLAMA_MODEL is pulled: `ollama pull qwen2.5-coder:7b`.
  - "anthropic" — calls the Anthropic Messages API directly via httpx (no
    SDK dependency). Needs ANTHROPIC_API_KEY. Switch LLM_PROVIDER to this
    once you have API credits — no other code changes needed.

Both call httpx directly rather than pulling in a provider SDK, same
pattern as utils/code_runner.py talking to Piston.
"""

from typing import Any

import httpx

from core.settings import Settings

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


def is_configured() -> bool:
    if Settings.LLM_PROVIDER == "anthropic":
        return bool(Settings.ANTHROPIC_API_KEY)
    return bool(Settings.OLLAMA_BASE_URL)


def _build_prompt(*, problem_title: str, problem_description: str, constraints: str | None,
                   language: str, student_prompt: str) -> str:
    parts = [
        f"You are solving a coding problem titled \"{problem_title}\" in {language}.",
        "Problem statement:",
        problem_description or "(no description provided)",
    ]
    if constraints:
        parts.append(f"Constraints:\n{constraints}")
    parts.append(
        "A student wrote the following instructions for how they want the solution "
        "approached. Follow their intent as closely as possible even if it isn't the "
        "most efficient approach — the point of this exercise is for the student to "
        "debug the result, not to get a perfect answer:\n"
        f"\"\"\"\n{student_prompt}\n\"\"\""
    )
    parts.append(
        "Output ONLY the code, no explanation, no markdown code fences, "
        "no commentary before or after."
    )
    return "\n\n".join(parts)


async def _generate_via_anthropic(user_message: str) -> dict[str, Any]:
    if not Settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured on the server")

    async with httpx.AsyncClient(
        base_url=ANTHROPIC_BASE_URL,
        headers={
            "x-api-key": Settings.ANTHROPIC_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        timeout=60.0,
    ) as client:
        resp = await client.post(
            "/messages",
            json={
                "model": Settings.ANTHROPIC_MODEL,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    code = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    usage = data.get("usage", {})
    return {
        "code": code.strip(),
        "model": data.get("model", Settings.ANTHROPIC_MODEL),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }


async def _generate_via_ollama(user_message: str) -> dict[str, Any]:
    async with httpx.AsyncClient(base_url=Settings.OLLAMA_BASE_URL, timeout=120.0) as client:
        resp = await client.post(
            "/api/chat",
            json={
                "model": Settings.OLLAMA_MODEL,
                "messages": [{"role": "user", "content": user_message}],
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    code = (data.get("message") or {}).get("content", "")
    return {
        "code": code.strip(),
        "model": data.get("model", Settings.OLLAMA_MODEL),
        "input_tokens": data.get("prompt_eval_count"),
        "output_tokens": data.get("eval_count"),
    }


async def generate_code_from_prompt(
    *,
    problem_title: str,
    problem_description: str,
    constraints: str | None,
    language: str,
    student_prompt: str,
) -> dict[str, Any]:
    """Returns {"code": str, "model": str, "input_tokens": int, "output_tokens": int}."""
    if not is_configured():
        raise RuntimeError(
            f"LLM_PROVIDER={Settings.LLM_PROVIDER!r} is not configured on the server"
        )

    user_message = _build_prompt(
        problem_title=problem_title,
        problem_description=problem_description,
        constraints=constraints,
        language=language,
        student_prompt=student_prompt,
    )

    if Settings.LLM_PROVIDER == "anthropic":
        return await _generate_via_anthropic(user_message)
    return await _generate_via_ollama(user_message)
