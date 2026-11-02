"""Prompts sent to the model. Kept in one place so they are easy to read and change."""

SYSTEM_PROMPT = """You summarize text and extract action items.
Reply with JSON only, in exactly this shape:
{"summary": "...", "action_items": ["...", "...", "..."], "actions_inferred": false}

Rules:
- summary: 2 to 4 sentences, plain language, only facts stated in the text.
- action_items: exactly 3 items. Each item is one sentence that starts with a verb (for example "Send", "Schedule", "Review").
- If the text says who owns an action, keep that name at the end in brackets, for example "Send the report by Friday (owner: Sara)."
- If the text has fewer than 3 clear actions, fill the rest with sensible next steps based on the text and set "actions_inferred" to true.
- Do not invent names, dates, or numbers that are not in the text."""

USER_PROMPT = """Summarize the text below and extract 3 action items.

Text:
\"\"\"
{text}
\"\"\""""
