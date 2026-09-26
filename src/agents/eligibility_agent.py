"""
The Eligibility agent: checks a proposal against a funding call's rules.

Like Budget and Reviewer, this is a DETERMINISTIC agent. Eligibility is a set
of hard rules, not a judgment call, so the rules live in code (check_eligibility)
and the LLM only narrates the result. We do not let a 3B model decide whether a
consortium is large enough; it would get it wrong, and eligibility is exactly
the kind of pass/fail that must be exact.

HONEST SCOPE: this encodes a SIMPLIFIED subset of the Horizon 2020 eligibility
rules (collaborative vs single-beneficiary structure, minimum partners and
countries, and the ERC budget ceilings). Real calls have more conditions
(entity types, associated-country lists, topic-specific limits). This is enough
to demonstrate the agent and honest about being a subset, not the full rulebook.
"""

from src.agents.tools import Tool
from src.agents.base import Agent


# Simplified Horizon 2020 scheme rules.
#   collaborative schemes need a minimum number of partners from a minimum
#     number of countries.
#   single-beneficiary schemes (ERC, MSCA-IF) fund one host; ERC calls also
#     carry a headline budget ceiling.
SCHEME_RULES = {
    "RIA":     {"kind": "collaborative", "min_partners": 3, "min_countries": 3},
    "IA":      {"kind": "collaborative", "min_partners": 3, "min_countries": 3},
    "CSA":     {"kind": "collaborative", "min_partners": 1, "min_countries": 1},
    "ERC-STG": {"kind": "single", "budget_cap": 1_500_000},
    "ERC-COG": {"kind": "single", "budget_cap": 2_000_000},
    "ERC-ADG": {"kind": "single", "budget_cap": 2_500_000},
    "MSCA-IF": {"kind": "single", "budget_cap": None},
}


def check_eligibility(scheme, ec_contribution=None, consortium_size=None,
                      num_countries=None):
    """
    Apply the rule set for `scheme`. Each check is (label, passed, detail),
    where passed is True, False, or None (could not check, value unknown).
    A None never counts as a failure; it is reported as uncheckable so the
    verdict is honest about what it did and did not verify.
    """
    rules = SCHEME_RULES.get(scheme)
    if rules is None:
        return {"scheme_known": False, "verdict": "UNDETERMINED", "checks": [],
                "detail": f"No eligibility rules on file for scheme '{scheme}'."}

    checks = []
    if rules["kind"] == "collaborative":
        mp, mc = rules["min_partners"], rules["min_countries"]
        if consortium_size is None:
            checks.append((f"at least {mp} partners", None, "consortium size unknown"))
        else:
            checks.append((f"at least {mp} partners", consortium_size >= mp,
                           f"has {consortium_size}"))
        if num_countries is None:
            checks.append((f"at least {mc} countries", None, "country count unknown"))
        else:
            checks.append((f"at least {mc} countries", num_countries >= mc,
                           f"has {num_countries}"))
    else:  # single-beneficiary
        if consortium_size is None:
            checks.append(("single beneficiary", None, "participant count unknown"))
        else:
            checks.append(("single beneficiary", consortium_size == 1,
                           f"has {consortium_size} participant(s)"))
        cap = rules.get("budget_cap")
        if cap is not None:
            if ec_contribution is None:
                checks.append((f"budget at most {cap:,} EUR", None, "budget unknown"))
            else:
                checks.append((f"budget at most {cap:,} EUR", ec_contribution <= cap,
                               f"requests {ec_contribution:,.0f} EUR"))

    # Three-way verdict, computed deterministically:
    #   any rule FAILED            -> NOT ELIGIBLE
    #   else any rule UNCHECKED    -> UNDETERMINED (we did not verify everything)
    #   else                       -> ELIGIBLE
    failed = [c for c in checks if c[1] is False]
    unchecked = [c for c in checks if c[1] is None]
    if failed:
        verdict = "NOT ELIGIBLE"
    elif unchecked:
        verdict = "UNDETERMINED"
    else:
        verdict = "ELIGIBLE"
    return {"scheme_known": True, "verdict": verdict, "checks": checks}


# Proposal store, populated by the test (and by the Coordinator in Phase 4).
PROPOSALS = {}


def register_proposal(proposal_id, **fields):
    PROPOSALS[proposal_id] = fields


ELIGIBILITY_ROLE = (
    "You are an Eligibility checker for EU research funding calls. You decide "
    "whether a proposal meets the hard eligibility rules of its funding scheme. "
    "Call check_eligibility with the given proposal_id. The tool applies the "
    "rules and returns, per rule, whether it passed, failed, or could not be "
    "checked, plus an overall verdict. "
    "The verdict is exactly one of ELIGIBLE, NOT ELIGIBLE, or UNDETERMINED. "
    "Report it exactly as the tool states it. UNDETERMINED means eligibility "
    "could not be decided (the scheme is not on file, or a required value was "
    "unknown); you must NEVER convert UNDETERMINED into NOT ELIGIBLE, they are "
    "different outcomes. "
    "Your Final Answer must give the verdict and then list each rule's result "
    "(PASS, FAIL, or UNCHECKED) with its detail. Never invent a rule or a verdict."
)


def _fmt_checks(checks):
    out = []
    for label, passed, detail in checks:
        mark = "PASS" if passed is True else "FAIL" if passed is False else "UNCHECKED"
        out.append(f"  [{mark}] {label} ({detail})")
    return "\n".join(out) if out else "  (no checks)"


def make_eligibility_tool():
    def _run(args):
        pid = args.get("proposal_id")
        if pid is None:
            return 'Error: check_eligibility needs {"proposal_id": "<id>"}.'
        if pid not in PROPOSALS:
            return (f"Error: no proposal registered with id '{pid}'. "
                    f"Known ids: {list(PROPOSALS)}.")
        fields = PROPOSALS[pid]
        r = check_eligibility(
            scheme=fields.get("scheme"),
            ec_contribution=fields.get("ec_contribution"),
            consortium_size=fields.get("consortium_size"),
            num_countries=fields.get("num_countries"),
        )
        if not r["scheme_known"]:
            return (f"proposal {pid} | scheme {fields.get('scheme')} | "
                    f"verdict: UNDETERMINED (scheme rules not on file, so "
                    f"eligibility cannot be decided)")
        return (f"proposal {pid} | scheme {fields.get('scheme')} | "
                f"verdict: {r['verdict']}\n{_fmt_checks(r['checks'])}")

    return Tool(
        name="check_eligibility",
        description=(
            "Check a registered proposal against its funding scheme's eligibility "
            "rules (structure, minimum partners and countries, budget ceiling). "
            'Action Input must be JSON like {"proposal_id": "E1"}.'
        ),
        func=_run,
    )


def make_eligibility_agent():
    tool = make_eligibility_tool()
    return Agent(
        name="EligibilityAgent",
        role=ELIGIBILITY_ROLE,
        registry={tool.name: tool},
        max_steps=5,
    )
