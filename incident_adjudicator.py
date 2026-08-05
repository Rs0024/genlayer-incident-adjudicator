# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

CRITICAL_THRESHOLD = 8


class Contract(gl.Contract):
    severity: TreeMap[str, str]
    category: TreeMap[str, str]
    escalate: TreeMap[str, str]
    rationale: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def assess_incident(self, incident_id: str, report: str):
        def leader_fn():
            prompt = f"""You are a workplace safety incident classifier.

Incident report:
{report}

Classify using this scale:
- category: one of "near_miss", "first_aid", "medical_treatment", "lost_time", "major"
- severity: integer 1-10 where 1-3 minor, 4-7 significant, 8-10 critical
- escalate: "yes" if severity >= 7 or category is "lost_time" or "major", else "no"

Return ONLY JSON, no markdown:
{{
  "category": "...",
  "severity": 0,
  "escalate": "yes" or "no",
  "rationale": "one short line"
}}"""
            return json.loads(gl.nondet.exec_prompt(prompt))

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            mine = leader_fn()
            theirs = leader_result.calldata

            ls = int(theirs["severity"])
            vs = int(mine["severity"])

            # categorical decisions must match exactly
            if theirs["category"] != mine["category"]:
                return False
            if theirs["escalate"] != mine["escalate"]:
                return False

            # both sides must agree on which side of the critical
            # threshold this sits — the boundary itself is never blurred
            if (ls >= CRITICAL_THRESHOLD) != (vs >= CRITICAL_THRESHOLD):
                return False

            # within whichever band both agree on, allow +/- 1
            return abs(ls - vs) <= 1

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.severity[incident_id] = str(result["severity"])
        self.category[incident_id] = result["category"]
        self.escalate[incident_id] = result["escalate"]
        self.rationale[incident_id] = result["rationale"]

    @gl.public.view
    def get_assessment(self, incident_id: str) -> str:
        return (
            self.category[incident_id]
            + " | severity " + self.severity[incident_id]
            + " | escalate: " + self.escalate[incident_id]
        )
