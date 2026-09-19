"""
The ReAct engine: the reason/act/observe loop itself.

This is the four-beat cycle in plain Python. Read run_agent from top to
bottom and you have the entire mechanism that CrewAI, LangGraph, and every
"agent framework" wraps. There is no hidden magic below this file.

The loop:
  1. Build a prompt: system instructions + tool list + the question +
     everything that has happened so far (the "scratchpad").
  2. Call the model. Stop generation as soon as it writes "Observation:"
     so it cannot invent the tool result.
  3. Parse the model's text into a ParsedStep.
  4. Branch:
       - Final Answer  -> return it, we are done.
       - Action        -> run the real tool, format its return as an
                          Observation, append it to the scratchpad, loop.
       - Error         -> append the error as an Observation, loop (the
                          model gets one more try to fix its format).
  5. Stop after max_steps no matter what, so a confused model cannot spin
     forever. The step cap is the agent's seatbelt.
"""

from .llm import call_llm
from .parser import parse


# The system prompt. This teaches the model the ReAct contract. Everything
# the model knows about how to behave is in here plus the tool list. Note
# the explicit format block: small models need the shape spelled out and an
# example, or they improvise and the parser has nothing to grab.
SYSTEM_PROMPT = """You are a careful assistant that solves problems step by step using tools.

You have access to these tools:
{tool_list}

To solve the problem, work in a strict loop. On each turn output EXACTLY ONE of these two forms.

Form 1, to use a tool:
Thought: <your reasoning about what to do next>
Action: <one tool name from the list above>
Action Input: <a single JSON object with the tool's arguments>

Form 2, when you have the final answer:
Thought: <your reasoning that you now have enough to answer>
Final Answer: <the answer for the user>

Rules:
- Output only ONE Thought and then either ONE Action (with Action Input) or ONE Final Answer. Never both.
- Action Input must be valid JSON on a single line.
- Do NOT write the Observation yourself. After your Action, stop. The system will run the tool and give you the Observation.
- Do not invent tool results. Use a tool when you need a fact or a calculation.

Begin.

Question: {question}
{scratchpad}"""


def _build_prompt(question, scratchpad, registry):
    from .tools import render_tools
    return SYSTEM_PROMPT.format(
        tool_list=render_tools(registry),
        question=question,
        scratchpad=scratchpad,
    )


def run_agent(question, registry, max_steps=6, verbose=True):
    """
    Run the ReAct loop until the model gives a Final Answer or we hit
    max_steps.

    question  : the user's task, a string.
    registry  : dict {name: Tool}, the tools the agent may use.
    max_steps : the seatbelt. 6 is plenty for the toy tests.
    verbose   : print every beat so you can watch reason/act/observe happen.

    Returns the final answer string, or a give-up message if the cap is hit.
    """
    # The scratchpad is the agent's working memory: the running transcript
    # of its own Thoughts/Actions and the Observations we fed back. It is
    # what makes step N aware of what happened in step N-1. This is the
    # entire "memory" of a ReAct agent, nothing more.
    scratchpad = ""

    for step in range(1, max_steps + 1):
        if verbose:
            print(f"\n{'='*60}\nSTEP {step}\n{'='*60}")

        prompt = _build_prompt(question, scratchpad, registry)

        # Stop the model the instant it tries to write an Observation, so
        # the tool result comes from OUR code, never the model's imagination.
        raw = call_llm(prompt, temperature=0.0, stop=["Observation:"])

        if verbose:
            print("MODEL OUTPUT:")
            print(raw.rstrip())

        step_result = parse(raw)

        # --- Branch 1: the model is finished. ---
        if step_result.is_final:
            if verbose:
                print(f"\n>>> FINAL ANSWER reached at step {step}")
            return step_result.final_answer

        # --- Branch 2: the model gave us an unusable response. ---
        # Feed the error back as an Observation and let it retry next loop.
        if step_result.error is not None and step_result.action is None:
            observation = f"Error: {step_result.error}"
            if verbose:
                print(f"\nOBSERVATION (parse error): {observation}")
            scratchpad += f"\n{raw.rstrip()}\nObservation: {observation}\n"
            continue

        # --- Branch 3: the model asked for a tool. ---
        tool_name = step_result.action
        tool_args = step_result.action_input

        if tool_name not in registry:
            # It asked for a tool that does not exist. Tell it so.
            observation = (
                f"Error: unknown tool '{tool_name}'. "
                f"Available tools: {', '.join(registry.keys())}."
            )
        elif step_result.error is not None:
            # Tool name was fine but the Action Input would not parse.
            observation = f"Error: {step_result.error}"
        else:
            # The real dispatch: OUR code runs the real function.
            tool = registry[tool_name]
            try:
                observation = tool.func(tool_args)
            except Exception as e:
                observation = f"Error running tool '{tool_name}': {e}"

        if verbose:
            print(f"\nACTION: {tool_name}  INPUT: {tool_args}")
            print(f"OBSERVATION: {observation}")

        # Append this whole beat to the scratchpad and loop. Note we append
        # the model's own raw output too, so its next turn sees its prior
        # reasoning, not just the observation.
        scratchpad += f"\n{raw.rstrip()}\nObservation: {observation}\n"

    # Fell out of the loop: the model never finished within the step cap.
    return (
        f"[Agent stopped: reached the {max_steps}-step limit without a "
        f"Final Answer. This usually means the task was too hard, the tools "
        f"were insufficient, or the model got stuck in a loop.]"
    )
