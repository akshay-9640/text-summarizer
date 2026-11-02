"""Core logic: clean the input, ask the model (or the offline mock), check the JSON it returns."""
import json
import os
import re
import textwrap

from openai import OpenAI

from prompts import SYSTEM_PROMPT, USER_PROMPT

# shortcut: long input is truncated, not chunked; chunk and merge summaries if long documents matter
MAX_CHARS = 12_000
SHORT_WORDS = 15


def summarize(text: str) -> dict:
    """Return {summary, action_items, model, truncated, notes}. Raises ValueError on empty text."""
    text = (text or "").strip()
    if not text:
        raise ValueError("text is empty")

    notes = []
    truncated = len(text) > MAX_CHARS
    if truncated:
        notes.append(f"Input was {len(text)} characters; only the first {MAX_CHARS} were summarized.")
        text = text[:MAX_CHARS]
    if len(text.split()) < SHORT_WORDS:
        notes.append("Input is very short; the summary and action items may only restate it.")

    if os.getenv("MOCK_LLM") == "1" or not os.getenv("OPENAI_API_KEY"):
        model, result = "mock", _mock(text)
    else:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        result = _ask_llm(text, model)

    if result["actions_inferred"]:
        notes.append("Fewer than 3 clear action items were found; some are best-effort suggestions.")
    return {
        "summary": result["summary"],
        "action_items": result["action_items"],
        "model": model,
        "truncated": truncated,
        "notes": notes,
    }


def _ask_llm(text: str, model: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT.format(text=text)},
    ]
    for _ in range(2):  # one retry if the model breaks the JSON contract
        try:
            return parse_reply(_chat(model, messages))
        except ValueError as err:
            error = err
    raise RuntimeError(f"Model did not return valid JSON after 2 tries: {error}")


def _chat(model: str, messages: list) -> str:
    # OpenAI() reads OPENAI_API_KEY, and OPENAI_BASE_URL for other OpenAI-compatible providers.
    reply = OpenAI().chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return reply.choices[0].message.content or ""


def parse_reply(raw: str) -> dict:
    """Check the model's JSON against the contract. Raises ValueError if it does not match."""
    data = json.loads(raw)  # JSONDecodeError is a ValueError
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    summary, items = data.get("summary"), data.get("action_items")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("summary is missing")
    if not isinstance(items, list) or len(items) != 3 or not all(isinstance(i, str) and i.strip() for i in items):
        raise ValueError("action_items must be exactly 3 non-empty strings")
    return {
        "summary": summary.strip(),
        "action_items": [i.strip() for i in items],
        "actions_inferred": bool(data.get("actions_inferred")),
    }


ACTION_HINT = re.compile(r"\b(should|must|need to|needs to|will|please)\b", re.IGNORECASE)
FILLERS = [
    "Review the full text for other next steps.",
    "Confirm who owns each next step.",
    "Schedule a check-in to track progress.",
]


def _mock(text: str) -> dict:
    """Offline stand-in with no AI: simple rules so the API can be demoed without a key."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    summary = textwrap.shorten(" ".join(sentences[:2]), 400)
    found = [s for s in sentences if ACTION_HINT.search(s)][:3]
    items = [f"Follow up on: {s.rstrip('.!?')}." for s in found]
    items += FILLERS[: 3 - len(items)]
    return {"summary": summary, "action_items": items, "actions_inferred": len(found) < 3}
