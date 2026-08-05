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
|
