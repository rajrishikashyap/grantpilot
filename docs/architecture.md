# GrantPilot System Architecture

**Phase 0 deliverable.** This document defines the five agents, their tools, the data flow between them, and exactly where the two ML models plug in. It is the contract the rest of the build follows.

---

## 1. What GrantPilot does (one paragraph)

A researcher or nonprofit pastes in a funding call and their own profile. GrantPilot decides whether they are eligible, and if so it drafts a compliant proposal, validates its budget against funded norms, and scores the draft the way a review panel would, looping draft and review until the score clears a threshold or a cap is hit. The output is a cited eligibility verdict, a drafted proposal, a budget report, and a panel-style score with feedback. Everything runs locally and free.

---

## 2. Why five agents (the load-bearing rationale)

The work splits into five genuinely distinct jobs, and two of them form a feedback loop. One prompt cannot hold all four responsibilities and also critique its own output well. Separation is what makes each step reliable and inspectable.

| # | Agent | Its one job | Could it fold into another? |
|---|---|---|---|
| 1 | **Coordinator** | Decompose the request, decide which agents run and in what order, gate the flow | No, it is the control plane |
| 2 | **Eligibility** | Decide qualify or disqualify against the call's rules, with citations | No, it gates everything downstream |
| 3 | **Drafting** | Assemble proposal sections grounded in the call and the user's profile | No, it is the generative core |
| 4 | **Budget-Compliance** | Validate figures against the cap, flag anomalous line items | No, it runs a real ML model |
| 5 | **Reviewer** | Score the draft against published criteria, send feedback back to Drafting | No, it is the quality loop |

**The load-bearing relationships:** Eligibility gates Drafting (do not draft if disqualified). Reviewer feeds back into Drafting (the Reflection loop). Remove the multi-agent structure and you lose both the gate and the loop, the two things that make the output trustworthy.

---

## 3. The five agents in detail

Each agent is a **ReAct loop** (reason, act, observe, capped at N steps) running on local Qwen 2.5 3B, with its own set of tools.

### 3.1 Coordinator
- **Input:** the user's request (funding call plus applicant profile).
- **Tools:** the other four agents (its actions are `run_eligibility()`, `run_drafting()`, `run_budget()`, `run_reviewer()`).
- **Logic:** run Eligibility first. If disqualified, stop and return the verdict. If eligible, run Drafting, then Budget, then Reviewer, managing the Reviewer and Drafting loop under an iteration cap.
- **Pattern:** ReAct plus a touch of Plan-and-Execute (it plans the high-level route up front).
- **Output:** the assembled final result.

### 3.2 Eligibility Agent
- **Input:** call ID plus applicant profile.
- **Tools:** `search_rules(call, query)` for RAG over the call's rule documents (ChromaDB), and `get_applicant_profile()`.
- **Logic:** fetch the relevant rules, fetch the applicant facts, reason to a hard qualify or disqualify with cited rule text.
- **Output:** `{eligible: bool, reasons: [...], citations: [...]}`.
- **No ML model.** Pure RAG plus reasoning. Citations come from observed rule text, which kills hallucination.

### 3.3 Drafting Agent
- **Input:** call requirements plus applicant profile (plus Reviewer feedback on later loops).
- **Tools:** `search_call_requirements(section)` (RAG), and `get_applicant_work()`.
- **Logic:** assemble each required proposal section, grounded in real requirements and the user's past work. On feedback loops, revise the weak sections the Reviewer named.
- **Output:** a structured draft (sections plus budget table).

### 3.4 Budget-Compliance Agent (ML plug-in point B)
- **Input:** the draft's budget table plus the call's funding cap plus programme and scheme.
- **Tools:** `check_cap(total, cap)` (deterministic), and **Model B, the budget-anomaly detector** (Isolation Forest or autoencoder trained on CORDIS funded budgets).
- **Logic:** verify the total is within cap, run Model B to flag line items that deviate from funded norms for that programme and project size, explain each flag (SHAP).
- **Output:** `{within_cap: bool, anomalies: [...], notes: [...]}`.

### 3.5 Reviewer Agent (ML plug-in point A)
- **Input:** the assembled draft.
- **Tools:** `search_criteria(call)` for RAG over the funder's published evaluation criteria, and **Model A, the fundability scorer** (LoRA-fine-tuned transformer plus tabular, trained on CORDIS).
- **Logic:** score the draft section by section against real criteria, use Model A as a fundability signal, and if the score is below threshold, emit **structured feedback** naming the weak sections and hand it back to Drafting via the Coordinator.
- **Output:** `{score, per_criterion: {...}, feedback: [...], pass: bool}`.

---

## 4. Where the ML plugs in (the "real ML, not an LLM wrapper" answer)

| Model | Lives in | Predicts | Trained on | Type |
|---|---|---|---|---|
| **Model A, Fundability scorer** | Reviewer agent | Fundability strength of a proposal | CORDIS objectives plus metadata (documented label proxy) | LoRA transformer plus GBM baseline |
| **Model B, Budget-anomaly detector** | Budget agent | Whether a budget line deviates from funded norms | CORDIS `ecMaxContribution` and cost structure, conditioned on programme and size | Isolation Forest, then autoencoder |

**The division of labour:** the LLM agents orchestrate, retrieve, and draft. The two ML models make the verifiable quantitative judgments. That is what keeps GrantPilot grounded rather than a chatbot guessing.

---

## 5. Data flow (end to end)

```
        +------------+
        |   USER     |  funding call + applicant profile
        +-----+------+
              |
              v
        +------------+
        |COORDINATOR |  plans the route
        +-----+------+
              |
              v
        +------------+   RAG: call rules (ChromaDB)
        |ELIGIBILITY |<------------------------------+
        +-----+------+                               |
              |  eligible?                            |
        +-----+-------+                               |
        NO            YES                             |
        |              v                              |
     [STOP]      +------------+  RAG: requirements ---+
                 |  DRAFTING  |<----------+           |
                 +-----+------+           |           |
                       v                  | feedback  |
                 +------------+           | (loop,    |
                 |   BUDGET   |  Model B  |  capped)  |
                 +-----+------+           |           |
                       v                  |           |
                 +------------+  Model A  |           |
                 |  REVIEWER  |  RAG:     |           |
                 +-----+------+  criteria-+           |
                       |  pass?                        |
                 +-----+-------+                       |
                 NO------------+  (back to Drafting)   |
                 |                                      |
                YES                                     |
                 v                                      |
        +----------------------------------------+      |
        | FINAL: verdict + draft + budget + score|      |
        +----------------------------------------+      |
   ChromaDB (RAG store) --------------------------------+
```

---

## 6. The stack, mapped to the architecture

| Concern | Choice | Where it appears above |
|---|---|---|
| LLM reasoning (all agents) | Ollama plus Qwen 2.5 3B (local) | every agent's ReAct loop |
| Agent loop | hand-built ReAct (Phase 3), then CrewAI (Phase 4) | all five agents |
| Retrieval | ChromaDB plus sentence-transformers | Eligibility, Drafting, Reviewer |
| Model A | HF Transformers plus PEFT/LoRA (trained on Colab) | Reviewer |
| Model B | scikit-learn (trained on Colab) | Budget |
| Serving | FastAPI plus Docker | wraps the Coordinator |
| Frontend | React plus Vite plus Tailwind plus Framer Motion | consumes the API |
| Observability | Langfuse (self-hosted) | traces every agent step |

---

## 7. Safety and scope guards (baked into the architecture)

- **Iteration cap** on the Reviewer and Drafting loop, which prevents runaway looping (a named failure mode, and it matters doubly on an 8GB machine).
- **Eligibility gate**, so no drafting effort is spent on disqualified applicants.
- **Citations required**, so Eligibility and Reviewer must ground claims in observed rule or criteria text.
- **Label honesty**, so Model A's negative-label proxy is documented as a known limitation in the README, not hidden.
- **4k context window**, which keeps each agent's transcript within local RAM limits.

---

*This architecture is the Phase 0 gate deliverable. Next: Phase 1, the CORDIS data pipeline.*
