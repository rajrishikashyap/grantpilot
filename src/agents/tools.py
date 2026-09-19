"""
The tool registry.

A tool is just a Python function the agent is allowed to call, wrapped with
a name and a plain-English description. The description matters as much as
the code: it is the ONLY thing the model sees about the tool, so it is how
the model decides when to use it. Bad description, wrong tool choice.

Two ideas live here:
  1. A Tool dataclass  = (name, description, the actual function).
  2. A registry        = a dict {name: Tool} the loop looks tools up in.

For 3A we register two TOY tools so we can watch the reason/act/observe
cycle work in isolation. In 3C we throw these away and register the real
ones (score_budget, the RAG search, etc). The engine will not change at
all, only the contents of this registry. That separation is the point.
"""

from dataclasses import dataclass
from typing import Callable
import json


@dataclass
class Tool:
    name: str
    description: str
    func: Callable  # takes a dict of arguments, returns a string


# ---------------------------------------------------------------------------
# TOY TOOL 1: a calculator.
# Forces a tool call for any arithmetic the model should not do in its head
# (and a 3B model gets arithmetic wrong constantly, so this is a fair test).
# ---------------------------------------------------------------------------
def _calculator(args):
    """
    args is a dict like {"expression": "37 * 12"}.
    We eval ONLY over a tiny safe namespace. Never eval raw user text in
    real code; here the input comes from our own model in a sandbox and the
    namespace is locked to numbers and operators, so it is contained.
    """
    expr = args.get("expression", "")
    try:
        # Locked-down eval: no builtins, nothing but the expression itself.
        result = eval(expr, {"__builtins__": {}}, {})
        return f"{expr} = {result}"
    except Exception as e:
        return f"Calculator error on '{expr}': {e}"


# ---------------------------------------------------------------------------
# TOY TOOL 2: a fake city lookup.
# A stand-in for any "go fetch a fact the model does not know" tool. It is
# hard-coded, which is exactly why it is a good test: the model CANNOT know
# these values from training, so if it answers correctly it can only have
# done so by calling the tool. That proves the loop actually routed data.
# ---------------------------------------------------------------------------
_FAKE_CITY_DB = {
    "zephyria": {"population": 812000, "founded": 1834},
    "novapolis": {"population": 2450000, "founded": 1901},
    "marrowfen": {"population": 47000, "founded": 1622},
}


def _city_lookup(args):
    """args is a dict like {"city": "Zephyria"}."""
    city = args.get("city", "").strip().lower()
    if city in _FAKE_CITY_DB:
        info = _FAKE_CITY_DB[city]
        return json.dumps(info)
    return f"No record found for city '{city}'."


# ---------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------
TOY_TOOLS = {
    "calculator": Tool(
        name="calculator",
        description=(
            "Evaluate a arithmetic expression. "
            'Action Input must be JSON like {"expression": "37 * 12"}.'
        ),
        func=_calculator,
    ),
    "city_lookup": Tool(
        name="city_lookup",
        description=(
            "Look up population and founding year for a city. "
            'Action Input must be JSON like {"city": "Zephyria"}. '
            "Only knows the cities Zephyria, Novapolis, and Marrowfen."
        ),
        func=_city_lookup,
    ),
}


def render_tools(registry):
    """
    Turn the registry into the text block we paste into the system prompt.
    This is literally the model's entire knowledge of what it can do, so we
    format it clearly: one line per tool, name then description.
    """
    lines = []
    for tool in registry.values():
        lines.append(f"- {tool.name}: {tool.description}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Confirm both toy tools work as plain functions, no model involved.
    # Run: python src/agents/tools.py
    print(_calculator({"expression": "37 * 12"}))
    print(_city_lookup({"city": "Marrowfen"}))
    print("\nRendered for prompt:\n" + render_tools(TOY_TOOLS))
