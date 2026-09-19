"""
The parser: turn the model's raw text into a structured decision.

This is the most important file in 3A and the one an interviewer will push
on, because it is where "the model proposes, our code disposes" actually
happens. The model writes free text. We have to reliably pull out: did it
ask for a tool (and which, with what arguments), or did it give a final
answer, or did it produce garbage we cannot use.

The contract we ask the model to follow (defined in the system prompt in
react.py) is one of these two shapes per turn:

    Thought: <reasoning>
    Action: <tool name>
    Action Input: <a JSON object>

or:

    Thought: <reasoning>
    Final Answer: <the answer to give the user>

Real 3B models break this contract constantly: extra prose, markdown code
fences around the JSON, single quotes instead of double, a trailing comma,
both an Action and a Final Answer in the same turn. A brittle parser turns
every one of those into a crash. So this parser is deliberately defensive,
and every branch returns something the loop can act on rather than throwing.
"""

import re
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedStep:
    """
    The structured result of parsing one model turn.

    Exactly one of these situations is true, and the loop branches on it:
      - is_final == True            -> the model is done; final_answer is set.
      - action is not None          -> the model wants a tool; run it.
      - both are empty (error set)  -> we could not parse; feed the error back.
    """
    thought: Optional[str] = None
    action: Optional[str] = None
    action_input: Optional[dict] = None
    is_final: bool = False
    final_answer: Optional[str] = None
    error: Optional[str] = None


def _extract_after(label, text):
    """
    Grab the text following a label like 'Action:' up to the next known
    label or end of string. Case-insensitive on the label. Returns None if
    the label is not present.
    """
    # The next-label lookahead stops us from swallowing the Action Input
    # into the Action, etc. We list every label that can follow.
    pattern = (
        rf"{label}\s*:\s*(.*?)"
        r"(?=\n\s*(?:Thought|Action Input|Action|Final Answer|Observation)\s*:|$)"
    )
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _parse_json_loose(raw):
    """
    Turn the Action Input text into a dict, tolerating the mistakes a small
    model actually makes. Returns (dict, None) on success or (None, reason).
    """
    if raw is None:
        return None, "no Action Input found"

    text = raw.strip()

    # Models love wrapping JSON in ```json ... ``` fences. Strip them.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    # First try: clean parse.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "Action Input was valid JSON but not an object"
    except json.JSONDecodeError:
        pass

    # Second try: swap single quotes for double. Small models write
    # {'city': 'Zephyria'} which is valid Python but not valid JSON.
    try:
        parsed = json.loads(text.replace("'", '"'))
        if isinstance(parsed, dict):
            return parsed, None
    except json.JSONDecodeError:
        pass

    return None, f"could not parse Action Input as JSON: {raw!r}"


def parse(text):
    """
    Parse one raw model completion into a ParsedStep. This function never
    raises on bad model output; it returns a ParsedStep whose .error the
    loop can feed back to the model as an Observation so it can retry.
    """
    thought = _extract_after("Thought", text)

    # Final Answer wins if present. We check it first because a well-behaved
    # model that is finished should not also be asking for a tool, and if it
    # confusingly does both, treating it as finished is the safe choice.
    final = _extract_after("Final Answer", text)
    if final is not None and final != "":
        return ParsedStep(thought=thought, is_final=True, final_answer=final)

    # Otherwise look for an action.
    action = _extract_after("Action", text)
    if action is not None and action != "":
        # Clean common noise: backticks, quotes around the tool name.
        action = action.strip().strip("`").strip('"').strip("'")
        raw_input = _extract_after("Action Input", text)
        args, err = _parse_json_loose(raw_input)
        if err is not None:
            return ParsedStep(
                thought=thought,
                action=action,
                error=err,
            )
        return ParsedStep(thought=thought, action=action, action_input=args)

    # Neither a final answer nor a usable action. Tell the loop we are stuck
    # so it can nudge the model back onto the format.
    return ParsedStep(
        thought=thought,
        error=(
            "response contained no valid Action or Final Answer. "
            "You must output either an Action with Action Input, "
            "or a Final Answer."
        ),
    )


if __name__ == "__main__":
    # Exercise the parser against the messy shapes a real 3B model emits.
    # Run: python src/agents/parser.py
    samples = [
        # clean action
        'Thought: I should add these.\nAction: calculator\nAction Input: {"expression": "2 + 2"}',
        # single-quoted JSON (Python dict style)
        "Thought: look it up.\nAction: city_lookup\nAction Input: {'city': 'Zephyria'}",
        # JSON wrapped in a code fence
        'Action: calculator\nAction Input: ```json\n{"expression": "9*9"}\n```',
        # final answer
        "Thought: I now know the result.\nFinal Answer: The population is 812000.",
        # garbage
        "I think the answer is probably around forty-something.",
    ]
    for i, s in enumerate(samples, 1):
        print(f"--- sample {i} ---")
        print(parse(s))
        print()
