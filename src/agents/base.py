"""
The Agent base class.

An agent is a thin bundle of three things over the ReAct engine:
  - a name (for logging and orchestration later, in Phase 4),
  - a role (the system-prompt persona that gives it a job),
  - a tool registry (the tools this agent, and only this agent, may use).

.run(task) just calls the engine with those. There is deliberately almost
nothing here: the intelligence lives in the role text and the tools, not in
this class. Every one of the five agents (Budget, Reviewer, Drafting,
Eligibility, Coordinator) is an instance of this same class with a different
role and different tools. That uniformity is the whole design.
"""

from .react import run_agent


class Agent:
    def __init__(self, name, role, registry, max_steps=6):
        self.name = name
        self.role = role
        self.registry = registry
        self.max_steps = max_steps

    def run(self, task, verbose=True):
        """Run this agent on a task string, return its final answer."""
        if verbose:
            print(f"\n########## AGENT: {self.name} ##########")
            print(f"TASK: {task}")
        return run_agent(
            task,
            self.registry,
            max_steps=self.max_steps,
            verbose=verbose,
            role=self.role,
        )

    def __repr__(self):
        return f"Agent(name={self.name!r}, tools={list(self.registry)})"
