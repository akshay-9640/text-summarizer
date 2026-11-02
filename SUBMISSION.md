# Take-home: Text Summarizer API

## What I built

- A small Python + FastAPI service with one endpoint, `POST /summarize`. It takes `{"text": "..."}` and returns `{"summary", "action_items", "model", "truncated", "notes"}`.
- It calls an LLM through the OpenAI chat completions client. The API key, model name, and an optional base URL come from environment variables, so any OpenAI-compatible provider works. I ran it through Fireworks with `gpt-oss-120b` (the default I chose) and `muse-spark-open`.
- Structure: `summarizer.py` (main logic), `prompts.py` (prompts), `api.py` (thin HTTP layer), `test_api.py` (3 tests).
- How it works:
  - It strips the input. Empty input returns a 400.
  - Input over 12,000 characters is truncated, and the response says so (`truncated: true` plus a note).
  - It sends the system and user prompts below, with JSON mode turned on.
  - The code checks the reply: valid JSON, a non-empty summary, exactly 3 non-empty action items. If the check fails, it retries once, then returns a 502.
  - If the model reports `actions_inferred: true`, the response notes that some items are best-effort.
- Mock mode: with no API key (or `MOCK_LLM=1`), simple text rules stand in for the model, so the API can be demoed offline. The response shows `"model": "mock"`.

## Prompts

System prompt (from `prompts.py`):

```
You summarize text and extract action items.
Reply with JSON only, in exactly this shape:
{"summary": "...", "action_items": ["...", "...", "..."], "actions_inferred": false}

Rules:
- summary: 2 to 4 sentences, plain language, only facts stated in the text.
- action_items: exactly 3 items. Each item is one sentence that starts with a verb (for example "Send", "Schedule", "Review").
- If the text says who owns an action, keep that name at the end in brackets, for example "Send the report by Friday (owner: Sara)."
- If the text has fewer than 3 clear actions, fill the rest with sensible next steps based on the text and set "actions_inferred" to true.
- Do not invent names, dates, or numbers that are not in the text.
```

User prompt (`{text}` is replaced with the input):

```
Summarize the text below and extract 3 action items.

Text:
"""
{text}
"""
```

Settings: `temperature=0.2`, `response_format={"type": "json_object"}`.

## How I used AI tools

- I used Claude Code (an AI coding assistant) for this exercise. I gave it the task and my constraints: one main module, one prompt module, a thin API layer, mock mode, the edge cases to handle, 2 to 3 tests, and nothing beyond that (no database, auth, or frontend).
- It wrote the code, tests, and README, and ran the tests and the test inputs against my Fireworks key.
- I read the real model outputs, picked the two problems below to fix, and had it re-run the same inputs to confirm the fixes. All outputs from both runs are in `sample_runs.txt`.

## What didn't work at first and how I adjusted

I ran 4 inputs through both models: a meeting note, a very short text ("Lovely weather today."), a factual text with no actions, and a 30,302-character text. All 8 calls returned valid JSON with 3 action items, but two things were wrong:

- **A note in the response was false.** The long text has one clear action ("Priya must review the escalation policy before the next release"), but the note said "The text has no clear action items." Both models set `actions_inferred: true` because they found fewer than 3 actions, not zero. I changed the note to "Fewer than 3 clear action items were found; some are best-effort suggestions."
- **Action items lost who owns the task.** The input said "Sara will send the final designs by Friday", and both models returned "Send the final designs by Friday." I added a prompt rule to keep the owner in brackets at the end, so the item still starts with a verb. After the change, both models returned "Send the final designs by Friday (owner: Sara)." and "Update the budget sheet (owner: Raj).", and "(owner: Priya)" on the long text.
- I also compared the two models on the same inputs: `gpt-oss-120b` took about 2 seconds per call and `muse-spark-open` 10 to 17 seconds, with similar output quality. I kept `gpt-oss-120b` as the default.

## What I would improve with more time

- Chunk long text and merge the chunk summaries, instead of truncating at 12,000 characters.
- Check the format rules in code, not only in the prompt. For example, on the short input after the fixes, `gpt-oss-120b` returned items without a final period ("Enjoy the pleasant weather"), and nothing in the code checks the 2-to-4-sentence summary limit.
- Log when the one retry on bad JSON happens. Right now I can't tell from the runs whether it ever fired.
- Build a small evaluation set of sample texts with expected properties, to compare prompts and models in a repeatable way instead of by reading outputs.
- Add a timeout and clearer error messages for slow or failing provider calls.

## How to run

See `README.md`. Short version: `pip install -r requirements.txt`, then `MOCK_LLM=1 uvicorn api:app` for offline mode, or put your key in `.env` (copy `.env.example`) for a real model. Run `pytest -q` for the tests.
