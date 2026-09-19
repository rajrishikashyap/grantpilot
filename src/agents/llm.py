"""
Thin wrapper around a local Ollama model.

The whole job of this file: send a prompt string to Qwen 2.5 3B running
locally, get raw text back. Nothing agentic lives here. Keeping the model
call isolated means the ReAct loop never has to know how Ollama works, and
if we ever swap the model (Llama 3.2 3B fallback) we change only this file.

We use requests against the Ollama HTTP API rather than the ollama python
package, so there is one less dependency and you can see the exact bytes on
the wire. Ollama serves on http://localhost:11434 by default.
"""

import requests

# Where the local Ollama server listens. Change the model name here if you
# ever fall back to llama3.2:3b.
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


def call_llm(prompt, temperature=0.0, stop=None):
    """
    Send one prompt to the local model, return the raw completion text.

    temperature=0.0 makes the model as deterministic as it can be. We want
    that for a ReAct agent: creative sampling produces creative (broken)
    action formats, and a parser hates surprises. Low temperature keeps the
    Thought/Action structure stable.

    stop is a list of strings that, when the model generates them, halt
    generation. We use this in the loop to stop the model right after it
    writes an Observation line, so it cannot hallucinate the tool result
    itself. That hallucination is the single most common ReAct failure, and
    the stop token is how we prevent it at the source.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,          # we want the full answer in one response
        "options": {
            "temperature": temperature,
        },
    }
    if stop is not None:
        payload["options"]["stop"] = stop

    # timeout is generous because a 3B model on a GTX 1650 is not fast.
    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()

    # Ollama returns the completion under the "response" key.
    return data["response"]


if __name__ == "__main__":
    # Quick sanity check: is Ollama up and is the model answering at all?
    # Run: python src/agents/llm.py
    print("Testing connection to local Ollama...")
    out = call_llm("Reply with exactly the word: ready")
    print("Model said:", repr(out.strip()))
