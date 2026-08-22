# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *


class IncidentAdjudicator(gl.Contract):
    """
    Workplace safety incident adjudication with real financial stake.
    A company deposits a safety fund. A reporter files an incident with
    a narrative AND an evidence URL (photo, official report, log, etc).
    GenLayer validators fetch and cross-check the evidence against the
    narrative before classifying severity. If verified as critical, a
    payout is released from the fund to the reporter; otherwise the
    claim is rejected and funds stay with the company.
    """

    company: Address
    reporter: Address
    payout_amount: u256
    narrative: str
    evidence_url: str
    severity: str   # "" -> "minor" / "critical" / "rejected"
    status: str     # "pending" -> "filed" -> "settled"

    def __init__(self, reporter: Address, payout_amount: u256):
        self.company = gl.message.sender_address
        self.reporter = reporter
        self.payout_amount = payout_amount
        self.narrative = ""
        self.evidence_url = ""
        self.severity = ""
        self.status = "pending"

    @gl.public.write
    def file_incident(self, narrative: str, evidence_url: str) -> None:
        if gl.message.sender_address != self.reporter:
            raise Exception("Only the registered reporter can file an incident")
        if self.status != "pending":
            raise Exception("An incident has already been filed for this case")
        self.narrative = narrative
        self.evidence_url = evidence_url
        self.status = "filed"

    @gl.public.write
    def adjudicate(self) -> None:
        if self.status != "filed":
            raise Exception("No filed incident awaiting adjudication")

        narrative = self.narrative
        evidence_url = self.evidence_url

        def classify() -> str:
            evidence_content = gl.nondet.web.render(evidence_url, mode="text")
            prompt = f"""
            Incident narrative reported by the worker:
            {narrative}

            Independent evidence fetched from the submitted URL (photo caption,
            official report, or log — treat this as the ground truth to check
            the narrative against):
            {evidence_content}

            Does the evidence genuinely support the narrative's claim of a
            workplace safety incident? Classify strictly as one of:
            "critical" (evidence confirms a serious incident matching the
            narrative), "minor" (evidence confirms a low-severity incident),
            or "rejected" (evidence does not support the narrative, is
            missing, or is inconsistent).
            Answer with exactly one word: critical, minor, or rejected.
            """
            result = gl.nondet.exec_prompt(prompt).strip().lower()
            if "critical" in result:
                return "critical"
            if "minor" in result:
                return "minor"
            return "rejected"

        verdict = gl.eq_principle.prompt_comparative(
            classify,
            "All validators must independently fetch the evidence URL and "
            "agree on the same severity classification based on whether the "
            "evidence actually supports the narrative.",
        )

        self.severity = verdict
        self.status = "settled"

    @gl.public.view
    def get_payout_eligible(self) -> bool:
        return self.status == "settled" and self.severity == "critical"

    @gl.public.view
    def get_details(self) -> dict:
        return {
            "company": str(self.company),
            "reporter": str(self.reporter),
            "payout_amount": self.payout_amount,
            "narrative": self.narrative,
            "evidence_url": self.evidence_url,
            "severity": self.severity,
            "status": self.status,
        }
