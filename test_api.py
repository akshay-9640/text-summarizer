import json

import pytest
from fastapi.testclient import TestClient

import summarizer
from api import app

client = TestClient(app)

MEETING = (
    "The team met to plan the Q3 launch. Sara will send the final designs by Friday. "
    "We need to book the venue before the end of the month. Raj should update the budget sheet. "
    "Everyone agreed the launch date is fixed."
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")


def test_summarize_returns_expected_json_shape():
    r = client.post("/summarize", json={"text": MEETING})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"summary", "action_items", "model", "truncated", "notes"}
    assert body["model"] == "mock"
    assert body["truncated"] is False
    assert len(body["action_items"]) == 3
    assert all(isinstance(i, str) and i for i in body["action_items"])


def test_empty_text_is_rejected():
    for text in ["", "   \n  "]:
        assert client.post("/summarize", json={"text": text}).status_code == 400
    assert client.post("/summarize", json={}).status_code == 422


def test_long_text_is_truncated_and_bad_model_json_is_retried(monkeypatch):
    monkeypatch.delenv("MOCK_LLM")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    good = {"summary": "A long text.", "action_items": ["Read it.", "Trim it.", "Send it."], "actions_inferred": True}
    replies = iter(["this is not json", json.dumps(good)])
    sent = []

    def fake_chat(model, messages):
        sent.append(messages[1]["content"])
        return next(replies)

    monkeypatch.setattr(summarizer, "_chat", fake_chat)
    r = client.post("/summarize", json={"text": "word " * 5000})
    assert r.status_code == 200
    body = r.json()
    assert body["truncated"] is True
    assert body["model"] == "test-model"
    assert body["action_items"] == good["action_items"]
    assert len(sent) == 2  # first reply was rejected, then retried
    assert len(sent[0]) < summarizer.MAX_CHARS + 200
    assert any("only the first" in n for n in body["notes"])
    assert any("best-effort" in n for n in body["notes"])
