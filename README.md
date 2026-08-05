# GenLayer Incident Severity Adjudicator

**Live demo:** https://rs0024.github.io/genlayer-incident-adjudicator/

An Intelligent Contract that classifies workplace safety incidents on-chain — with a validator design that tolerates LLM scoring noise inside a band while refusing to let the critical boundary blur.

## Problem

Safety incident classification decides real consequences: regulatory reportability, escalation to plant leadership, insurance exposure, contractor scorecards. Today it is one person reading a narrative report and applying judgement, which means the same incident gets scored differently depending on who logs it.

A deterministic contract cannot do this. The input is a free-text narrative, and mapping it to a category and severity requires reading comprehension, not pattern matching.

But naively putting an LLM behind it doesn't work either: ask two models to score the same incident 1-10 and they will routinely differ by a point. Requiring exact agreement would leave most transactions undetermined.

## Approach

On `assess_incident(incident_id, report)` the leader classifies the narrative into four fields: `category`, `severity` (1-10), `escalate`, and a free-text `rationale`.

Each validator independently re-runs the same classification on the same report, then applies a four-part comparison:

| Field | Rule | Why |
|---|---|---|
| `category` | exact match | It's an enum with regulatory meaning — `lost_time` vs `first_aid` changes reportability |
| `escalate` | exact match | It's the actionable output; disagreement here is disagreement about what happens next |
| `severity` | both sides must land on the same side of the critical threshold, then ±1 within that band | Two competent assessors differ by a point mid-scale, but must never disagree about whether something is critical |
| `rationale` | never compared | Two LLMs always word an explanation differently while agreeing on the verdict |

## The boundary problem

The first version of this validator required **exact** severity match whenever either side scored ≥8. The reasoning seemed sound: nobody should be sloppy about a critical call.

In practice it broke. Ask two models to score a fall-from-height with a fractured femur and one says 8, the other 9. Both are calling it critical. Both are right. But exact-match rejected the pair, consensus failed, and the transaction went undetermined — the contract refused to record the most serious incident it was given.

The fix is to gate on the **band**, not the number:

```python
# both sides must agree which side of the threshold this sits on
if (ls >= CRITICAL_THRESHOLD) != (vs >= CRITICAL_THRESHOLD):
    return False

# within whichever band both agree on, allow +/- 1
return abs(ls - vs) <= 1
```

This keeps the safety property that mattered — a leader scoring 8 can never reach consensus with a validator scoring 7, so the critical boundary is never silently crossed — while letting 8-vs-9 through, since both agree on what the incident *is*.

The general lesson: when a numeric field has a consequential threshold, the thing validators must agree on is which side of the threshold they're on, not the exact value.

## Consensus design

Uses `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` with categorical exact-match plus threshold-gated numeric tolerance.

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

## Frontend

A browser dApp at [rs0024.github.io/genlayer-incident-adjudicator](https://rs0024.github.io/genlayer-incident-adjudicator/) talks to the deployed contract directly via `genlayer-js` — no backend.

Three sample narratives are built in, one per band. **Assess on-chain** sends a real write transaction and waits for validator consensus; **Read stored assessment** performs a view call. Severity badges are colour-coded by band.

Single static file (`index.html`), zero build step.

## Test results

Run end-to-end from the browser dApp against the deployed contract:

| Incident | Category | Severity | Escalate | Band exercised |
|---|---|---|---|---|
| Coolant puddle, cordoned off, no injury | `near_miss` | 1 | no | Low |
| Laceration, six sutures, five days restricted duty | `medical_treatment` | 5 | no | Tolerance band |
| Fall from scaffold, fractured femur, eight weeks off | `major` | 8 | **yes** | Critical |

All three reached consensus and finalized. The critical case is the one that failed under the original exact-match gate and passes under the band gate.

## Limitations

- **Category can shift between runs.** The same fall narrative classified as `lost_time` in one run and `major` in another. Both are defensible readings, and validators agreed *within* each run — but the contract does not currently guarantee run-to-run stability on category. Narrowing the enum or giving each category an explicit definition in the prompt would tighten this.
- The severity scale lives in the prompt, not in code. A validator interpreting the scale differently surfaces as a category or escalation mismatch rather than an explicit error.
- `escalate` is produced by the LLM rather than computed from `severity` and `category`, so it is compared as its own decision field rather than derived. Computing it in deterministic code after consensus would remove one source of disagreement.
- Very long narratives may need truncation.

## Reusing this pattern

The validator shape generalises to any scored assessment where the middle of the scale is noisy but a threshold is consequential:

- Credit or counterparty risk scoring with a hard gate at a default-probability threshold
- Content moderation severity with a gate at the takedown line
- Equipment condition scoring where "run to failure" vs "shut down now" must not blur
- Vendor SLA breach grading with a gate at penalty-triggering tiers

Keep the four-part comparison: exact match on categorical decisions, band agreement at the consequential threshold, tolerance within the band, no comparison at all on free-text reasoning.

## Running it

**Contract:** open [studio.genlayer.com](https://studio.genlayer.com), create a new contract file, paste `incident_adjudicator.py`, and deploy.

**Frontend:** `index.html` is standalone. Update the `CONTRACT` constant if you deploy your own instance.

## Deployed instance

`0x9AE9D84Bc940dc77FBF243A71e78A413e2897470` — [view on explorer](https://explorer-studio.genlayer.com/address/0x9AE9D84Bc940dc77FBF243A71e78A413e2897470)

## License

MIT
