"""
Thin wrapper around a local Ollama model.

Send a prompt to Ollama and get raw text back. Nothing agentic lives here, so
the ReAct loop never has to know how Ollama works, and swapping the model or
the host is a one-line change (now via environment variables, for Docker).

We use requests against the Ollama HTTP API rather than the ollama python
package, so there is one less dependency and the exact bytes on the wire are
visible. Ollama serves on http://localhost:11434 by default.

Environment overrides (used by the Docker image and deploy):
  OLLAMA_URL    full generate endpoint (default http://localhost:11434/api/generate)
  OLLAMA_MODEL  model name (default qwen2.5:3b)
"""

import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")


def call_llm(prompt, temperature=0.0, stop=None):
    """
    Send one prompt to the local model, return the raw completion text.

    temperature=0.0 makes the model as deterministic as it can be, which a
    ReAct parser prefers. stop halts generation on a given string; the loop
    uses stop=["Observation:"] so the model cannot hallucinate a tool result.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if stop is not None:
        payload["options"]["stop"] = stop

    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    response.raise_for_status()
    return response.json()["response"]


if __name__ == "__main__":
    print("Testing connection to Ollama at", OLLAMA_URL)
    out = call_llm("Reply with exactly the word: ready")
    print("Model said:", repr(out.strip()))
