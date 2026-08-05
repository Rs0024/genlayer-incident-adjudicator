# GenLayer Incident Severity Adjudicator

An Intelligent Contract that classifies workplace safety incidents on-chain — with a validator design that tolerates LLM scoring noise in the middle of the scale while refusing any tolerance at the critical end.

## Problem

Safety incident classification decides real consequences: regulatory reportability, escalation to plant leadership, insurance exposure, contractor scorecards. Today it is one person reading a narrative report and applying judgement, which means the same incident gets scored differently depending on who logs it.

A deterministic contract cannot do this. The input is a free-text narrative, and mapping it to a category and severity requires reading comprehension, not pattern matching.

But naively putting an LLM behind it doesn't work either: ask two models to score the same incident 1-10 and they will routinely differ by a point. Requiring exact agreement would leave most transactions undetermined.

## Approach

On `assess_incident(incident_id, report)` the leader classifies the narrative into four fields: `category`, `severity` (1-10), `escalate`, and a free-text `rationale`.

Each validator independently re-runs the same classification on the same report, then applies a **three-part comparison**:

| Field | Rule | Why |
|---|---|---|
| `category` | exact match | It's an enum with real regulatory meaning — `lost_time` vs `first_aid` changes reportability |
| `escalate` | exact match | It's the actionable output; a disagreement here is a disagreement about what happens next |
| `severity` | ±1 tolerance, **but exact match if either side scores ≥8** | Two competent assessors differ by a point in the middle of the scale; nobody should be sloppy about a critical call |
| `rationale` | never compared | Two LLMs always word an explanation differently while agreeing on the verdict |

The critical-band gate is the part worth stealing. A flat ±1 tolerance would let a leader scoring 8 (critical) reach consensus with a validator scoring 7 (not critical) — silently converting a critical incident into a non-critical one at the exact boundary where it matters most. Clamping tolerance to zero above the threshold closes that gap.

## Consensus design

Uses `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` with **numeric tolerance plus categorical exact-match**.

The validator does not inspect the leader's output for schema correctness. Checking that `category` is one of five allowed strings and `severity` is an integer 1-10 would only prove the leader formatted its answer well — it would not verify the classification. The validator instead produces its own independent classification from the same narrative and compares decision fields.

## State

| Field | Type | Description |
|---|---|---|
| `category` | `TreeMap[str, str]` | `near_miss` / `first_aid` / `medical_treatment` / `lost_time` / `major` |
| `severity` | `TreeMap[str, str]` | Agreed score, 1-10 |
| `escalate` | `TreeMap[str, str]` | `yes` / `no` |
| `rationale` | `TreeMap[str, str]` | Leader's reasoning, stored but never compared |

## Methods

**`assess_incident(incident_id: str, report: str)`** — write. Classifies, reaches consensus, stores result.

**`get_assessment(incident_id: str) -> str`** — view. Returns category, severity and escalation flag.

## Test results

Verified on GenLayer Studio in full consensus mode, chosen to exercise each band of the validator:

| Incident | Category | Severity | Escalate | Band exercised |
|---|---|---|---|---|
| Coolant leak, area cordoned, no injury | `near_miss` | 2 | no | Low |
| Chemical splash, wound cleaned and dressed | `first_aid` | 2 | no | Low |
| Laceration, six sutures, five days restricted duty | `medical_treatment` | 4 | no | **Tolerance band** |
| Fall from scaffold, fractured femur, eight weeks off | `lost_time` | 8 | **yes** | **Critical, zero tolerance** |

All four reached consensus and finalized. The middle case is the one that demonstrates the tolerance rule doing work; the fall case demonstrates the critical gate holding at exactly the threshold where a flat tolerance would have been unsafe.

The `first_aid` result on the chemical splash is correct rather than lenient — cleaning, dressing and topical treatment fall under first aid, not medical treatment, under standard occupational classification.

## Reusing this pattern

The validator shape generalises to any scored assessment where the middle of the scale is noisy but one end is consequential:

- Credit or counterparty risk scoring with a hard gate at default probability
- Content moderation severity with zero tolerance above a takedown threshold
- Equipment condition scoring where "run to failure" vs "shut down now" must not blur
- Vendor SLA breach grading with an exact gate on penalty-triggering tiers

Keep the three-part comparison: exact match on categorical decisions, tolerance on the noisy numeric, zero tolerance above the consequential threshold, and no comparison at all on free-text reasoning.

## Limitations

- The severity scale is defined in the prompt, not enforced in code — a validator disagreeing on scale interpretation shows up as a category or escalation mismatch rather than an explicit error
- Very long incident narratives may need truncation
- The category enum is fixed to a common occupational scheme; other regimes need the prompt and gate threshold adjusted together
- `escalate` is derived by the LLM rather than computed from `severity` and `category` in code, so it is compared as its own decision field rather than trusted as a function of the others

## Running it

Open [studio.genlayer.com](https://studio.genlayer.com), create a new contract file, paste `incident_adjudicator.py`, and deploy. Call `assess_incident` with any incident narrative.

## License

MIT
