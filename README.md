# Text Summarizer API

A small FastAPI service. Send it a block of text; it uses an LLM to return a short summary and exactly 3 action items as JSON.

## Files

| File | What it does |
|------|--------------|
| `summarizer.py` | Main logic: cleans input, truncates long text, calls the model (or the mock), checks the JSON it returns. |
| `prompts.py` | The system and user prompts. |
| `api.py` | Thin HTTP layer: `POST /summarize`. |
| `test_api.py` | 3 tests: JSON shape, empty input, long input + bad model JSON. |

## Setup

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

With a real model (any OpenAI-compatible chat completions API):

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o-mini          # optional, this is the default
# export OPENAI_BASE_URL=https://...     # optional, for other OpenAI-compatible providers
uvicorn api:app --reload
```

Example with Fireworks (OpenAI-compatible):

```bash
export OPENAI_API_KEY=<your Fireworks key>
export OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1
export OPENAI_MODEL=accounts/fireworks/models/gpt-oss-120b
uvicorn api:app --reload
```

Or keep the settings in a `.env` file (git ignores it):

```bash
cp .env.example .env      # then paste your key into .env
set -a; source .env; set +a
uvicorn api:app --reload
```

Offline mock mode (no key needed): leave `OPENAI_API_KEY` unset, or set `MOCK_LLM=1`. The mock uses simple text rules, not AI, and reports `"model": "mock"`.

```bash
MOCK_LLM=1 uvicorn api:app --reload
```

Call it:

```bash
curl -s -X POST localhost:8000/summarize \
  -H 'Content-Type: application/json' \
  -d '{"text": "The team met to plan the Q3 launch. Sara will send the final designs by Friday. We need to book the venue before the end of the month. Raj should update the budget sheet. Everyone agreed the launch date is fixed."}'
```

Interactive docs: http://localhost:8000/docs

## Response

```json
{
  "summary": "2 to 4 sentences.",
  "action_items": ["Verb ...", "Verb ...", "Verb ..."],
  "model": "gpt-4o-mini",
  "truncated": false,
  "notes": []
}
```

`notes` explains anything unusual about the result:

- Input longer than 12,000 characters is truncated, and `truncated` is `true`.
- Input under 15 words gets a note that the output may only restate it.
- If the text has no clear actions, the model fills in best-effort items and a note says so.

Errors: empty or whitespace-only text returns `400`. A missing `text` field returns `422`. If the model call fails, or the model returns invalid JSON twice in a row, the API returns `502`.

## Test

```bash
pytest -q
```

The tests run offline. They use the mock, or a fake model reply.
