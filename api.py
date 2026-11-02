"""Thin HTTP layer: one endpoint that calls summarizer.summarize()."""
from fastapi import FastAPI, HTTPException
from openai import OpenAIError
from pydantic import BaseModel

from summarizer import summarize

app = FastAPI(title="Text Summarizer")


class SummarizeRequest(BaseModel):
    text: str


class SummarizeResponse(BaseModel):
    summary: str
    action_items: list[str]
    model: str
    truncated: bool
    notes: list[str]


@app.post("/summarize", response_model=SummarizeResponse)
def summarize_endpoint(req: SummarizeRequest):
    try:
        return summarize(req.text)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except (RuntimeError, OpenAIError) as err:
        raise HTTPException(status_code=502, detail=f"Model call failed: {err}")
